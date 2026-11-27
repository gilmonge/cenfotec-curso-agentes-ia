"""Barandas de la estructura del proyecto (ver docs/arquitectura.md).

Si una persona o una herramienta de IA agrega un agente y olvida una pieza, estas pruebas fallan con un mensaje
que dice qué falta. No se relajan para que pasen: se completa lo que falta.
"""
import ast
import json
import re
from pathlib import Path

import pytest

from agentes.analista.core.agent_registry import _TOOL_NAMESPACE, AgentId
from agentes.equipo import listar_definicion

RAIZ = Path(__file__).resolve().parents[4]
EQUIPO = RAIZ / "agentes" / "equipo"
DEFINICION = listar_definicion()
PLANTILLA_SERVIDOR = (EQUIPO / "analista" / "servidor_mcp.py").read_text(encoding="utf-8")


def test_cada_carpeta_del_equipo_es_un_agente_registrado():
    carpeta = {ruta.name for ruta in EQUIPO.iterdir() if ruta.is_dir() and not ruta.name.startswith(("_", "."))}
    assert carpeta == {definicion.id for definicion in DEFINICION}
    assert {agente.value for agente in AgentId} == carpeta


@pytest.mark.parametrize("definicion", DEFINICION, ids=lambda definicion: definicion.id)
def test_cada_agente_tiene_prompt_versionado_y_servidor_mcp_estandar(definicion):
    prompt = definicion.ruta_prompt.read_text(encoding="utf-8")
    assert re.search(r"^\*\*Versión editorial:\*\*\s*\d+\.\d+\.\d+", prompt, re.MULTILINE), \
        f"{definicion.id}/prompt.md debe declarar «**Versión editorial:** X.Y.Z»."
    assert definicion.ruta_servidor_mcp.read_text(encoding="utf-8") == PLANTILLA_SERVIDOR, \
        f"{definicion.id}/servidor_mcp.py debe ser igual al de los demás agentes (no se edita)."


@pytest.mark.parametrize("definicion", DEFINICION, ids=lambda definicion: definicion.id)
def test_las_herramientas_del_agente_existen_y_leen_solo_sus_namespaces(definicion):
    desconocida = definicion.herramienta - set(_TOOL_NAMESPACE)
    assert not desconocida, f"{definicion.id} declara herramientas que no existen: {sorted(desconocida)}"
    for herramienta in definicion.herramienta:
        assert _TOOL_NAMESPACE[herramienta].value in definicion.fuente, \
            f"{definicion.id} usa {herramienta} pero no declara el namespace {_TOOL_NAMESPACE[herramienta].value}."


def test_opencode_jsonc_coincide_con_el_registro():
    config = json.loads((RAIZ / "opencode.jsonc").read_text(encoding="utf-8"))
    assert set(config["agents"]) == {definicion.id for definicion in DEFINICION}
    for definicion in DEFINICION:
        agente = config["agents"][definicion.id]
        ruta = definicion.ruta_prompt.relative_to(RAIZ).as_posix()
        assert agente["system"] == f"{{file:./{ruta}}}"
        assert agente["mode"] == definicion.modo_opencode
        assert {"action": "*", "resource": "*", "effect": "deny"} in agente["permissions"]


@pytest.mark.parametrize("definicion", DEFINICION, ids=lambda definicion: definicion.id)
def test_el_servicio_del_agente_sigue_el_estandar_de_nombres(definicion):
    servicio = definicion.carpeta / f"{definicion.id}_service.py"
    assert servicio.is_file(), f"Falta {definicion.id}/{definicion.id}_service.py con la implementación del agente."
    if definicion.id == "analista":
        return  # el Analista es conversacional: su servicio expone run_turn
    clase = [nodo.name for nodo in ast.parse(servicio.read_text(encoding="utf-8")).body if isinstance(nodo, ast.ClassDef)]
    assert any(nombre.endswith("Service") for nombre in clase), \
        f"{servicio.name} debe definir una clase cuyo nombre termine en «Service»."


def test_la_ayuda_describe_a_cada_agente_del_equipo():
    ayuda = (RAIZ / "src" / "data" / "ayudaDocumentacion.js").read_text(encoding="utf-8")
    for definicion in DEFINICION:
        assert f"nombre: '{definicion.nombre}'" in ayuda, \
            f"La Ayuda (src/data/ayudaDocumentacion.js, AGENTES) no describe a «{definicion.nombre}»."


