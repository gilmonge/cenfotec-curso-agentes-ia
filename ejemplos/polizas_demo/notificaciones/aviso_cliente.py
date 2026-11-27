"""Arma los avisos de bienvenida por correo y por mensaje de texto (solo los construye, no los envía)."""
from __future__ import annotations

from dataclasses import dataclass

from ejemplos.polizas_demo.clientes.modelo_cliente import Cliente


@dataclass(frozen=True, slots=True)
class Aviso:
    canal: str
    destino: str
    texto: str


def construir_aviso_bienvenida(cliente: Cliente) -> list[Aviso]:
    """Todo cliente activo recibe correo y mensaje de texto; el número se envía con prefijo de país."""
    if not cliente.activo:
        return []
    saludo = f"Hola {cliente.nombre.split()[0]}, gracias por registrarse."
    return [
        Aviso("correo", cliente.correo, saludo),
        Aviso("sms", "+506" + cliente.telefono, saludo),
    ]
