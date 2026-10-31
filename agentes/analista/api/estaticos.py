"""Sirve la interfaz ya compilada (carpeta ``dist``) desde el mismo servicio que la API.

Así el hosting expone un solo URL y la interfaz usa rutas relativas ``/api/analista``.
Solo se activa si existe la carpeta compilada, por lo que no cambia nada en desarrollo local.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

RAIZ_PROYECTO = Path(__file__).resolve().parents[3]


def carpeta_frontend() -> Path | None:
    configurada = os.environ.get("FRONTEND_DIST", "").strip()
    carpeta = Path(configurada) if configurada else RAIZ_PROYECTO / "dist"
    return carpeta if (carpeta / "index.html").is_file() else None


def montar_frontend(app: FastAPI) -> bool:
    carpeta = carpeta_frontend()
    if carpeta is None:
        return False
    base = carpeta.resolve()

    @app.get("/healthz", include_in_schema=False)
    async def salud() -> dict[str, str]:
        return {"estado": "ok"}

    @app.get("/{ruta:path}", include_in_schema=False)
    async def interfaz(ruta: str) -> FileResponse:
        if ruta == "api" or ruta.startswith("api/"):
            raise HTTPException(status_code=404, detail="No encontrado.")
        candidato = (base / ruta).resolve()
        if ruta and candidato.is_file() and base in candidato.parents:
            return FileResponse(candidato)
        # Rutas de React Router (/historias, /historias/nueva...): devuelve la página principal.
        return FileResponse(base / "index.html")

    return True
