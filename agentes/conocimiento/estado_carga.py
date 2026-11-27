"""Estado compartido de la carga automática del índice de conocimiento.

Mientras la carga inicial está en curso, el índice puede estar vacío o a medias: el
recuperador usa la copia local y lo marca como ``degraded``, en lugar de devolver
resultados incompletos de Pinecone como si fueran correctos.
"""
from __future__ import annotations

import threading

_lock = threading.Lock()
_carga_inicial_en_curso = False


def marcar_carga_inicial(en_curso: bool) -> None:
    global _carga_inicial_en_curso
    with _lock:
        _carga_inicial_en_curso = en_curso


def pinecone_disponible() -> bool:
    with _lock:
        return not _carga_inicial_en_curso
