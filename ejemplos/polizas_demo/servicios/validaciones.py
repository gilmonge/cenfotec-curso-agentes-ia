"""Validaciones deterministas para los datos ficticios de pólizas."""
from ejemplos.polizas_demo.modelos import Poliza


def validar_poliza(poliza: Poliza) -> None:
    """Valida estructura y fechas sin consultar catálogos o servicios externos."""
    if not poliza.numero_demo.startswith("DEMO-"):
        raise ValueError("El número de póliza debe usar el prefijo sintético DEMO-.")
    if not poliza.producto.strip():
        raise ValueError("El producto demo es obligatorio.")
    if poliza.inicio >= poliza.fin:
        raise ValueError("La fecha final debe ser posterior a la inicial.")
    if poliza.prima < 0:
        raise ValueError("La prima demo no puede ser negativa.")
