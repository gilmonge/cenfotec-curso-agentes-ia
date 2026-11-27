"""Catálogo de acciones: lo único que hay que tocar para proteger una funcionalidad nueva.

Cada acción tiene un código (solo para el programa), un nombre que lee la persona en Mantenimiento
y el módulo donde se agrupa. Para agregar una acción:

1. Se agrega una línea en ``LISTA_ACCION``.
2. La ruta de la API que la usa declara ``requiere_accion(ACCION.X)``.
3. En el frontend, la ruta o el botón lleva ``accion: ACCION.X`` (``src/config/acciones.js``).

La pestaña Mantenimiento la muestra sola para asignarla a los roles. Las pruebas de estructura
revisan que cada ruta de la API declare su acción y que el catálogo del frontend sea el mismo.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace


@dataclass(frozen=True)
class Accion:
    codigo: str
    nombre: str
    modulo: str


MODULO_HISTORIA = "Historias de usuario"
MODULO_CAMBIO = "Cambios a historias aprobadas"
MODULO_LECCION = "Lecciones aprendidas"
MODULO_MANTENIMIENTO = "Mantenimiento"

LISTA_ACCION: tuple[Accion, ...] = (
    Accion("historia.ver", "Acceder a Historias de usuario", MODULO_HISTORIA),
    Accion("historia.crear", "Crear historia", MODULO_HISTORIA),
    Accion("historia.responder_negocio", "Responder las preguntas a negocio", MODULO_HISTORIA),
    Accion("historia.editar", "Editar historia", MODULO_HISTORIA),
    Accion("historia.aprobar", "Aprobar historia", MODULO_HISTORIA),
    Accion("historia.devolver", "Devolver historia para ajustes", MODULO_HISTORIA),
    Accion("historia.rechazar", "Rechazar historia", MODULO_HISTORIA),
    Accion("historia.eliminar", "Eliminar historia", MODULO_HISTORIA),
    Accion("historia.descartar_en_proceso", "Descartar historia en proceso", MODULO_HISTORIA),
    Accion("cambio.solicitar", "Solicitar cambio a una historia aprobada", MODULO_CAMBIO),
    Accion("cambio.decidir", "Decidir sobre un cambio", MODULO_CAMBIO),
    Accion("leccion.ver", "Acceder a Lecciones aprendidas", MODULO_LECCION),
    Accion("leccion.decidir", "Aprobar o rechazar lecciones", MODULO_LECCION),
    Accion("mantenimiento.ver", "Acceder a Mantenimiento", MODULO_MANTENIMIENTO),
    Accion("usuario.administrar", "Crear usuarios y asignarles roles", MODULO_MANTENIMIENTO),
    Accion("rol.administrar", "Crear roles y asignarles acciones", MODULO_MANTENIMIENTO),
)

# Acceso por nombre en el código: ACCION.HISTORIA_APROBAR == "historia.aprobar".
ACCION = SimpleNamespace(**{a.codigo.replace(".", "_").upper(): a.codigo for a in LISTA_ACCION})
CODIGO_ACCION = frozenset(a.codigo for a in LISTA_ACCION)
_POR_CODIGO = {a.codigo: a for a in LISTA_ACCION}


def accion_de(codigo: str) -> Accion:
    return _POR_CODIGO[codigo]


# Roles con los que arranca una base nueva. Después se administran en Mantenimiento.
ROL_ADMINISTRADOR = "Administrador"
LISTA_ROL_INICIAL: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (ROL_ADMINISTRADOR, "Administra usuarios y roles; tiene todas las acciones.", tuple(sorted(CODIGO_ACCION))),
    ("Analista de negocio", "Crea historias y responde las preguntas a negocio.", (
        ACCION.HISTORIA_VER, ACCION.HISTORIA_CREAR, ACCION.HISTORIA_RESPONDER_NEGOCIO, ACCION.HISTORIA_EDITAR,
        ACCION.HISTORIA_DESCARTAR_EN_PROCESO, ACCION.CAMBIO_SOLICITAR, ACCION.LECCION_VER,
    )),
    ("Product Owner", "Aprueba, devuelve o rechaza historias y decide los cambios.", (
        ACCION.HISTORIA_VER, ACCION.HISTORIA_APROBAR, ACCION.HISTORIA_DEVOLVER, ACCION.HISTORIA_RECHAZAR,
        ACCION.CAMBIO_DECIDIR, ACCION.LECCION_VER, ACCION.LECCION_DECIDIR,
    )),
    ("Consulta", "Solo consulta las historias.", (ACCION.HISTORIA_VER, ACCION.LECCION_VER)),
)
