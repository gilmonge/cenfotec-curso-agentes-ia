from datetime import date
from decimal import Decimal

import pytest

from ejemplos.polizas_demo.modelos import EstadoPoliza
from ejemplos.polizas_demo.servicios.coberturas import agregar_cobertura
from ejemplos.polizas_demo.servicios.pagos import registrar_pago_demo
from ejemplos.polizas_demo.servicios.polizas import activar_poliza, crear_poliza
from ejemplos.polizas_demo.servicios.primas import calcular_prima
from ejemplos.polizas_demo.servicios.renovaciones import proponer_renovacion
from ejemplos.polizas_demo.servicios.validaciones import validar_poliza


def test_fictional_policy_lifecycle_uses_only_local_demo_data():
    policy = crear_poliza(
        "DEMO-0001", "producto ficticio", date(2026, 1, 1), date(2027, 1, 1), Decimal("120.00")
    )
    agregar_cobertura(policy, "BASICA")
    assert calcular_prima(policy) == Decimal("220.00")
    activar_poliza(policy)
    renewal = proponer_renovacion(policy, date(2028, 1, 1), Decimal("0.05"))
    payment = registrar_pago_demo(policy, "PAGO-DEMO-1", Decimal("220.00"), date(2026, 1, 2))

    assert policy.estado == EstadoPoliza.VIGENTE
    assert renewal.prima_propuesta == Decimal("231.0000")
    assert payment.confirmado is True
    assert payment.numero_poliza_demo == "DEMO-0001"


@pytest.mark.parametrize(
    ("number", "start", "end", "premium"),
    [
        ("POL-1", date(2026, 1, 1), date(2027, 1, 1), Decimal("1.00")),
        ("DEMO-2", date(2027, 1, 1), date(2026, 1, 1), Decimal("1.00")),
        ("DEMO-3", date(2026, 1, 1), date(2027, 1, 1), Decimal("-1.00")),
    ],
)
def test_policy_validation_rejects_invalid_synthetic_records(number, start, end, premium):
    from ejemplos.polizas_demo.modelos import Poliza

    with pytest.raises(ValueError):
        validar_poliza(Poliza(number, "producto ficticio", start, end, premium))
