"""Repositorio de HU y lecciones aprendidas: la memoria de largo plazo del agente."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from agentes.analista.memory.repositorio import RepositorioError, RepositorioHU, detect_personal_data

router = APIRouter()

# Todos los identificadores son GUID.
_GUID = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

_Categoria = Literal[
    "Reglas de negocio", "Datos requeridos", "Validaciones", "Excepciones", "Comportamiento esperado",
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HistoriaIn(_Model):
    asA: str = Field(min_length=1, max_length=500)
    iWant: str = Field(min_length=1, max_length=500)
    soThat: str = Field(min_length=1, max_length=500)


class CriterioIn(_Model):
    text: str = Field(min_length=1, max_length=500)
    given: str = Field(default="", max_length=500)
    when: str = Field(default="", max_length=500)
    then: str = Field(default="", max_length=500)


class AclaracionIn(_Model):
    pregunta: str = Field(min_length=1, max_length=500)
    respuesta: str = Field(min_length=1, max_length=1000)


class HuIn(_Model):
    id: str = Field(pattern=_GUID)
    codigo: str = Field(default="", max_length=60)
    titulo: str = Field(min_length=1, max_length=200)
    tipo_informacion: str = Field(min_length=1, max_length=60)
    requerimiento: str = Field(min_length=1, max_length=4000)
    historia: HistoriaIn
    criterios: list[CriterioIn] = Field(max_length=20)
    aclaraciones: list[AclaracionIn] = Field(max_length=10)
    # El Product Owner confirma que la HU no contiene datos personales reales.
    confirmo_anonimizada: Literal[True]


class HuOut(_Model):
    id: str
    titulo: str
    aprobada_en: str


class CambioIn(_Model):
    hu_id: str = Field(pattern=_GUID)
    solicitud: str = Field(min_length=1, max_length=2000)
    clasificacion: Literal["aclaracion", "correccion", "cambio_alcance"]
    causa_raiz: _Categoria | None = None
    pregunta_sugerida: str | None = Field(default=None, min_length=1, max_length=500)
    terminos: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(default_factory=list, max_length=10)


class CambioOut(_Model):
    solicitud_id: str
    leccion_id: str | None = None
    estado: Literal["propuesta"] | None = None


class DecisionIn(_Model):
    decision: Literal["aprobar", "rechazar"]


def _repo(request: Request) -> RepositorioHU:
    return request.app.state.repositorio


def _reject_personal_data(*texts: str) -> None:
    findings = detect_personal_data(*texts)
    if findings:
        raise RepositorioError(
            "El texto parece contener datos personales (" + ", ".join(findings) + "). Anonimícelo antes de guardarlo."
        )


@router.post("/repositorio/historias", response_model=HuOut, status_code=status.HTTP_201_CREATED)
def guardar_historia(payload: HuIn, request: Request) -> dict:
    texts = [
        payload.titulo, payload.requerimiento, payload.historia.asA, payload.historia.iWant, payload.historia.soThat,
        *[c.text for c in payload.criterios], *[a.pregunta for a in payload.aclaraciones],
        *[a.respuesta for a in payload.aclaraciones],
    ]
    _reject_personal_data(*texts)
    data = payload.model_dump(exclude={"confirmo_anonimizada"})
    return _repo(request).guardar_hu(data)


@router.get("/repositorio/historias", response_model=list[HuOut])
def listar_historias(request: Request) -> list[dict]:
    return _repo(request).listar_hu()


@router.delete("/repositorio/historias/{hu_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_historia(hu_id: Annotated[str, Path(pattern=_GUID)], request: Request) -> Response:
    _repo(request).eliminar_hu(hu_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/repositorio/cambios", response_model=CambioOut, status_code=status.HTTP_201_CREATED)
def registrar_cambio(payload: CambioIn, request: Request) -> dict:
    _reject_personal_data(payload.solicitud, payload.pregunta_sugerida or "", *payload.terminos)
    return _repo(request).registrar_cambio(**payload.model_dump())


@router.get("/repositorio/cambios")
def listar_cambios(request: Request, hu_id: Annotated[str | None, Query(pattern=_GUID)] = None) -> list[dict]:
    return _repo(request).listar_cambios(hu_id)


@router.get("/repositorio/lecciones")
def listar_lecciones(
    request: Request,
    estado: Annotated[Literal["propuesta", "aprobada", "rechazada"] | None, Query()] = None,
) -> list[dict]:
    return _repo(request).listar_lecciones(estado)


@router.post("/repositorio/lecciones/{leccion_id}/decision")
def decidir_leccion(leccion_id: Annotated[str, Path(pattern=_GUID)], payload: DecisionIn, request: Request) -> dict:
    return _repo(request).decidir_leccion(leccion_id, payload.decision)
