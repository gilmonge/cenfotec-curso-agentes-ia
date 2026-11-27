"""Propuesta local de renovación para una póliza ficticia."""
from datetime import date
from decimal import Decimal

from ejemplos.polizas_demo.modelos import EstadoPoliza, Poliza, Renovacion
from ejemplos.polizas_demo.servicios.primas import calcular_prima
from ejemplos.polizas_demo.servicios.validaciones import validar_poliza


def proponer_renovacion(poliza: Poliza, nueva_fecha_fin: date, ajuste_demo: Decimal = Decimal("0.05")) -> Renovacion:
    """Devuelve una propuesta ilustrativa, sin renovar ni modificar la póliza."""
    validar_poliza(poliza)
    if poliza.estado != EstadoPoliza.VIGENTE:
        raise ValueError("Solo se puede proponer la renovación de una póliza vigente.")
    if nueva_fecha_fin <= poliza.fin or ajuste_demo < Decimal("-1"):
        raise ValueError("La fecha o ajuste demo de renovación no es válido.")
    prima_actual = calcular_prima(poliza)
    return Renovacion(poliza.numero_demo, nueva_fecha_fin, prima_actual * (Decimal("1") + ajuste_demo))
