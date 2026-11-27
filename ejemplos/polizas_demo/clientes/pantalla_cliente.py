"""Pantalla «Datos del cliente»: campos, formato y validaciones al guardar."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from ejemplos.polizas_demo.clientes.modelo_cliente import FORMATO_FECHA, Cliente

EDAD_MINIMA = 18
_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CampoPantalla:
    nombre: str
    etiqueta: str
    obligatorio: bool


CAMPO_PANTALLA: tuple[CampoPantalla, ...] = (
    CampoPantalla("nombre", "Nombre completo", True),
    CampoPantalla("correo", "Correo electrónico", True),
    CampoPantalla("telefono", "Teléfono", True),
    CampoPantalla("fecha_nacimiento", "Fecha de nacimiento (dd/mm/aaaa)", True),
)


def leer_fecha_nacimiento(texto: str) -> date:
    return datetime.strptime(texto.strip(), FORMATO_FECHA).date()


def mostrar_fecha_nacimiento(cliente: Cliente) -> str:
    return cliente.fecha_nacimiento.strftime(FORMATO_FECHA)


def validar_cliente(cliente: Cliente, fecha_referencia: date) -> list[str]:
    """Devuelve los mensajes de validación; la lista vacía significa que se puede guardar."""
    lista_error: list[str] = []
    if not cliente.nombre.strip():
        lista_error.append("El nombre es obligatorio.")
    if not _CORREO.match(cliente.correo):
        lista_error.append("El correo electrónico no tiene un formato válido.")
    if len(cliente.telefono) != 8 or not cliente.telefono.isdigit():
        lista_error.append("El teléfono es obligatorio y debe tener 8 dígitos.")
    edad = fecha_referencia.year - cliente.fecha_nacimiento.year - (
        (fecha_referencia.month, fecha_referencia.day) < (cliente.fecha_nacimiento.month, cliente.fecha_nacimiento.day)
    )
    if edad < EDAD_MINIMA:
        lista_error.append(f"El cliente debe ser mayor de {EDAD_MINIMA} años.")
    return lista_error
