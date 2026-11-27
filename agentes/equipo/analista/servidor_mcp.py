"""Servidor MCP (stdio, solo lectura) de este agente. Es igual en todas las carpetas: no se edita.

Las herramientas salen de la definición del agente (``definicion.py``). FastMCP lo arranca por ruta en un
proceso aparte, por eso agrega la raíz del proyecto al path antes de importar.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agentes.analista.mcp.tools import servidor_del_agente  # noqa: E402

AGENTE = Path(__file__).resolve().parent.name


def main() -> None:
    servidor_del_agente(AGENTE).run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
