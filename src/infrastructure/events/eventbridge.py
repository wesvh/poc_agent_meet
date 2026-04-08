from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

import aioboto3

from src.config import Config

log = logging.getLogger(__name__)


async def _wait_for_rule(events_client, rule_name: str, attempts: int = 10, delay_s: float = 0.5) -> None:
    for _ in range(attempts):
        response = await events_client.list_rules(NamePrefix=rule_name)
        rules = response.get("Rules", [])
        if any(rule.get("Name") == rule_name for rule in rules):
            return
        await asyncio.sleep(delay_s)
    raise RuntimeError(f"EventBridge rule not visible after creation: {rule_name}")


def _aws_client_kwargs() -> dict:
    kwargs: dict = {"region_name": Config.AWS_REGION}
    if Config.AWS_ENDPOINT:
        kwargs["endpoint_url"] = Config.AWS_ENDPOINT
    return kwargs


async def _ensure_invoke_role() -> str:
    session = aioboto3.Session()
    assume_role_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "events.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    )
    async with session.client("iam", **_aws_client_kwargs()) as iam:
        try:
            response = await iam.get_role(RoleName=Config.EVENTBRIDGE_INVOKE_ROLE_NAME)
            return response["Role"]["Arn"]
        except Exception:
            response = await iam.create_role(
                RoleName=Config.EVENTBRIDGE_INVOKE_ROLE_NAME,
                AssumeRolePolicyDocument=assume_role_policy,
                Description="Allows EventBridge to invoke the Airflow API destination",
            )
            return response["Role"]["Arn"]


async def _account_id() -> str:
    session = aioboto3.Session()
    async with session.client("sts", **_aws_client_kwargs()) as sts:
        response = await sts.get_caller_identity()
    return response["Account"]


async def _ensure_scheduler_role(account_id: str) -> str:
    session = aioboto3.Session()
    role_name = Config.MEETING_SCHEDULE_ROLE_NAME
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    assume_role_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "scheduler.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    )
    policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["events:PutEvents"],
                    "Resource": f"arn:aws:events:{Config.AWS_REGION}:{account_id}:event-bus/{Config.MEETING_EVENT_BUS_NAME}",
                }
            ],
        }
    )
    async with session.client("iam", **_aws_client_kwargs()) as iam:
        try:
            await iam.get_role(RoleName=role_name)
        except Exception:
            await iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=assume_role_policy,
                Description="Allows EventBridge Scheduler to emit meeting due events",
            )
        await iam.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}-put-events",
            PolicyDocument=policy,
        )
    return role_arn


async def _ensure_schedule_group(scheduler_client) -> None:
    try:
        await scheduler_client.get_schedule_group(Name=Config.MEETING_SCHEDULE_GROUP_NAME)
    except Exception:
        await scheduler_client.create_schedule_group(Name=Config.MEETING_SCHEDULE_GROUP_NAME)


async def _replace_connection(events_client) -> str:
    try:
        await events_client.delete_connection(Name=Config.EVENTBRIDGE_CONNECTION_NAME)
    except Exception:
        pass
    response = await events_client.create_connection(
        Name=Config.EVENTBRIDGE_CONNECTION_NAME,
        AuthorizationType="BASIC",
        AuthParameters={
            "BasicAuthParameters": {
                "Username": Config.AIRFLOW_USERNAME,
                "Password": Config.AIRFLOW_PASSWORD,
            }
        },
        Description="Basic auth connection for the Airflow REST API",
    )
    return response["ConnectionArn"]


async def _replace_api_destination(events_client, connection_arn: str) -> str:
    endpoint = f"{Config.AIRFLOW_BASE_URL}/api/v1/dags/{Config.AIRFLOW_ETL_DAG_ID}/dagRuns"
    try:
        await events_client.delete_api_destination(Name=Config.EVENTBRIDGE_API_DESTINATION_NAME)
    except Exception:
        pass
    response = await events_client.create_api_destination(
        Name=Config.EVENTBRIDGE_API_DESTINATION_NAME,
        ConnectionArn=connection_arn,
        InvocationEndpoint=endpoint,
        HttpMethod="POST",
        InvocationRateLimitPerSecond=10,
        Description="Triggers the ETL DAG in Airflow when a CSV arrives in the raw bucket",
    )
    return response["ApiDestinationArn"]


