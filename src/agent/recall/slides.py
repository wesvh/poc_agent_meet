"""Presentation slides for the Handoff session.

Slides are loaded from src/assets/{1..7}.jpeg at import time and kept in memory
as base64 strings. They are displayed via Recall.ai's output_video endpoint
(bot's camera feed), which accepts a JPEG as base64.

Slide content:
  1 — Portada: bienvenida, logo Rappi, "Impulsando el crecimiento de tu negocio"
  2 — Agenda: 4 pilares — Verificación, Soporte, Capacitación, Orden de Prueba
  3 — Objetivo principal: configuración correcta → recibir pedidos el mismo día
  4 — Ecosistema digital: RappiAliados (app móvil) vs Portal Partners (web) — comparativa
  5 — Checklist de activación: acceso, horarios, menú/fotos, finanzas, orden de prueba
  6 — Condiciones y próximos pasos: orden de prueba como paso final antes de salir al aire
  7 — Cierre y preguntas: "¿Preguntas?" + "¡Vamos a crecer juntos!"
"""
from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

# Resolved at import: works both locally (src/assets/) and in Docker (/app/src/assets/)
_ASSETS_DIR = Path(__file__).resolve().parents[3] / "src" / "assets"
if not _ASSETS_DIR.exists():
    # Fallback for Docker: /app/src/assets/
    _ASSETS_DIR = Path("/app/src/assets")

TOTAL_SLIDES = 7

# Slides indexed 1-based: SLIDES[1] = base64 of 1.jpeg, ... SLIDES[7] = base64 of 7.jpeg
# SLIDES[0] is None (unused) so callers use natural 1-based indexing.
SLIDES: list[str | None] = [None]

for _n in range(1, TOTAL_SLIDES + 1):
    _path = _ASSETS_DIR / f"{_n}.jpeg"
    if _path.exists():
        with open(_path, "rb") as _f:
            SLIDES.append(base64.b64encode(_f.read()).decode("ascii"))
        log.info("[slides] Loaded slide %d from %s", _n, _path)
    else:
        SLIDES.append(None)
        log.warning("[slides] Slide %d not found at %s", _n, _path)


def get_slide(n: int) -> str | None:
    """Return base64-encoded JPEG for slide n (1-based), or None if not available."""
    if 1 <= n <= TOTAL_SLIDES:
        return SLIDES[n]
    return None


# Slides that may trigger the portal screenshare demo.
PORTAL_SLIDES = {4, 5, 7}
