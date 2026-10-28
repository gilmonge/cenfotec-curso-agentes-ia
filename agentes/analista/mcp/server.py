"""Run the read-only Analyst MCP server over stdio."""
import sys
from pathlib import Path

# FastMCP launches this file by path in a child process. Add the repository root
# so the package imports work even when the process starts outside the project.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agentes.analista.mcp.tools import mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
