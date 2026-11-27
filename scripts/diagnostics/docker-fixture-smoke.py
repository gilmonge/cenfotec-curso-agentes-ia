"""Smoke test para comprobar el fixture ficticio en una imagen Docker construida."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "ejemplos" / "polizas_demo"
REQUIRED_FILES = (
    "modelos.py",
    "servicios/polizas.py",
    "servicios/primas.py",
    "servicios/coberturas.py",
    "servicios/renovaciones.py",
    "servicios/pagos.py",
    "servicios/validaciones.py",
    "mapa_dependencias.md",
    "clientes/modelo_cliente.py",
    "clientes/pantalla_cliente.py",
    "notificaciones/aviso_cliente.py",
    "reportes/exportacion_cliente.py",
    "cargas/carga_cliente.py",
)


def main() -> None:
    if not FIXTURE.is_dir():
        raise SystemExit("Falta el directorio de fixtures ficticios en la imagen.")
    for relative in REQUIRED_FILES:
        path = FIXTURE / relative
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            raise SystemExit(f"El archivo del fixture no se puede leer: {relative}") from None
        if not content.strip():
            raise SystemExit(f"El archivo del fixture está vacío: {relative}")
    print(f"docker_fixture_smoke=passed files={len(REQUIRED_FILES)} root={FIXTURE}")


if __name__ == "__main__":
    main()
