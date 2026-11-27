"""Registro de pagos ficticios en memoria, sin pasarela ni movimiento de fondos."""
from datetime import date
from decimal import Decimal

from ejemplos.polizas_demo.modelos import Pago, Poliza


def registrar_pago_demo(poliza: Poliza, referencia_demo: str, importe: Decimal, fecha: date) -> Pago:
    """Construye un recibo simulado; no contacta bancos ni proveedores."""
    if importe <= 0:
        raise ValueError("El importe demo debe ser positivo.")
    return Pago(referencia_demo, poliza.numero_demo, importe, fecha, confirmado=True)
