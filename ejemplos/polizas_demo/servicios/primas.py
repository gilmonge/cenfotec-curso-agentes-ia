"""Cálculo ilustrativo de primas; no es una tarifa actuarial."""
from decimal import Decimal, ROUND_HALF_UP

from ejemplos.polizas_demo.modelos import Poliza


def calcular_prima(poliza: Poliza, factor_demo: Decimal = Decimal("1.00")) -> Decimal:
    """Suma cargos ficticios de cobertura y redondea a dos decimales."""
    if factor_demo <= 0:
        raise ValueError("El factor demo debe ser positivo.")
    base = sum((cobertura.limite / Decimal("100") for cobertura in poliza.coberturas), Decimal("0"))
    return (poliza.prima + base * factor_demo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
