"""El flujo se declara como tabla de pasos; la tabla se valida antes de compilar el grafo."""
from typing import TypedDict

import pytest

from agentes.analista.core.flujo import FIN, FlujoInvalidoError, Paso, Ruta, construir_flujo


class _Estado(TypedDict, total=False):
    valor: int


def _nodo(_state):
    return {}


INICIO = Ruta(lambda _state: "a", {"a": "a"})


def test_una_tabla_valida_compila_y_recorre_los_pasos():
    lista_paso = [
        Paso("a", lambda state: {"valor": 1}, "b"),
        Paso("b", lambda state: {"valor": state["valor"] + 1},
             Ruta(lambda state: "fin" if state["valor"] >= 2 else "otra", {"fin": FIN, "otra": "a"})),
    ]
    grafo = construir_flujo(_Estado, INICIO, lista_paso, checkpointer=None)
    assert grafo.invoke({})["valor"] == 2


@pytest.mark.parametrize(("lista_paso", "mensaje"), [
    ([Paso("a", _nodo, FIN), Paso("a", _nodo, FIN)], "repetidos"),
    ([Paso("a", _nodo, "no_existe")], "no existen"),
    ([Paso("a", _nodo, FIN), Paso("huerfano", _nodo, FIN)], "nunca se llega"),
])
def test_la_tabla_invalida_se_rechaza_con_un_mensaje_claro(lista_paso, mensaje):
    with pytest.raises(FlujoInvalidoError, match=mensaje):
        construir_flujo(_Estado, INICIO, lista_paso, checkpointer=None)


def test_el_flujo_real_es_valido():
    from agentes.analista.core.workflow_graph import build_workflow_graph

    assert build_workflow_graph() is not None
