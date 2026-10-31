"""Conexión a la base de datos del Repositorio de HU: MySQL compatible (TiDB Cloud Starter) o SQLite local.

La URL llega por la variable de entorno ``DATABASE_URL`` (nunca se escribe en el repositorio ni en los logs).
Sin esa variable se usa un archivo SQLite local, útil para desarrollo y pruebas.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

import certifi
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url

_lock = threading.Lock()
_engines: dict[str, Engine] = {}


def ruta_sqlite_por_defecto() -> Path:
    configurada = os.environ.get("ANALISTA_REPO_DB", "").strip()
    if configurada:
        return Path(configurada)
    return Path(__file__).resolve().parents[1] / "data" / "repositorio.db"


def url_desde_entorno() -> str:
    """URL de la base: DATABASE_URL (MySQL/TiDB) o, si no existe, el SQLite local."""
    url = os.environ.get("DATABASE_URL", "").strip()
    return url or f"sqlite:///{ruta_sqlite_por_defecto().as_posix()}"


def normalizar_url(valor: str | Path) -> URL:
    """Acepta rutas de archivo, ``mysql://`` y ``mysql+pymysql://``; devuelve una URL de SQLAlchemy."""
    texto = str(valor)
    if "://" not in texto:
        return make_url(f"sqlite:///{Path(texto).as_posix()}")
    url = make_url(texto)
    if url.drivername in ("mysql", "mariadb"):
        url = url.set(drivername="mysql+pymysql")
    return url


def crear_motor(valor: str | Path | None = None) -> Engine:
    """Motor compartido por URL. Pocas conexiones y reciclaje corto: el plan gratuito tiene poca memoria
    y TiDB Cloud puede cerrar conexiones inactivas (conviene reciclar antes de ~5 minutos)."""
    url = normalizar_url(valor if valor is not None else url_desde_entorno())
    clave = url.render_as_string(hide_password=False)
    with _lock:
        if clave in _engines:
            return _engines[clave]
        if url.get_backend_name() == "sqlite":
            if url.database and url.database != ":memory:":
                Path(url.database).parent.mkdir(parents=True, exist_ok=True)
            motor = create_engine(url, connect_args={"timeout": 5}, pool_pre_ping=True)
        else:
            argumentos: dict = {}
            if os.environ.get("DATABASE_SSL", "1").strip().lower() not in ("0", "false", "no"):
                argumentos["ssl"] = {"ca": certifi.where()}
            motor = create_engine(
                url, connect_args={"connect_timeout": 10, **argumentos},
                pool_size=2, max_overflow=1, pool_recycle=240, pool_pre_ping=True, pool_timeout=10,
            )
        _engines[clave] = motor
        return motor
