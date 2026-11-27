"""Modelos puramente ficticios; no representan clientes ni pólizas reales."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum


class EstadoPoliza(StrEnum):
    BORRADOR = "borrador"
    VIGENTE = "vigente"
    VENCIDA = "vencida"
    CANCELADA = "cancelada"


@dataclass(frozen=True, slots=True)
class Cobertura:
    codigo: str
    nombre: str
    limite: Decimal
    deducible: Decimal = Decimal("0.00")


@dataclass(slots=True)
class Poliza:
    """Registro de ejemplo identificado por una clave sintética, sin PII."""

    numero_demo: str
    producto: str
    inicio: date
    fin: date
    prima: Decimal
    estado: EstadoPoliza = EstadoPoliza.BORRADOR
    coberturas: list[Cobertura] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Pago:
    referencia_demo: str
    numero_poliza_demo: str
    importe: Decimal
    fecha: date
    confirmado: bool


@dataclass(frozen=True, slots=True)
class Renovacion:
    numero_poliza_demo: str
    nueva_fecha_fin: date
    prima_propuesta: Decimal
