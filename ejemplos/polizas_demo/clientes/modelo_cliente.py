"""Modelo ficticio de cliente; no representa personas reales."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Formato con el que se muestra y se recibe la fecha de nacimiento.
FORMATO_FECHA = "%d/%m/%Y"


@dataclass(slots=True)
class Cliente:
    codigo_demo: str
    nombre: str
    correo: str
    telefono: str
    fecha_nacimiento: date
    activo: bool = True
