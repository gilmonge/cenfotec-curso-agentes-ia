"""Operaciones en memoria para pólizas ficticias; sin persistencia externa."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from ejemplos.polizas_demo.modelos import EstadoPoliza, Poliza
from ejemplos.polizas_demo.servicios.validaciones import validar_poliza


def crear_poliza(numero_demo: str, producto: str, inicio: date, fin: date, prima: Decimal) -> Poliza:
    """Crea una póliza sintética en estado borrador después de validar sus datos."""
    poliza = Poliza(numero_demo, producto, inicio, fin, prima)
    validar_poliza(poliza)
    return poliza


def activar_poliza(poliza: Poliza) -> Poliza:
    """Activa un borrador válido sin guardar datos fuera del proceso."""
    validar_poliza(poliza)
    if poliza.estado != EstadoPoliza.BORRADOR:
        raise ValueError("Solo una póliza demo en borrador puede activarse.")
    poliza.estado = EstadoPoliza.VIGENTE
    return poliza