async def ensure_s3_to_airflow_rule() -> None:
    session = aioboto3.Session()
    detail: dict = {"bucket": {"name": [Config.S3_RAW_BUCKET]}}
    if Config.EVENTBRIDGE_FILTER_CSV_SUFFIX:
        detail["object"] = {"key": [{"suffix": ".csv"}]}
    rule_pattern = json.dumps(
        {
            "source": ["aws.s3"],
            "detail-type": ["Object Created"],
            "detail": detail,
        }
    )
    input_template = (
        '{"conf":{"s3_bucket":"<bucket>","s3_key":"<key>",'
        '"triggered_by":"s3_event","event_id":"<event_id>"}}'
    )

    role_arn = await _ensure_invoke_role()
    async with session.client("events", **_aws_client_kwargs()) as events:
        connection_arn = await _replace_connection(events)
        api_destination_arn = await _replace_api_destination(events, connection_arn)
        await events.put_rule(
            Name=Config.EVENTBRIDGE_RULE_NAME,
            EventPattern=rule_pattern,
            State="ENABLED",
            Description="Trigger Airflow ETL when a CSV is created in the raw S3 bucket",
        )
        await _wait_for_rule(events, Config.EVENTBRIDGE_RULE_NAME)
        target = {
            "Id": Config.EVENTBRIDGE_TARGET_ID,
            "Arn": api_destination_arn,
            "RoleArn": role_arn,
            "HttpParameters": {
                "HeaderParameters": {
                    "Content-Type": "application/json",
                }
            },
        }
        if Config.EVENTBRIDGE_USE_INPUT_TRANSFORMER:
            target["InputTransformer"] = {
                "InputPathsMap": {
                    "bucket": "$.detail.bucket.name",
                    "key": "$.detail.object.key",
                    "event_id": "$.id",
                },
                "InputTemplate": input_template,
            }
        await events.put_targets(
            Rule=Config.EVENTBRIDGE_RULE_NAME,
            Targets=[target],
        )
    log.info("EventBridge rule ready: %s", Config.EVENTBRIDGE_RULE_NAME)


async def upsert_meeting_schedule(
    meeting_id: str,
    store_id: str,
    scheduled_at: datetime | None,
    meeting_link: str | None,
    lead_minutes: int,
) -> str:
    if scheduled_at is None or not meeting_link:
        raise ValueError("Meeting schedule requires scheduled_at and meeting_link")

    schedule_time = scheduled_at.astimezone(UTC) - timedelta(minutes=lead_minutes)
    schedule_expression = f"at({schedule_time.strftime('%Y-%m-%dT%H:%M:%S')})"
    schedule_name = f"{Config.MEETING_SCHEDULE_PREFIX}-{meeting_id}"
    account_id = await _account_id()
    role_arn = await _ensure_scheduler_role(account_id)
    bus_arn = f"arn:aws:events:{Config.AWS_REGION}:{account_id}:event-bus/{Config.MEETING_EVENT_BUS_NAME}"
    payload = json.dumps(
        {
            "meeting_id": meeting_id,
            "store_id": store_id,
            "scheduled_at": scheduled_at.astimezone(UTC).isoformat(),
            "trigger_at": schedule_time.isoformat(),
            "meeting_link": meeting_link,
            "lead_minutes": lead_minutes,
        }
    )
    target = {
        "Arn": bus_arn,
        "RoleArn": role_arn,
        "EventBridgeParameters": {
            "Source": Config.MEETING_EVENT_SOURCE,
            "DetailType": Config.MEETING_EVENT_DETAIL_TYPE,
        },
        "Input": payload,
        "RetryPolicy": {
            "MaximumEventAgeInSeconds": 3600,
            "MaximumRetryAttempts": 2,
        },
    }

    session = aioboto3.Session()
    async with session.client("scheduler", **_aws_client_kwargs()) as scheduler:
        await _ensure_schedule_group(scheduler)
        params = {
            "Name": schedule_name,
            "GroupName": Config.MEETING_SCHEDULE_GROUP_NAME,
            "ScheduleExpression": schedule_expression,
            "FlexibleTimeWindow": {"Mode": "OFF"},
            "Target": target,
            "Description": f"Trigger handoff meeting {meeting_id} {lead_minutes} minutes before scheduled_at",
            "State": "ENABLED",
            "ActionAfterCompletion": "DELETE",
        }
        try:
            await scheduler.create_schedule(**params)
            return "created"
        except scheduler.exceptions.ConflictException:
            await scheduler.update_schedule(**params)
            return "updated"
