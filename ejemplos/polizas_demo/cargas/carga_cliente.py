"""Carga masiva de clientes desde la plantilla de archivo «Clientes - Carga»."""
from __future__ import annotations

from datetime import datetime

from ejemplos.polizas_demo.clientes.modelo_cliente import Cliente

# Columna del archivo → atributo del cliente. Los nombres de columna son los de la plantilla publicada.
MAPEO_COLUMNA = {
    "NOMBRE": "nombre",
    "EMAIL": "correo",
    "TEL": "telefono",
    "FNAC": "fecha_nacimiento",
}
COLUMNA_OBLIGATORIA = ("NOMBRE", "EMAIL", "TEL", "FNAC")


def procesar_fila(codigo_demo: str, fila: dict[str, str]) -> Cliente:
    """Convierte una fila en cliente; rechaza la fila si falta una columna obligatoria."""
    lista_faltante = [columna for columna in COLUMNA_OBLIGATORIA if not fila.get(columna, "").strip()]
    if lista_faltante:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(lista_faltante)}")
    tel = "".join(caracter for caracter in fila["TEL"] if caracter.isdigit())
    if len(tel) != 8:
        raise ValueError("TEL debe tener 8 dígitos.")
    return Cliente(
        codigo_demo=codigo_demo,
        nombre=fila["NOMBRE"].strip(),
        correo=fila["EMAIL"].strip().lower(),
        telefono=tel,
        fecha_nacimiento=datetime.strptime(fila["FNAC"].strip(), "%d/%m/%Y").date(),
    )
