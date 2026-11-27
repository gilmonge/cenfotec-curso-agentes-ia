"""Mensaje a Microsoft Teams cuando una historia queda lista para que el Product Owner la apruebe.

Se configura con ``TEAMS_WEBHOOK_URL``: la URL del flujo de Teams «When a Teams webhook request is received»
(app Workflows). Sin la variable no se envía nada. Un fallo al enviar se registra y nunca detiene el flujo.
El enlace a la aplicación sale de ``APP_URL`` o, en Render, de ``RENDER_EXTERNAL_URL``.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIEMPO_ESPERA_SEGUNDO = 8.0


def _entorno(nombre: str) -> str:
    return os.environ.get(nombre, "").strip()


def url_aplicacion() -> str:
    return (_entorno("APP_URL") or _entorno("RENDER_EXTERNAL_URL")).rstrip("/")


def tarjeta_por_aprobar(titulo: str, creado_por: str | None, enlace: str | None) -> dict[str, Any]:
    """Tarjeta adaptable. Los flujos de Teams no muestran botones, así que el enlace va también como texto."""
    cuerpo: list[dict[str, Any]] = [
        {"type": "TextBlock", "text": "Historia lista para su aprobación", "weight": "Bolder", "size": "Medium"},
        {"type": "TextBlock", "text": titulo, "wrap": True},
    ]
    if creado_por:
        cuerpo.append({"type": "TextBlock", "text": f"Creada por {creado_por}", "isSubtle": True, "spacing": "None"})
    if enlace:
        cuerpo.append({"type": "TextBlock", "text": f"[Revisar y decidir]({enlace})", "wrap": True})
    contenido: dict[str, Any] = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": cuerpo,
    }
    if enlace:
        contenido["actions"] = [{"type": "Action.OpenUrl", "title": "Revisar y decidir", "url": enlace}]
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive",
                                                "content": contenido}]}


class TeamsService:
    def __init__(self, url_webhook: str | None = None) -> None:
        self.url_webhook = url_webhook if url_webhook is not None else _entorno("TEAMS_WEBHOOK_URL")

    @property
    def activo(self) -> bool:
        return bool(self.url_webhook)

    def enviar(self, tarjeta: dict[str, Any]) -> bool:
        if not self.activo:
            return False
        try:
            respuesta = httpx.post(self.url_webhook, json=tarjeta, timeout=_TIEMPO_ESPERA_SEGUNDO)
            respuesta.raise_for_status()
            logger.info("aviso_teams_enviado", extra={"event": "aviso_teams_enviado"})
            return True
        except httpx.HTTPError as exc:
            # No se registra la URL (contiene la firma del flujo), solo el tipo de error.
            logger.warning("aviso_teams_fallido", extra={"event": "aviso_teams_fallido", "error": type(exc).__name__})
            return False

    def avisar_por_aprobar(self, workflow_id: str, titulo: str, creado_por: str | None) -> None:
        """Envía en segundo plano para no demorar la respuesta a la persona."""
        if not self.activo:
            return
        base = url_aplicacion()
        enlace = f"{base}/historias/nueva?flujo={workflow_id}" if base else None
        tarjeta = tarjeta_por_aprobar(titulo, creado_por, enlace)
        try:
            asyncio.get_running_loop().run_in_executor(None, self.enviar, tarjeta)
        except RuntimeError:
            self.enviar(tarjeta)
