"""Exportar e importar el punto de control de un workflow de LangGraph para guardarlo en la base de datos.

El grafo trabaja con ``InMemorySaver`` (rápido y sin dependencias). Cuando el flujo se detiene a esperar a
una persona, o falla, el runtime exporta el último punto de control del hilo y lo guarda en la tabla
``workflow_guardado``. Si el proceso se reinicia (por ejemplo, Render duerme el servicio), el hilo se
importa de nuevo y el flujo continúa donde quedó.

Solo se guarda el **último** punto de control con sus valores y sus escrituras pendientes (entre ellas la
interrupción que espera a la persona): es lo único que LangGraph necesita para reanudar o reintentar.
La prueba ``test_workflow_persistencia.py`` verifica el viaje completo contra la versión instalada de
LangGraph, porque este módulo depende de la estructura interna de ``InMemorySaver``.
"""
from __future__ import annotations

import base64
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

VERSION_FORMATO = 1


def _codificar(tipado: tuple[str, bytes]) -> list[str]:
    tipo, datos = tipado
    return [tipo, base64.b64encode(datos).decode("ascii")]


def _decodificar(valor: list[str]) -> tuple[str, bytes]:
    tipo, datos = valor
    return tipo, base64.b64decode(datos.encode("ascii"))


def exportar_hilo(saver: InMemorySaver, thread_id: str) -> dict[str, Any] | None:
    """El último punto de control del hilo, en un diccionario apto para JSON; ``None`` si no hay."""
    espacio = saver.storage.get(thread_id)
    if not espacio:
        return None
    salida: dict[str, Any] = {"v": VERSION_FORMATO, "ns": {}}
    for checkpoint_ns, punto in espacio.items():
        if not punto:
            continue
        checkpoint_id = max(punto.keys())
        checkpoint_tipado, metadata_tipada, padre = punto[checkpoint_id]
        checkpoint = saver.serde.loads_typed(checkpoint_tipado)
        blob = []
        for canal, version in checkpoint.get("channel_versions", {}).items():
            valor = saver.blobs.get((thread_id, checkpoint_ns, canal, version))
            if valor is not None:
                blob.append([canal, version, _codificar(valor)])
        escritura = [
            [llave[0], llave[1], valor[0], valor[1], _codificar(valor[2]), valor[3]]
            for llave, valor in saver.writes.get((thread_id, checkpoint_ns, checkpoint_id), {}).items()
        ]
        salida["ns"][checkpoint_ns] = {
            "checkpoint_id": checkpoint_id,
            "checkpoint": _codificar(checkpoint_tipado),
            "metadata": _codificar(metadata_tipada),
            "padre": padre,
            "blob": blob,
            "escritura": escritura,
        }
    return salida if salida["ns"] else None


def importar_hilo(saver: InMemorySaver, thread_id: str, datos: dict[str, Any]) -> None:
    """Carga en memoria un punto de control exportado con :func:`exportar_hilo`."""
    if datos.get("v") != VERSION_FORMATO:
        raise ValueError("El punto de control guardado tiene un formato desconocido.")
    for checkpoint_ns, punto in datos["ns"].items():
        checkpoint_id = punto["checkpoint_id"]
        saver.storage[thread_id][checkpoint_ns][checkpoint_id] = (
            _decodificar(punto["checkpoint"]),
            _decodificar(punto["metadata"]),
            punto["padre"],
        )
        for canal, version, valor in punto["blob"]:
            saver.blobs[(thread_id, checkpoint_ns, canal, version)] = _decodificar(valor)
        escritura = saver.writes[(thread_id, checkpoint_ns, checkpoint_id)]
        for task_id, indice, task_id_valor, canal, valor, ruta in punto["escritura"]:
            escritura[(task_id, indice)] = (task_id_valor, canal, _decodificar(valor), ruta)
