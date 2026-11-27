"""Exportación «Clientes activos» a texto delimitado por punto y coma."""
from __future__ import annotations

from ejemplos.polizas_demo.clientes.modelo_cliente import FORMATO_FECHA, Cliente

ENCABEZADO = ("CODIGO", "NOMBRE", "CORREO", "TELEFONO", "FECHA_NACIMIENTO")


def _telefono_con_guion(telefono: str) -> str:
    return f"{telefono[:4]}-{telefono[4:]}"


def exportar_cliente(lista_cliente: list[Cliente]) -> str:
    lista_linea = [";".join(ENCABEZADO)]
    for cliente in lista_cliente:
        if not cliente.activo:
            continue
        lista_linea.append(";".join((
            cliente.codigo_demo,
            cliente.nombre,
            cliente.correo,
            _telefono_con_guion(cliente.telefono),
            cliente.fecha_nacimiento.strftime(FORMATO_FECHA),
        )))
    return "\n".join(lista_linea)
