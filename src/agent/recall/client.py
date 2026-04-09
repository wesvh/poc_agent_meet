"""Recall.ai REST API client — create and manage meeting bots."""
from __future__ import annotations

import logging

import httpx

from src.agent.recall.assets import ALIA_AVATAR_B64
from src.config import Config

log = logging.getLogger(__name__)


class RecallClient:
    """Thin async HTTP client for the Recall.ai v1 API."""

    def __init__(self):
        self.base_url = Config.RECALL_API_BASE_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Token {Config.RECALL_API_KEY}",
            "Content-Type": "application/json",
        }

    async def create_bot(
        self,
        meeting_url: str,
        bot_name: str,
        realtime_ws_url: str,
        output_page_url: str,
    ) -> dict:
        """Create a bot and send it to a meeting.

        Args:
            meeting_url:     Google Meet / Zoom / Teams URL
            bot_name:        Name shown in the meeting participant list
            realtime_ws_url: wss://... Recall.ai pushes audio_separate_raw.data events here
            output_page_url: https://... Recall.ai loads this page as the bot's camera feed
                             (our audio player page — black background, plays TTS via Web Audio)
        """
        payload = {
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            "recording_config": {
                "audio_separate_raw": {},
                "realtime_endpoints": [
                    {
                        "type": "websocket",
                        "url": realtime_ws_url,
                        "events": ["audio_separate_raw.data"],
                    }
                ],
            },
            # Bot creation uses kind/config format — different from the output_media
            # update endpoint which uses the nested webpage.url format.
            "output_media": {
                "camera": {
                    "kind": "webpage",
                    "config": {"url": output_page_url},
                },
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/bot/",
                headers=self.headers,
                json=payload,
            )
            if not resp.is_success:
                log.error("[recall:client] Bot creation failed: %s %s", resp.status_code, resp.text)
            resp.raise_for_status()
            data = resp.json()
            log.info("[recall:client] Bot created: id=%s url=%s", data.get("id"), meeting_url)
            return data

    async def get_bot(self, bot_id: str) -> dict:
        """Retrieve bot status and metadata."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/bot/{bot_id}/",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def update_output_media(
        self,
        bot_id: str,
        *,
        camera_url: str | None = None,
        screenshare_url: str | None = None,
    ) -> dict:
        """Update the bot's output media while it is in a call.

        Use this to start or change screenshare (and/or camera) after the bot is created.
        Each field is optional — only the keys you include are updated.

        Endpoint: POST /api/v1/bot/{id}/output_media/

        Args:
            bot_id:          Recall.ai bot UUID (the id returned by create_bot)
            camera_url:      Webpage URL to render as the bot's camera feed
            screenshare_url: Webpage URL to share as screenshare in the meeting
        """
        body: dict = {}
        if camera_url is not None:
            body["camera"] = {"kind": "webpage", "config": {"url": camera_url}}
        if screenshare_url is not None:
            body["screenshare"] = {"kind": "webpage", "config": {"url": screenshare_url}}

        if not body:
            raise ValueError("At least one of camera_url or screenshare_url must be provided")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/bot/{bot_id}/output_media/",
                headers=self.headers,
                json=body,
            )
            if not resp.is_success:
                log.error(
                    "[recall:client] update_output_media failed: bot=%s %s %s",
                    bot_id, resp.status_code, resp.text,
                )
            resp.raise_for_status()
            return resp.json()

    async def update_output_video(self, bot_id: str, b64_data: str, kind: str = "jpeg") -> dict:
        """Update the bot's video frame while it is in a call.

        Endpoint: POST /api/v1/bot/{id}/output_video/

        Args:
            bot_id:   Recall.ai bot UUID
            b64_data: Base64-encoded image (JPEG or PNG, no data URI prefix)
            kind:     Image format — "jpeg" (default) or "png"
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/bot/{bot_id}/output_video/",
                headers=self.headers,
                json={"kind": kind, "b64_data": b64_data},
            )
            if not resp.is_success:
                log.error(
                    "[recall:client] update_output_video failed: bot=%s %s %s",
                    bot_id, resp.status_code, resp.text,
                )
            resp.raise_for_status()
            return resp.json()

    async def stop_output_media(
        self,
        bot_id: str,
        *,
        camera: bool = False,
        screenshare: bool = False,
    ) -> None:
        """Stop camera and/or screenshare output for a bot.

        Endpoint: DELETE /api/v1/bot/{id}/output_media/

        Args:
            bot_id:     Recall.ai bot UUID
            camera:     If True, stop the camera feed
            screenshare: If True, stop the screenshare
        """
        if not camera and not screenshare:
            raise ValueError("At least one of camera or screenshare must be True")

        body: dict = {}
        if camera:
            body["camera"] = False
        if screenshare:
            body["screenshare"] = False

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.request(
                "DELETE",
                f"{self.base_url}/api/v1/bot/{bot_id}/output_media/",
                headers=self.headers,
                json=body,
            )
            if not resp.is_success:
                log.error(
                    "[recall:client] stop_output_media failed: bot=%s %s %s",
                    bot_id, resp.status_code, resp.text,
                )
            resp.raise_for_status()
            log.info("[recall:client] Output media stopped: bot=%s camera=%s screenshare=%s",
                     bot_id, camera, screenshare)
