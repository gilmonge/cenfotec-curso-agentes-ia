"""Memoria de largo plazo del Agente Analista: Repositorio de HU, lecciones aprendidas e historias de trabajo.

Se guarda en una base MySQL compatible (TiDB Cloud Starter en Render) o, en local y en pruebas, en SQLite.
Contiene lo que una persona aprobó (HU anonimizadas y lecciones aprobadas) y las historias de trabajo del
equipo, compartidas entre dispositivos. El agente solo lee; las escrituras llegan por la API.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column, ForeignKey, Index, Integer, MetaData, String, Table, Text, delete, insert, select, update,
)
from sqlalchemy.dialects import mysql
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from agentes.analista.memory.base_datos import crear_motor, ruta_sqlite_por_defecto, url_desde_entorno

logger = logging.getLogger(__name__)

CATEGORIAS = (
    "Reglas de negocio",
    "Datos requeridos",
    "Validaciones",
    "Excepciones",
    "Comportamiento esperado",
)
CLASIFICACIONES = ("aclaracion", "correccion", "cambio_alcance")
ESTADOS_LECCION = ("propuesta", "aprobada", "rechazada")

# Texto largo: MEDIUMTEXT en MySQL/TiDB (16 MB), TEXT en SQLite.
_Largo = Text().with_variant(mysql.MEDIUMTEXT(), "mysql")

# Todas las llaves primarias y foráneas son GUID (texto de 36 caracteres) generados por la aplicación.
_GUID = String(36)
_PATRON_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def nuevo_guid() -> str:
    return str(uuid.uuid4())


def es_guid(valor: object) -> bool:
    return isinstance(valor, str) and bool(_PATRON_GUID.match(valor))


_metadata = MetaData()
# Historias de trabajo del equipo (borradores, en análisis, revisadas): un documento JSON por historia.
historia = Table(
    "historia", _metadata,
    Column("id", _GUID, primary_key=True),
    Column("codigo", String(60)),  # número legible de la plantilla (por ejemplo HU-ABC-001)
    Column("datos", _Largo, nullable=False),
    Column("creada_en", String(40), nullable=False),
    Column("actualizada_en", String(40), nullable=False),
    Index("ix_historia_codigo", "codigo"),
)
# Repositorio de HU: la versión aprobada y anonimizada. Su id es el mismo GUID de la historia de trabajo.
hu_aprobada = Table(
    "hu_aprobada", _metadata,
    Column("id", _GUID, primary_key=True),
    Column("codigo", String(60)),  # código legible de la HU (HU-CODIGO-001); distinto del id
    Column("titulo", String(200), nullable=False),
    Column("tipo_informacion", String(60), nullable=False),
    Column("requerimiento", _Largo, nullable=False),
    Column("historia", _Largo, nullable=False),
    Column("criterios", _Largo, nullable=False),
    Column("aclaraciones", _Largo, nullable=False),
    Column("aprobada_en", String(40), nullable=False),
)
solicitud_cambio = Table(
    "solicitud_cambio", _metadata,
    Column("id", _GUID, primary_key=True),
    Column("hu_id", _GUID, ForeignKey("hu_aprobada.id", name="fk_solicitud_cambio_hu_aprobada"), nullable=False),
    Column("solicitud", _Largo, nullable=False),
    Column("clasificacion", String(20), nullable=False),
    Column("causa_raiz", String(60), nullable=False),
    Column("creada_en", String(40), nullable=False),
    Index("ix_solicitud_cambio_hu", "hu_id"),
)
leccion = Table(
    "leccion", _metadata,
    Column("id", _GUID, primary_key=True),
    Column("codigo", String(20), nullable=False),  # código legible consecutivo (LEC-001); distinto del id
    Column("solicitud_id", _GUID, ForeignKey("solicitud_cambio.id", name="fk_leccion_solicitud_cambio"), nullable=False),
    Column("hu_id", _GUID, nullable=False),
    Column("categoria", String(60), nullable=False),
    Column("pregunta_sugerida", _Largo, nullable=False),
    Column("terminos", _Largo, nullable=False),
    Column("estado", String(20), nullable=False),
    Column("creada_en", String(40), nullable=False),
    Column("decidida_en", String(40)),
    Index("ix_leccion_estado", "estado"),
    Index("ix_leccion_hu", "hu_id"),
)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_DIGITS = re.compile(r"(?<![\d.,])\d{9,}(?![\d.,])")
_ID_PATTERN = re.compile(r"\b\d-\d{4}-\d{4}\b")


class RepositorioError(Exception):
    """Error de dominio del repositorio (no encontrado o valor no permitido)."""

    def __init__(self, message: str, *, not_found: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.not_found = not_found


def detect_personal_data(*texts: str) -> list[str]:
    """Avisa de patrones evidentes de datos personales; no sustituye la anonimización humana."""
    findings: list[str] = []
    joined = "\n".join(texts)
    if _EMAIL.search(joined):
        findings.append("correo electrónico")
    if _LONG_DIGITS.search(joined) or _ID_PATTERN.search(joined):
        findings.append("número largo parecido a una identificación o teléfono")
    return findings


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[^\W_]+", value.casefold(), flags=re.UNICODE) if len(token) > 2]


def _verificar_esquema(motor) -> None:
    """Detiene el arranque con un mensaje claro si la base conserva el esquema anterior (ids numéricos)."""
    inspector = inspect(motor)
    for tabla in ("leccion", "solicitud_cambio"):
        if not inspector.has_table(tabla):
            continue
        columna = next((c for c in inspector.get_columns(tabla) if c["name"] == "id"), None)
        if columna is not None and not isinstance(columna["type"], (String, Text)) and "CHAR" not in str(columna["type"]).upper():
            raise RuntimeError(
                "La base de datos tiene el esquema anterior (ids numéricos). Elimine las tablas historia, leccion, "
                "solicitud_cambio y hu_aprobada para que se creen de nuevo con ids GUID (ver DESPLIEGUE.md)."
            )


def _siguiente_codigo_leccion(conexion) -> str:
    """Código legible consecutivo de la lección (LEC-001, LEC-002, ...)."""
    mayor = 0
    for (codigo,) in conexion.execute(select(leccion.c.codigo)):
        coincidencia = re.fullmatch(r"LEC-(\d+)", codigo or "")
        if coincidencia:
            mayor = max(mayor, int(coincidencia.group(1)))
    return f"LEC-{mayor + 1:03d}"


class RepositorioHU:
    def __init__(self, fuente: str | Path | None = None) -> None:
        """``fuente``: URL de base de datos, ruta de archivo SQLite o None (usa DATABASE_URL / SQLite local)."""
        self.fuente = str(fuente) if fuente is not None else url_desde_entorno()
        self.motor = crear_motor(fuente)
        _verificar_esquema(self.motor)
        _metadata.create_all(self.motor)

    # --- HU aprobadas -------------------------------------------------
    def guardar_hu(self, hu: dict[str, Any]) -> dict[str, Any]:
        aprobada_en = _now()
        valores = {
            "codigo": (str(hu.get("codigo") or "").strip()[:60] or None),
            "titulo": hu["titulo"], "tipo_informacion": hu["tipo_informacion"], "requerimiento": hu["requerimiento"],
            "historia": json.dumps(hu["historia"], ensure_ascii=False),
            "criterios": json.dumps(hu["criterios"], ensure_ascii=False),
            "aclaraciones": json.dumps(hu["aclaraciones"], ensure_ascii=False),
            "aprobada_en": aprobada_en,
        }
        with self.motor.begin() as conexion:
            existe = conexion.execute(select(hu_aprobada.c.id).where(hu_aprobada.c.id == hu["id"])).first()
            if existe:
                conexion.execute(update(hu_aprobada).where(hu_aprobada.c.id == hu["id"]).values(**valores))
            else:
                conexion.execute(insert(hu_aprobada).values(id=hu["id"], **valores))
        return {"id": hu["id"], "titulo": hu["titulo"], "aprobada_en": aprobada_en}

    def listar_hu(self) -> list[dict[str, Any]]:
        consulta = select(hu_aprobada.c.id, hu_aprobada.c.titulo, hu_aprobada.c.aprobada_en).order_by(
            hu_aprobada.c.aprobada_en.desc())
        with self.motor.connect() as conexion:
            return [dict(fila._mapping) for fila in conexion.execute(consulta)]

    def obtener_hu(self, hu_id: str) -> dict[str, Any]:
        with self.motor.connect() as conexion:
            fila = conexion.execute(select(hu_aprobada).where(hu_aprobada.c.id == hu_id)).first()
        if fila is None:
            raise RepositorioError("La HU no está en el Repositorio de HU.", not_found=True)
        return dict(fila._mapping)

    def eliminar_hu(self, hu_id: str) -> None:
        """Elimina la HU y, con ella, sus solicitudes de cambio y lecciones (una sola transacción)."""
        with self.motor.begin() as conexion:
            conexion.execute(delete(leccion).where(leccion.c.hu_id == hu_id))
            conexion.execute(delete(solicitud_cambio).where(solicitud_cambio.c.hu_id == hu_id))
            borradas = conexion.execute(delete(hu_aprobada).where(hu_aprobada.c.id == hu_id)).rowcount
        if borradas == 0:
            raise RepositorioError("La HU no está en el Repositorio de HU.", not_found=True)

    # --- Solicitudes de cambio y lecciones -----------------------------
    def registrar_cambio(
        self, *, hu_id: str, solicitud: str, clasificacion: str, causa_raiz: str,
        pregunta_sugerida: str | None = None, terminos: list[str] | None = None,
    ) -> dict[str, Any]:
        """Registra la solicitud; solo genera lección si trae la pregunta que debió hacerse.

        Cuando Negocio simplemente cambia de decisión no hubo un vacío del análisis y no hay lección que aprender.
        Las clasificaciones "aclaracion" y "correccion" se conservan solo para leer solicitudes registradas antes.
        """
        if clasificacion not in CLASIFICACIONES:
            raise RepositorioError("Clasificación no permitida.")
        pregunta_sugerida = (pregunta_sugerida or "").strip()
        con_leccion = clasificacion != "correccion" and bool(pregunta_sugerida)
        if con_leccion and causa_raiz not in CATEGORIAS:
            raise RepositorioError("La causa raíz debe ser una categoría del checklist de vacíos.")
        causa_raiz = causa_raiz if con_leccion else ""
        self.obtener_hu(hu_id)
        creada_en = _now()
        with self.motor.begin() as conexion:
            solicitud_id = nuevo_guid()
            conexion.execute(insert(solicitud_cambio).values(
                id=solicitud_id, hu_id=hu_id, solicitud=solicitud, clasificacion=clasificacion,
                causa_raiz=causa_raiz, creada_en=creada_en,
            ))
            if not con_leccion:
                return {"solicitud_id": solicitud_id, "leccion_id": None, "estado": None}
            leccion_id = nuevo_guid()
            conexion.execute(insert(leccion).values(
                id=leccion_id, codigo=_siguiente_codigo_leccion(conexion), solicitud_id=solicitud_id, hu_id=hu_id,
                categoria=causa_raiz, pregunta_sugerida=pregunta_sugerida,
                terminos=json.dumps(terminos or [], ensure_ascii=False), estado="propuesta", creada_en=creada_en,
            ))
        return {"solicitud_id": solicitud_id, "leccion_id": leccion_id, "estado": "propuesta"}

    def listar_cambios(self, hu_id: str | None = None) -> list[dict[str, Any]]:
        consulta = select(
            solicitud_cambio, leccion.c.id.label("leccion_id"), leccion.c.estado.label("leccion_estado"),
        ).select_from(solicitud_cambio.outerjoin(leccion, leccion.c.solicitud_id == solicitud_cambio.c.id))
        if hu_id:
            consulta = consulta.where(solicitud_cambio.c.hu_id == hu_id)
        with self.motor.connect() as conexion:
            return [dict(fila._mapping) for fila in conexion.execute(consulta.order_by(solicitud_cambio.c.creada_en.desc(), solicitud_cambio.c.id.desc()))]

    def listar_lecciones(self, estado: str | None = None) -> list[dict[str, Any]]:
        if estado is not None and estado not in ESTADOS_LECCION:
            raise RepositorioError("Estado de lección no permitido.")
        consulta = select(leccion, hu_aprobada.c.codigo.label("hu_codigo")).select_from(
            leccion.outerjoin(hu_aprobada, hu_aprobada.c.id == leccion.c.hu_id))
        if estado:
            consulta = consulta.where(leccion.c.estado == estado)
        with self.motor.connect() as conexion:
            filas = conexion.execute(consulta.order_by(leccion.c.creada_en.desc(), leccion.c.id.desc())).all()
        resultado = []
        for fila in filas:
            item = dict(fila._mapping)
            item["terminos"] = json.loads(item["terminos"])
            resultado.append(item)
        return resultado

    def decidir_leccion(self, leccion_id: str, decision: str) -> dict[str, Any]:
        estado = {"aprobar": "aprobada", "rechazar": "rechazada"}.get(decision)
        if estado is None:
            raise RepositorioError("La decisión debe ser aprobar o rechazar.")
        with self.motor.begin() as conexion:
            if conexion.execute(select(leccion.c.id).where(leccion.c.id == leccion_id)).first() is None:
                raise RepositorioError("La lección no existe.", not_found=True)
            conexion.execute(update(leccion).where(leccion.c.id == leccion_id).values(estado=estado, decidida_en=_now()))
        return next(item for item in self.listar_lecciones() if item["id"] == leccion_id)

    # --- Historias de trabajo (compartidas entre dispositivos) -----------
    def listar_historias(self) -> list[dict[str, Any]]:
        consulta = select(historia.c.datos).order_by(historia.c.creada_en.desc(), historia.c.id.desc())
        with self.motor.connect() as conexion:
            filas = conexion.execute(consulta).all()
        return [json.loads(fila.datos) for fila in filas]

    def guardar_historia(self, historia_id: str, datos: dict[str, Any]) -> dict[str, Any]:
        """Crea o reemplaza la historia (última escritura gana)."""
        ahora = _now()
        texto = json.dumps(datos, ensure_ascii=False)
        codigo = (str(datos.get("number") or "").strip() or None)
        codigo = codigo[:60] if codigo else None
        with self.motor.begin() as conexion:
            existe = conexion.execute(select(historia.c.id).where(historia.c.id == historia_id)).first()
            if existe:
                conexion.execute(update(historia).where(historia.c.id == historia_id).values(
                    codigo=codigo, datos=texto, actualizada_en=ahora))
            else:
                conexion.execute(insert(historia).values(
                    id=historia_id, codigo=codigo, datos=texto, creada_en=ahora, actualizada_en=ahora))
        return datos

    def eliminar_historia(self, historia_id: str) -> None:
        with self.motor.begin() as conexion:
            conexion.execute(delete(historia).where(historia.c.id == historia_id))


# --- Lectura para el servidor MCP (solo lectura, nunca escribe) ---------------
def load_memory_entries(fuente: str | Path | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Devuelve (historias, items_de_checklist) aprobados, en el formato de las fuentes del agente."""
    if fuente is None:
        if not os.environ.get("DATABASE_URL", "").strip() and not ruta_sqlite_por_defecto().is_file():
            return [], []
    elif "://" not in str(fuente) and not Path(fuente).is_file():
        return [], []
    try:
        motor = crear_motor(fuente)
        with motor.connect() as conexion:
            historias_db = conexion.execute(
                select(hu_aprobada).order_by(hu_aprobada.c.aprobada_en.desc()).limit(200)).all()
            lecciones_db = conexion.execute(
                select(leccion).where(leccion.c.estado == "aprobada").order_by(leccion.c.id.desc()).limit(200)).all()
    except SQLAlchemyError:
        logger.warning("repositorio_no_disponible", extra={"event": "repositorio_no_disponible"})
        return [], []

    historias: list[dict[str, Any]] = []
    for fila in historias_db:
        row = fila._mapping
        hist = json.loads(row["historia"])
        aclaraciones = json.loads(row["aclaraciones"])[:5]
        resumen = (
            f"HU aprobada por el Product Owner. Como {hist.get('asA', '')}, quiero {hist.get('iWant', '')}, "
            f"para {hist.get('soThat', '')}"
        )[:1000]
        historias.append({
            "id": row["codigo"] or row["id"],  # el agente cita el código legible, no el GUID
            "titulo": row["titulo"][:200],
            "resumen": resumen,
            "aclaraciones": [f"{item['pregunta']} → {item['respuesta']}"[:400] for item in aclaraciones],
            "similitud": 0.6,
            "terminos": _tokens(f"{row['titulo']} {row['requerimiento']}")[:30],
        })
    checklist = [
        {
            "id": fila.id,
            "categoria": fila.categoria,
            "descripcion": fila.pregunta_sugerida[:500],
            "terminos": json.loads(fila.terminos),
            "evidencia": "Lección aprendida aprobada tras un cambio posterior al grooming de una HU del Repositorio; requiere validación humana.",
        }
        for fila in lecciones_db
    ]
    return historias, checklist