def test_las_skills_para_ia_son_iguales_en_ambas_carpetas():
    """Las guías para herramientas de IA existen en .agents/skills y en .claude/skills, sin diferencias."""
    lista_skill = ("agregar-agente", "agregar-ruta", "estructura-proyecto", "marca-diseno")
    for skill in lista_skill:
        agentes = RAIZ / ".agents" / "skills" / skill / "SKILL.md"
        claude = RAIZ / ".claude" / "skills" / skill / "SKILL.md"
        assert agentes.is_file() and claude.is_file(), f"Falta la skill «{skill}» en .agents/skills o .claude/skills."
        assert agentes.read_text(encoding="utf-8") == claude.read_text(encoding="utf-8"), \
            f"La skill «{skill}» difiere entre .agents/skills y .claude/skills."


def test_cada_intervencion_humana_del_backend_tiene_formulario_en_la_interfaz():
    from typing import get_args

    from agentes.analista.api.routes.workflows import WorkflowInterrupt

    tipo_backend = set(get_args(WorkflowInterrupt.model_fields["kind"].annotation))
    registro = (RAIZ / "src" / "flujo" / "interrupciones.jsx").read_text(encoding="utf-8")
    tipo_interfaz = set(re.findall(r"^  ([a-z_]+): \{$", registro, re.MULTILINE))
    assert tipo_backend == tipo_interfaz, \
        "Cada tipo de interrupción del backend necesita su entrada en src/flujo/interrupciones.jsx."


def test_la_interfaz_no_usa_cuadros_nativos_del_navegador():
    """Las confirmaciones y avisos usan el modal de la aplicación (useConfirmacion), no window.confirm/alert/prompt."""
    patron = re.compile(r"window\.(confirm|alert|prompt)\s*\(")
    infractor = [
        ruta.relative_to(RAIZ).as_posix()
        for ruta in (RAIZ / "src").rglob("*.js*")
        if "__tests__" not in ruta.parts and patron.search(ruta.read_text(encoding="utf-8"))
    ]
    assert not infractor, f"Usa useConfirmacion (src/components/Comun/ConfirmacionComponent.jsx) en: {infractor}"


# --- Marca «Ciruela corporativa» (docs/marca.md) ---------------------------------------------
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_HEX_PERMITIDO = {"#fff", "#ffffff", "#1a1a1a"}


def test_los_colores_de_la_marca_solo_se_definen_en_el_tema():
    """Un color nuevo va como variable en _theme.scss (claro y oscuro), no escrito en un estilo o componente."""
    fuera = []
    for ruta in list((RAIZ / "src").rglob("*.scss")) + list((RAIZ / "src").rglob("*.jsx")):
        relativa = ruta.relative_to(RAIZ).as_posix()
        if relativa in {"src/styles/_theme.scss", "src/styles/_variables.scss"} or "__tests__" in relativa:
            continue
        texto = ruta.read_text(encoding="utf-8")
        for valor in _HEX.findall(texto):
            if valor.lower() not in _HEX_PERMITIDO:
                fuera.append(f"{relativa}: {valor}")
    assert fuera == [], f"Colores fuera de src/styles/_theme.scss (use var(--color-…)): {fuera}"


def test_el_tema_claro_y_el_oscuro_definen_las_mismas_variables():
    tema = (RAIZ / "src" / "styles" / "_theme.scss").read_text(encoding="utf-8")
    claro, _, oscuro = tema.partition(":root[data-theme='dark']")
    variables = lambda bloque: set(re.findall(r"(--[a-z0-9-]+)\s*:", bloque))
    assert variables(claro) == variables(oscuro), "Cada variable de color necesita su par en modo oscuro."


def test_la_tipografia_es_inter_e_ibm_plex_mono():
    """Solo las dos familias de la marca, cargadas en index.html."""
    indice = (RAIZ / "index.html").read_text(encoding="utf-8")
    familias = set(re.findall(r"family=([A-Za-z+]+)", indice))
    assert familias == {"Inter", "IBM+Plex+Mono"}, f"Fuentes fuera de la marca: {familias}"
    for ruta in (RAIZ / "src").rglob("*.scss"):
        for familia in re.findall(r"font-family:\s*['\"]([^'\"]+)['\"]", ruta.read_text(encoding="utf-8")):
            assert familia in {"Inter", "IBM Plex Mono"}, f"{ruta.name} usa la fuente «{familia}»."


def test_cada_opcion_del_menu_tiene_etiqueta_corta_para_movil():
    rutas = (RAIZ / "src" / "config" / "rutas.jsx").read_text(encoding="utf-8")
    for menu in re.findall(r"menu: \{ (etiqueta[^}]*)\}", rutas):
        corta = re.search(r"corta: '([^']+)'", menu)
        assert corta, f"Falta «corta» en el menú: {menu.strip()[:60]}"
        assert len(corta.group(1)) <= 9, f"La etiqueta corta «{corta.group(1)}» supera 9 letras."
