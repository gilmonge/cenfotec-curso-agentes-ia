"""Repositorio de código que revisa el Asesor Técnico, con acceso de solo lectura.

El Asesor no consulta el código del propio proyecto: revisa un repositorio aparte
(por defecto, uno ficticio de pólizas). Este módulo lo descarga con un clon superficial,
conserva únicamente archivos .py y .md, elimina el historial de Git y deja una marca
con el origen. Nada del repositorio se importa ni se ejecuta: solo se lee como texto.

Si el repositorio no está configurado o no puede descargarse, el sistema usa el
ejemplo incluido en ``ejemplos/polizas_demo`` y lo indica en el resultado.

Uso: ``python -m agentes.conocimiento.repositorio_codigo``
(lee ``ASESOR_REPOSITORIO_URL`` y ``ASESOR_REPOSITORIO_RAMA``).
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAIZ_PREDETERMINADA = "ejemplos/polizas_demo"
RAIZ_SINCRONIZADA = "repositorio_codigo"
MARCA_ORIGEN = ".origen-repositorio.json"
EXTENSION_PERMITIDA = frozenset({".py", ".md"})
MAXIMO_ARCHIVO = 400
MAXIMO_BYTE_ARCHIVO = 200_000
TIEMPO_CLON_SEGUNDO = 90
_RAMA_VALIDA = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")


class RepositorioCodigoError(RuntimeError):
    """Error seguro: nunca incluye la URL completa ni la salida de git."""


@dataclass(frozen=True, slots=True)
class ResultadoSincronizacion:
    sincronizado: bool
    raiz: str
    detalle: str
    commit: str | None = None


def raiz_codigo_relativa(project_root: Path | None = None) -> str:
    """Raíz (relativa al proyecto) del código que revisa el Asesor en este momento."""
    root = (project_root or PROJECT_ROOT).resolve()
    destino = root / RAIZ_SINCRONIZADA
    if not destino.is_symlink() and (destino / MARCA_ORIGEN).is_file():
        return RAIZ_SINCRONIZADA
    return RAIZ_PREDETERMINADA


def prefijo_codigo(project_root: Path | None = None) -> str:
    return raiz_codigo_relativa(project_root) + "/"


def prefijo_codigo_conocido() -> tuple[str, ...]:
    """Prefijos que pueden existir en el índice: el ejemplo incluido y el repositorio sincronizado."""
    return (RAIZ_PREDETERMINADA + "/", RAIZ_SINCRONIZADA + "/")


def es_ruta_codigo(ruta: str, project_root: Path | None = None) -> bool:
    """Una referencia de código válida: relativa, sin traversal, .py/.md y dentro de la raíz activa."""
    if not isinstance(ruta, str) or not ruta or "\\" in ruta or ":" in ruta or ruta.startswith("/"):
        return False
    parte = PurePosixPath(ruta).parts
    if any(item in {"", ".", ".."} for item in parte):
        return False
    return ruta.startswith(prefijo_codigo(project_root)) and PurePosixPath(ruta).suffix in EXTENSION_PERMITIDA


def origen_repositorio(project_root: Path | None = None) -> dict[str, Any]:
    """Describe de dónde viene el código que revisa el Asesor (para trazas y para la interfaz)."""
    root = (project_root or PROJECT_ROOT).resolve()
    if raiz_codigo_relativa(root) == RAIZ_SINCRONIZADA:
        try:
            dato = json.loads((root / RAIZ_SINCRONIZADA / MARCA_ORIGEN).read_text(encoding="utf-8"))
            if isinstance(dato, dict):
                return {"tipo": "repositorio", **{k: dato.get(k) for k in ("repositorio", "rama", "commit", "sincronizado_en")}}
        except (OSError, ValueError) as exc:
            logger.warning("repositorio_codigo_marca_invalida", extra={"event": "repositorio_codigo_marca_invalida", "error": type(exc).__name__})
    return {"tipo": "ejemplo_incluido", "repositorio": RAIZ_PREDETERMINADA}


def _validar_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise RepositorioCodigoError("La URL del repositorio está vacía.")
    url = url.strip()
    partes = urlsplit(url)
    if partes.scheme != "https" or not partes.hostname:
        raise RepositorioCodigoError("El repositorio debe indicarse con una URL https.")
    if partes.username or partes.password or "@" in partes.netloc:
        # Las credenciales nunca viajan en la URL: quedarían en logs y en la configuración.
        raise RepositorioCodigoError("La URL del repositorio no debe incluir credenciales.")
    if partes.query or partes.fragment:
        raise RepositorioCodigoError("La URL del repositorio no debe incluir parámetros.")
    return url


def _nombre_publico(url: str) -> str:
    partes = urlsplit(url)
    ruta = partes.path.removesuffix(".git").strip("/")
    return f"{partes.hostname}/{ruta}"


def _ejecutar_git(argumento: list[str], *, cwd: Path | None = None) -> str:
    entorno = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_LFS_SKIP_SMUDGE": "1",
    }
    for clave in ("HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "GIT_SSL_CAINFO", "SSL_CERT_FILE"):
        if clave in os.environ:
            entorno[clave] = os.environ[clave]
    try:
        resultado = subprocess.run(
            ["git", *argumento], cwd=cwd, env=entorno, capture_output=True, text=True,
            timeout=TIEMPO_CLON_SEGUNDO, check=False,
        )
    except FileNotFoundError as exc:
        raise RepositorioCodigoError("git no está instalado en el entorno.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepositorioCodigoError("La descarga del repositorio superó el tiempo permitido.") from exc
    if resultado.returncode != 0:
        raise RepositorioCodigoError("git no pudo descargar el repositorio (revise URL, rama y visibilidad).")
    return resultado.stdout.strip()


def _tiene_texto(ruta: Path) -> bool:
    """Solo texto UTF-8 con contenido: los archivos vacíos o binarios no aportan evidencia."""
    try:
        return bool(ruta.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError):
        return False


def _depurar(directorio: Path) -> int:
    """Deja solo .py/.md regulares y de tamaño acotado; borra enlaces, binarios y el historial."""
    shutil.rmtree(directorio / ".git", ignore_errors=True)
    conservado = 0
    for actual, carpeta, archivo in os.walk(directorio, topdown=True, followlinks=False):
        ruta_actual = Path(actual)
        for nombre in list(carpeta):
            ruta = ruta_actual / nombre
            if ruta.is_symlink() or nombre.startswith("."):
                carpeta.remove(nombre)
                if ruta.is_symlink():
                    ruta.unlink()
                else:
                    shutil.rmtree(ruta, ignore_errors=True)
        for nombre in archivo:
            ruta = ruta_actual / nombre
            permitido = (
                not ruta.is_symlink()
                and ruta.is_file()
                and ruta.suffix in EXTENSION_PERMITIDA
                and 0 < ruta.stat().st_size <= MAXIMO_BYTE_ARCHIVO
                and conservado < MAXIMO_ARCHIVO
                and _tiene_texto(ruta)
            )
            if permitido:
                conservado += 1
            else:
                ruta.unlink()
    return conservado


def sincronizar(url: str, rama: str = "main", *, project_root: Path | None = None) -> ResultadoSincronizacion:
    """Descarga el repositorio en ``repositorio_codigo/``; si falla, conserva la versión anterior."""
    root = (project_root or PROJECT_ROOT).resolve()
    url = _validar_url(url)
    if not _RAMA_VALIDA.fullmatch(rama or "") or rama.startswith("-") or ".." in rama:
        raise RepositorioCodigoError("La rama indicada no es válida.")
    destino = root / RAIZ_SINCRONIZADA
    if destino.is_symlink():
        raise RepositorioCodigoError("La carpeta del repositorio no puede ser un enlace simbólico.")
    temporal = Path(tempfile.mkdtemp(prefix=".repositorio_codigo_", dir=root))
    try:
        clon = temporal / "clon"
        _ejecutar_git([
            "-c", "core.symlinks=false", "-c", "protocol.file.allow=never", "-c", "protocol.ext.allow=never",
            "clone", "--depth", "1", "--single-branch", "--no-tags", "--branch", rama, "--", url, str(clon),
        ])
        commit = _ejecutar_git(["rev-parse", "HEAD"], cwd=clon)
        cantidad = _depurar(clon)
        if cantidad == 0:
            raise RepositorioCodigoError("El repositorio no contiene archivos .py o .md que revisar.")
        (clon / MARCA_ORIGEN).write_text(json.dumps({
            "repositorio": _nombre_publico(url),
            "rama": rama,
            "commit": commit[:40],
            "archivos": cantidad,
            "sincronizado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        respaldo = temporal / "anterior"
        if destino.exists():
            destino.rename(respaldo)
        clon.rename(destino)
        return ResultadoSincronizacion(True, RAIZ_SINCRONIZADA, f"{cantidad} archivos de {_nombre_publico(url)}@{rama}", commit[:40])
    finally:
        shutil.rmtree(temporal, ignore_errors=True)


def sincronizar_desde_entorno(project_root: Path | None = None) -> ResultadoSincronizacion:
    """Punto de arranque: nunca detiene el servicio; ante un fallo sigue con lo que ya hay."""
    url = os.environ.get("ASESOR_REPOSITORIO_URL", "").strip()
    rama = os.environ.get("ASESOR_REPOSITORIO_RAMA", "main").strip() or "main"
    if not url:
        return ResultadoSincronizacion(False, raiz_codigo_relativa(project_root), "ASESOR_REPOSITORIO_URL no está definida; se usa el ejemplo incluido.")
    try:
        return sincronizar(url, rama, project_root=project_root)
    except RepositorioCodigoError as exc:
        logger.warning("repositorio_codigo_no_sincronizado", extra={"event": "repositorio_codigo_no_sincronizado", "motivo": str(exc)})
        return ResultadoSincronizacion(False, raiz_codigo_relativa(project_root), f"No se sincronizó: {exc}")


def main() -> int:
    resultado = sincronizar_desde_entorno()
    estado = "sincronizado" if resultado.sincronizado else "sin cambios"
    print(f"Repositorio del Asesor Técnico ({estado}): raíz {resultado.raiz}. {resultado.detalle}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
