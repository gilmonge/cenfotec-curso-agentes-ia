"""Memoria de largo plazo del Agente Analista: Repositorio de HU, lecciones aprendidas e historias de trabajo.

Se guarda en una base MySQL compatible (TiDB Cloud Starter en Render) o, en local y en pruebas, en SQLite.
Contiene lo que una persona aprobó (HU anonimizadas y lecciones aprobadas) y las historias de trabajo del
equipo, compartidas entre dispositivos. El agente solo lee; las escrituras llegan por la API.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Callable
from typing import Any

from sqlalchemy import (
    Column, ForeignKey, Index, Integer, MetaData, String, Table, Text, delete, insert, select, text, update,
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
    # Impacto, decisiones, dependencias, pendientes técnicos, devoluciones del PO y beneficios (JSON).
    Column("seguimiento", _Largo),
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
# Huella de lo que ya se cargó en el índice de conocimiento (Pinecone), por fuente. Permite que la carga
# automática solo recargue lo que cambió.
sincronizacion_conocimiento = Table(
    "sincronizacion_conocimiento", _metadata,
    Column("fuente", String(40), primary_key=True),
    Column("huella", String(64), nullable=False),
    Column("actualizada_en", String(40), nullable=False),
)

# Flujos de creación o cambio de una HU que todavía no terminan: se guardan cada vez que esperan a una persona
# (o fallan) para poder retomarlos otro día, aunque el servicio se haya reiniciado.
workflow_guardado = Table(
    "workflow_guardado", _metadata,
    Column("id", _GUID, primary_key=True),  # el workflow_id público
    Column("hilo", String(64), nullable=False),  # identificador interno del hilo de LangGraph; no se expone
    Column("modo", String(20), nullable=False),
    Column("titulo", String(200), nullable=False),
    Column("creado_por", String(120)),
    Column("creado_por_usuario", String(60)),  # id del usuario que inició el flujo (con seguridad activa)
    Column("estado", String(20), nullable=False),  # esperando | en_ejecucion | error | completado | cancelado | fallido
    Column("etapa", String(40), nullable=False),
    Column("espera", String(40)),  # tipo de interrupción pendiente, si hay
    Column("formulario", _Largo),
    Column("borrador", _Largo),  # respuestas escritas y todavía no enviadas
    Column("punto_control", _Largo),
    Column("creado_en", String(40), nullable=False),
    Column("actualizado_en", String(40), nullable=False),
    Index("ix_workflow_guardado_estado", "estado"),
)

# Avisos para una persona: su historia fue aprobada, devuelta o rechazada. Lo que espera decisión no se guarda
# aquí: sale de los flujos guardados (workflow_guardado.espera), así nunca queda desactualizado.
aviso = Table(
    "aviso", _metadata,
    Column("id", _GUID, primary_key=True),
    Column("usuario_id", String(60), nullable=False),  # destinatario (id del usuario de la sesión)
    Column("tipo", String(20), nullable=False),  # aprobada | devuelta | rechazada
    Column("workflow_id", _GUID),
    Column("titulo", String(200), nullable=False),
    Column("detalle", _Largo),
    Column("autor", String(120)),
    Column("creado_en", String(40), nullable=False),
    Column("leido_en", String(40)),
    Index("ix_aviso_usuario", "usuario_id"),
)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_LONG_DIGITS = re.compile(r"(?<![\d.,])\d{9,}(?![\d.,])")
_ID_PATTERN = re.compile(r"\b\d-\d{4}-\d{4}\b")
_UUID_TEXT = re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.IGNORECASE)


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
    numeric_content = _UUID_TEXT.sub(" ", joined)
    if _EMAIL.search(joined):
        findings.append("correo electrónico")
    if _LONG_DIGITS.search(numeric_content) or _ID_PATTERN.search(numeric_content):
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


# Columnas agregadas después de crear la tabla: create_all no altera tablas existentes.
_COLUMNA_NUEVA = {"hu_aprobada": ("seguimiento",), "workflow_guardado": ("creado_por_usuario",)}


def _agregar_columnas_nuevas(motor) -> None:
    inspector = inspect(motor)
    for nombre_tabla, lista_columna in _COLUMNA_NUEVA.items():
        if not inspector.has_table(nombre_tabla):
            continue
        existentes = {columna["name"] for columna in inspector.get_columns(nombre_tabla)}
        tabla = _metadata.tables[nombre_tabla]
        for nombre_columna in lista_columna:
            if nombre_columna in existentes:
                continue
            tipo = tabla.c[nombre_columna].type.compile(dialect=motor.dialect)
            with motor.begin() as conexion:
                conexion.execute(text(f"ALTER TABLE {nombre_tabla} ADD COLUMN {nombre_columna} {tipo}"))
            logger.info("columna_agregada", extra={"event": "columna_agregada", "tabla": nombre_tabla,
                                                    "columna": nombre_columna})


def _siguiente_codigo_leccion(conexion) -> str:
    """Código legible consecutivo de la lección (LEC-001, LEC-002, ...)."""
    mayor = 0
    for (codigo,) in conexion.execute(select(leccion.c.codigo)):
        coincidencia = re.fullmatch(r"LEC-(\d+)", codigo or "")
        if coincidencia:
            mayor = max(mayor, int(coincidencia.group(1)))
    return f"LEC-{mayor + 1:03d}"


class RepositorioHU:
    def __init__(self, fuente: str | Path | None = None, *, crear_esquema: bool = True) -> None:
        """``fuente``: URL, SQLite o None; ``crear_esquema=False`` habilita lectura sin DDL."""
        self.fuente = str(fuente) if fuente is not None else url_desde_entorno()
        self.motor = crear_motor(fuente)
        _verificar_esquema(self.motor)
        if crear_esquema:
            _metadata.create_all(self.motor)
            _agregar_columnas_nuevas(self.motor)

    # --- HU aprobadas -------------------------------------------------
        # Se avisa al cambiar HU o lecciones aprobadas (la carga automática de Pinecone se suscribe aquí).
        self.al_cambiar_conocimiento: Callable[[], None] | None = None

    def _avisar_cambio_conocimiento(self) -> None:
        aviso = self.al_cambiar_conocimiento
        if aviso is None:
            return
        try:
            aviso()
        except Exception as exc:
            logger.warning("aviso_conocimiento_fallido", extra={"event": "aviso_conocimiento_fallido", "error": type(exc).__name__})

    # --- Huellas de la carga del conocimiento ---------------------------
    def obtener_huella(self, fuente: str) -> str | None:
        with self.motor.connect() as conexion:
            fila = conexion.execute(
                select(sincronizacion_conocimiento.c.huella).where(sincronizacion_conocimiento.c.fuente == fuente)
            ).first()
        return fila[0] if fila else None

    def guardar_huella(self, fuente: str, huella: str) -> None:
        with self.motor.begin() as conexion:
            existe = conexion.execute(
                select(sincronizacion_conocimiento.c.fuente).where(sincronizacion_conocimiento.c.fuente == fuente)
            ).first()
            valores = {"huella": huella, "actualizada_en": _now()}
            if existe:
                conexion.execute(update(sincronizacion_conocimiento)
                                 .where(sincronizacion_conocimiento.c.fuente == fuente).values(**valores))
            else:
                conexion.execute(insert(sincronizacion_conocimiento).values(fuente=fuente, **valores))

    def huella_repositorio(self) -> str:
        """Resume las HU y lecciones aprobadas: cambia cuando se aprueba, edita o elimina alguna."""
        with self.motor.connect() as conexion:
            lista_hu = conexion.execute(
                select(hu_aprobada.c.id, hu_aprobada.c.aprobada_en).order_by(hu_aprobada.c.id)).all()
            lista_leccion = conexion.execute(
                select(leccion.c.id, leccion.c.estado, leccion.c.decidida_en)
                .where(leccion.c.estado == "aprobada").order_by(leccion.c.id)).all()
        texto = json.dumps([[list(fila) for fila in lista_hu], [list(fila) for fila in lista_leccion]], default=str)
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()

    def guardar_hu(self, hu: dict[str, Any]) -> dict[str, Any]:
        aprobada_en = _now()
        valores = {
            "codigo": (str(hu.get("codigo") or "").strip()[:60] or None),
            "titulo": hu["titulo"], "tipo_informacion": hu["tipo_informacion"], "requerimiento": hu["requerimiento"],
            "historia": json.dumps(hu["historia"], ensure_ascii=False),
            "criterios": json.dumps(hu["criterios"], ensure_ascii=False),
            "aclaraciones": json.dumps(hu["aclaraciones"], ensure_ascii=False),
            "seguimiento": json.dumps(hu.get("seguimiento") or {}, ensure_ascii=False),
            "aprobada_en": aprobada_en,
        }
        with self.motor.begin() as conexion:
            existe = conexion.execute(select(hu_aprobada.c.id).where(hu_aprobada.c.id == hu["id"])).first()
            if existe:
                conexion.execute(update(hu_aprobada).where(hu_aprobada.c.id == hu["id"]).values(**valores))
            else:
                conexion.execute(insert(hu_aprobada).values(id=hu["id"], **valores))
        self._avisar_cambio_conocimiento()
        return {"id": hu["id"], "titulo": hu["titulo"], "aprobada_en": aprobada_en}

    # --- Flujos en proceso ----------------------------------------------
    def guardar_workflow(self, registro: dict[str, Any]) -> None:
        """Crea o actualiza el flujo guardado. Conserva ``creado_en`` y el borrador si no se envían."""
        ahora = _now()
        valores = {
            "hilo": registro["hilo"], "modo": registro["modo"], "titulo": (registro.get("titulo") or "Sin título")[:200],
            "creado_por": (registro.get("creado_por") or None) and registro["creado_por"][:120],
            "creado_por_usuario": registro.get("creado_por_usuario"),
            "estado": registro["estado"], "etapa": registro["etapa"], "espera": registro.get("espera"),
            "formulario": json.dumps(registro.get("formulario") or {}, ensure_ascii=False),
            "punto_control": json.dumps(registro.get("punto_control"), ensure_ascii=False),
            "actualizado_en": ahora,
        }
        with self.motor.begin() as conexion:
            existe = conexion.execute(
                select(workflow_guardado.c.id).where(workflow_guardado.c.id == registro["id"])).first()
            if existe:
                conexion.execute(update(workflow_guardado).where(workflow_guardado.c.id == registro["id"]).values(**valores))
            else:
                conexion.execute(insert(workflow_guardado).values(
                    id=registro["id"], creado_en=ahora, borrador=json.dumps({}), **valores))

    def obtener_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        with self.motor.connect() as conexion:
            fila = conexion.execute(select(workflow_guardado).where(workflow_guardado.c.id == workflow_id)).first()
        if fila is None:
            return None
        registro = dict(fila._mapping)
        for campo in ("formulario", "borrador", "punto_control"):
            registro[campo] = json.loads(registro[campo]) if registro.get(campo) else None
        return registro

    def listar_workflow(self) -> list[dict[str, Any]]:
        """Resumen de los flujos guardados, del más reciente al más antiguo (sin el punto de control)."""
        consulta = select(
            workflow_guardado.c.id, workflow_guardado.c.modo, workflow_guardado.c.titulo,
            workflow_guardado.c.creado_por, workflow_guardado.c.creado_por_usuario, workflow_guardado.c.estado, workflow_guardado.c.etapa,
            workflow_guardado.c.espera, workflow_guardado.c.creado_en, workflow_guardado.c.actualizado_en,
        ).order_by(workflow_guardado.c.actualizado_en.desc())
        with self.motor.connect() as conexion:
            return [dict(fila._mapping) for fila in conexion.execute(consulta)]

    # --- Avisos ---------------------------------------------------------
    def registrar_aviso(self, *, usuario_id: str, tipo: str, titulo: str, workflow_id: str | None = None,
                        detalle: str | None = None, autor: str | None = None) -> None:
        with self.motor.begin() as conexion:
            conexion.execute(insert(aviso).values(
                id=nuevo_guid(), usuario_id=usuario_id[:60], tipo=tipo[:20], workflow_id=workflow_id,
                titulo=(titulo or "Sin título")[:200], detalle=(detalle or None), autor=(autor or None) and autor[:120],
                creado_en=_now()))

    def listar_aviso(self, usuario_id: str, limite: int = 30) -> list[dict[str, Any]]:
        """Avisos sin leer de la persona, del más reciente al más antiguo."""
        consulta = (select(aviso).where(aviso.c.usuario_id == usuario_id, aviso.c.leido_en.is_(None))
                    .order_by(aviso.c.creado_en.desc()).limit(limite))
        with self.motor.connect() as conexion:
            return [dict(fila._mapping) for fila in conexion.execute(consulta)]

    def marcar_aviso_leido(self, aviso_id: str, usuario_id: str) -> None:
        with self.motor.begin() as conexion:
            conexion.execute(update(aviso).where(aviso.c.id == aviso_id, aviso.c.usuario_id == usuario_id)
                             .values(leido_en=_now()))

    def guardar_borrador_workflow(self, workflow_id: str, borrador: dict[str, str]) -> None:
        with self.motor.begin() as conexion:
            resultado = conexion.execute(update(workflow_guardado).where(workflow_guardado.c.id == workflow_id).values(
                borrador=json.dumps(borrador, ensure_ascii=False), actualizado_en=_now()))
        if resultado.rowcount == 0:
            raise RepositorioError("El flujo no está guardado.", not_found=True)

    def eliminar_workflow(self, workflow_id: str) -> None:
        with self.motor.begin() as conexion:
            conexion.execute(delete(workflow_guardado).where(workflow_guardado.c.id == workflow_id))

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
        self._avisar_cambio_conocimiento()

    # --- Solicitudes de cambio y lecciones -----------------------------
    def registrar_cambio(
        self, *, hu_id: str, solicitud: str, clasificacion: str, causa_raiz: str,
        pregunta_sugerida: str | None = None, terminos: list[str] | None = None,
        lecciones_propuestas: list[dict[str, Any]] | None = None, cambio_id: str | None = None,
        incluir_ids_lecciones: bool = False,
    ) -> dict[str, Any]:
        """Registra la solicitud; solo genera lección si trae la pregunta que debió hacerse.

        Cuando Negocio simplemente cambia de decisión no hubo un vacío del análisis y no hay lección que aprender.
        Las clasificaciones "aclaracion" y "correccion" se conservan solo para leer solicitudes registradas antes.
        """
        if clasificacion not in CLASIFICACIONES:
            raise RepositorioError("Clasificación no permitida.")
        pregunta_sugerida = (pregunta_sugerida or "").strip()
        propuestas = list(lecciones_propuestas or [])
        if pregunta_sugerida:
            propuestas.insert(0, {
                "categoria": causa_raiz, "pregunta_sugerida": pregunta_sugerida, "terminos": terminos or [],
            })
        if clasificacion == "correccion":
            propuestas = []
        for propuesta in propuestas:
            if (
                not isinstance(propuesta, dict)
                or propuesta.get("categoria") not in CATEGORIAS
                or not isinstance(propuesta.get("pregunta_sugerida"), str)
                or not propuesta["pregunta_sugerida"].strip()
                or not isinstance(propuesta.get("terminos", []), list)
            ):
                raise RepositorioError("La lección propuesta no satisface el contrato del Repositorio.")
        if propuestas and causa_raiz and causa_raiz not in CATEGORIAS:
            raise RepositorioError("La causa raíz debe ser una categoría del checklist de vacíos.")
        causa_raiz = causa_raiz if propuestas else ""
        self.obtener_hu(hu_id)
        creada_en = _now()
        with self.motor.begin() as conexion:
            solicitud_id = cambio_id or nuevo_guid()
            if not es_guid(solicitud_id):
                raise RepositorioError("La clave idempotente del cambio debe ser un GUID.")
            existente = conexion.execute(
                select(solicitud_cambio).where(solicitud_cambio.c.id == solicitud_id)
            ).first()
            if existente is not None:
                row = existente._mapping
                if (row["hu_id"], row["solicitud"], row["clasificacion"]) != (hu_id, solicitud, clasificacion):
                    raise RepositorioError("La clave de cambio ya se usó para otra solicitud.")
                lesson_rows = conexion.execute(
                    select(leccion).where(leccion.c.solicitud_id == solicitud_id).order_by(leccion.c.id)
                ).all()
                expected = sorted([
                    (item["categoria"], item["pregunta_sugerida"], json.dumps(item.get("terminos", []), ensure_ascii=False))
                    for item in propuestas
                ])
                actual = sorted((item.categoria, item.pregunta_sugerida, item.terminos) for item in lesson_rows)
                if expected != actual:
                    raise RepositorioError("La clave de cambio ya se usó con otras lecciones.")
                lesson_ids = [
                    str(uuid.uuid5(uuid.UUID(solicitud_id), f"lesson:{index}"))
                    for index in range(len(propuestas))
                ]
                result = {
                    "solicitud_id": solicitud_id, "leccion_id": lesson_ids[0] if lesson_ids else None,
                    "estado": "propuesta" if lesson_ids else None,
                }
                if incluir_ids_lecciones:
                    result["leccion_ids"] = lesson_ids
                return result
            conexion.execute(insert(solicitud_cambio).values(
                id=solicitud_id, hu_id=hu_id, solicitud=solicitud, clasificacion=clasificacion,
                causa_raiz=causa_raiz, creada_en=creada_en,
            ))
            lesson_ids = []
            for index, propuesta in enumerate(propuestas):
                lesson_id = str(uuid.uuid5(uuid.UUID(solicitud_id), f"lesson:{index}"))
                lesson_ids.append(lesson_id)
                conexion.execute(insert(leccion).values(
                    id=lesson_id, codigo=_siguiente_codigo_leccion(conexion), solicitud_id=solicitud_id, hu_id=hu_id,
                    categoria=propuesta["categoria"], pregunta_sugerida=propuesta["pregunta_sugerida"].strip(),
                    terminos=json.dumps(propuesta.get("terminos", []), ensure_ascii=False),
                    estado="propuesta", creada_en=creada_en,
                ))
        result = {
            "solicitud_id": solicitud_id, "leccion_id": lesson_ids[0] if lesson_ids else None,
            "estado": "propuesta" if lesson_ids else None,
        }
        if incluir_ids_lecciones:
            result["leccion_ids"] = lesson_ids
        return result

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
        if estado == "aprobada":
            self._avisar_cambio_conocimiento()
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
        if detect_personal_data(json.dumps(dict(row), ensure_ascii=False, default=str)):
            continue
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
    checklist = []
    for fila in lecciones_db:
        row = fila._mapping
        if detect_personal_data(json.dumps(dict(row), ensure_ascii=False, default=str)):
            continue
        checklist.append({
            "id": fila.id,
            "categoria": fila.categoria,
            "descripcion": fila.pregunta_sugerida[:500],
            "terminos": json.loads(fila.terminos),
            "evidencia": "Lección aprendida aprobada tras un cambio posterior al grooming de una HU del Repositorio; requiere validación humana.",
        })
    return historias, checklist
