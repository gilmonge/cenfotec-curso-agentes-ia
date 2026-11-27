"""Catálogo y asociación local de coberturas de demostración."""
from __future__ import annotations

from decimal import Decimal

from ejemplos.polizas_demo.modelos import Cobertura, Poliza


CATALOGO_DEMO = {
    "BASICA": Cobertura("BASICA", "Cobertura básica demo", Decimal("10000.00"), Decimal("250.00")),
    "ASISTENCIA": Cobertura("ASISTENCIA", "Asistencia demo", Decimal("500.00")),
}


def agregar_cobertura(poliza: Poliza, codigo: str) -> Poliza:
    """Agrega una cobertura ficticia del catálogo en memoria."""
    if codigo not in CATALOGO_DEMO:
        raise ValueError("La cobertura demo no existe.")
    if any(item.codigo == codigo for item in poliza.coberturas):
        raise ValueError("La cobertura demo ya está asociada.")
    poliza.coberturas.append(CATALOGO_DEMO[codigo])
    return poliza
