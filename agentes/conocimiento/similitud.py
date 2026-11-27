"""Similitud por significado entre textos cortos, con el mismo modelo de embeddings de Pinecone.

Se usa para detectar que el Analista vuelve a reportar, con otras palabras, un punto que Negocio ya
respondió. Todos los textos se envían en una sola llamada por turno. Si Pinecone no está configurado,
falla o tarda demasiado, devuelve ``None`` y quien llama decide sin similitud.
"""
from __future__ import annotations

import logging
import math
import os
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturoTimeoutError

from .contract import DEFAULT_INDEX_CONTRACT

logger = logging.getLogger(__name__)

TIEMPO_MAXIMO_SEGUNDOS = 8.0
_ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="similitud")

Vectorizador = Callable[[list[str]], list[list[float]]]


def _vectorizar_con_pinecone(lista_texto: list[str]) -> list[list[float]]:
    from langchain_pinecone import PineconeEmbeddings

    modelo = PineconeEmbeddings(
        model=os.environ.get("PINECONE_EMBEDDING_MODEL", DEFAULT_INDEX_CONTRACT.embedding_model),
        dimension=DEFAULT_INDEX_CONTRACT.dimension,
        pinecone_api_key=os.environ["PINECONE_API_KEY"],
    )
    return modelo.embed_documents(lista_texto)


def _coseno(primero: Sequence[float], segundo: Sequence[float]) -> float:
    producto = sum(a * b for a, b in zip(primero, segundo))
    norma = math.sqrt(sum(a * a for a in primero)) * math.sqrt(sum(b * b for b in segundo))
    return producto / norma if norma else 0.0


def similitud_maxima(
    lista_punto: Sequence[str],
    lista_referencia: Sequence[str],
    *,
    vectorizador: Vectorizador | None = None,
    tiempo_maximo: float = TIEMPO_MAXIMO_SEGUNDOS,
) -> list[float] | None:
    """Para cada punto, la similitud más alta (coseno) contra las referencias; ``None`` si no se pudo medir."""
    if not lista_punto:
        return []
    if not lista_referencia:
        return [0.0] * len(lista_punto)
    if vectorizador is None:
        if not os.environ.get("PINECONE_API_KEY"):
            logger.info("Similitud no disponible: falta PINECONE_API_KEY.")
            return None
        vectorizador = _vectorizar_con_pinecone
    texto = [*lista_punto, *lista_referencia]
    try:
        vector = _ejecutor.submit(vectorizador, texto).result(timeout=tiempo_maximo)
    except FuturoTimeoutError:
        logger.warning("Similitud no disponible: Pinecone tardó más de %.1f s.", tiempo_maximo)
        return None
    except Exception as exc:  # El servicio externo puede fallar de muchas formas; se registra y se sigue sin similitud.
        logger.warning("Similitud no disponible: %s", type(exc).__name__)
        return None
    if len(vector) != len(texto):
        logger.warning("Similitud no disponible: Pinecone devolvió %d vectores para %d textos.", len(vector), len(texto))
        return None
    vector_punto, vector_referencia = vector[: len(lista_punto)], vector[len(lista_punto):]
    return [max(_coseno(punto, referencia) for referencia in vector_referencia) for punto in vector_punto]
