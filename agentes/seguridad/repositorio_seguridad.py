"""Usuarios, roles y la asignación de roles a usuarios y de acciones a roles (misma base del Repositorio de HU).

Las acciones no tienen tabla propia: viven en el catálogo del código (``catalogo.py``) y aquí solo se
guarda qué rol tiene cada código. Un código que se retire del catálogo deja de contar sin migraciones.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, Column, ForeignKey, Index, MetaData, String, Table, delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from agentes.seguridad.catalogo import ACCION, CODIGO_ACCION, LISTA_ROL_INICIAL, ROL_ADMINISTRADOR
from agentes.seguridad.clave import cifrar_clave, verificar_clave

logger = logging.getLogger(__name__)

_GUID = String(36)
_metadata = MetaData()
usuario = Table(
    "usuario", _metadata,
    Column("id", _GUID, primary_key=True),
    Column("usuario", String(60), nullable=False, unique=True),
    Column("nombre", String(120), nullable=False),
    Column("clave", String(200), nullable=False),
    Column("activo", Boolean, nullable=False, default=True),
    Column("creado_en", String(40), nullable=False),
)
rol = Table(
    "rol", _metadata,
    Column("id", _GUID, primary_key=True),
    Column("nombre", String(80), nullable=False, unique=True),
    Column("descripcion", String(300), nullable=False, default=""),
    Column("creado_en", String(40), nullable=False),
)
usuario_rol = Table(
    "usuario_rol", _metadata,
    Column("usuario_id", _GUID, ForeignKey("usuario.id", name="fk_usuario_rol_usuario"), primary_key=True),
    Column("rol_id", _GUID, ForeignKey("rol.id", name="fk_usuario_rol_rol"), primary_key=True),
)
rol_accion = Table(
    "rol_accion", _metadata,
    Column("rol_id", _GUID, ForeignKey("rol.id", name="fk_rol_accion_rol"), primary_key=True),
    Column("accion", String(80), primary_key=True),
    Index("ix_rol_accion_accion", "accion"),
)

_PATRON_USUARIO = re.compile(r"^[a-zA-Z0-9._-]{3,60}$")
_LARGO_MINIMO_CLAVE = 8


class SeguridadError(Exception):
    def __init__(self, mensaje: str, *, no_encontrado: bool = False) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.no_encontrado = no_encontrado


def _ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _validar_clave(clave: str) -> None:
    if len(clave or "") < _LARGO_MINIMO_CLAVE:
        raise SeguridadError(f"La contraseña debe tener al menos {_LARGO_MINIMO_CLAVE} caracteres.")


class RepositorioSeguridad:
    def __init__(self, motor) -> None:
        self.motor = motor
        _metadata.create_all(motor)

    # --- Arranque -----------------------------------------------------
    def inicializar(self, administrador_usuario: str, administrador_clave: str) -> None:
        """Base nueva: crea los roles iniciales y el administrador. Siempre agrega al Administrador las
        acciones nuevas del catálogo, para que nunca quede sin poder asignarlas."""
        with self.motor.begin() as conexion:
            if conexion.execute(select(rol.c.id).limit(1)).first() is None:
                for nombre, descripcion, lista_codigo in LISTA_ROL_INICIAL:
                    rol_id = str(uuid.uuid4())
                    conexion.execute(insert(rol).values(id=rol_id, nombre=nombre, descripcion=descripcion, creado_en=_ahora()))
                    for codigo in lista_codigo:
                        conexion.execute(insert(rol_accion).values(rol_id=rol_id, accion=codigo))
                logger.info("roles_iniciales_creados", extra={"event": "roles_iniciales_creados"})
            administrador_id = conexion.execute(select(rol.c.id).where(rol.c.nombre == ROL_ADMINISTRADOR)).scalar()
            if administrador_id:
                actuales = set(conexion.execute(select(rol_accion.c.accion).where(rol_accion.c.rol_id == administrador_id)).scalars())
                for codigo in sorted(CODIGO_ACCION - actuales):
                    conexion.execute(insert(rol_accion).values(rol_id=administrador_id, accion=codigo))
            if conexion.execute(select(usuario.c.id).limit(1)).first() is None and administrador_id:
                usuario_id = str(uuid.uuid4())
                conexion.execute(insert(usuario).values(
                    id=usuario_id, usuario=administrador_usuario, nombre="Administrador",
                    clave=cifrar_clave(administrador_clave), activo=True, creado_en=_ahora()))
                conexion.execute(insert(usuario_rol).values(usuario_id=usuario_id, rol_id=administrador_id))
                logger.info("administrador_inicial_creado", extra={"event": "administrador_inicial_creado"})

    # --- Sesión -------------------------------------------------------
    def autenticar(self, nombre_usuario: str, clave: str) -> dict[str, Any] | None:
        with self.motor.connect() as conexion:
            fila = conexion.execute(select(usuario).where(usuario.c.usuario == (nombre_usuario or "").strip())).first()
        if fila is None or not fila.activo or not verificar_clave(clave or "", fila.clave):
            return None
        return self.obtener_usuario(fila.id)

    def obtener_usuario(self, usuario_id: str) -> dict[str, Any] | None:
        with self.motor.connect() as conexion:
            fila = conexion.execute(select(usuario).where(usuario.c.id == usuario_id)).first()
            if fila is None:
                return None
            lista_rol = conexion.execute(
                select(rol.c.id, rol.c.nombre).join(usuario_rol, usuario_rol.c.rol_id == rol.c.id)
                .where(usuario_rol.c.usuario_id == usuario_id).order_by(rol.c.nombre)).all()
            lista_accion = conexion.execute(
                select(rol_accion.c.accion).distinct().join(usuario_rol, usuario_rol.c.rol_id == rol_accion.c.rol_id)
                .where(usuario_rol.c.usuario_id == usuario_id)).scalars().all()
        return {
            "id": fila.id, "usuario": fila.usuario, "nombre": fila.nombre, "activo": bool(fila.activo),
            "roles": [{"id": r.id, "nombre": r.nombre} for r in lista_rol],
            "acciones": sorted(set(lista_accion) & CODIGO_ACCION),
        }

    # --- Usuarios -----------------------------------------------------
    def listar_usuario(self, busqueda: str = "") -> list[dict[str, Any]]:
        consulta = select(usuario.c.id).order_by(usuario.c.nombre)
        texto = (busqueda or "").strip()
        if texto:
            patron = f"%{texto}%"
            consulta = consulta.where(usuario.c.nombre.ilike(patron) | usuario.c.usuario.ilike(patron))
        with self.motor.connect() as conexion:
            lista_id = conexion.execute(consulta).scalars().all()
        return [self.obtener_usuario(usuario_id) for usuario_id in lista_id]

    def crear_usuario(self, nombre_usuario: str, nombre: str, clave: str, lista_rol_id: list[str]) -> dict[str, Any]:
        nombre_usuario = (nombre_usuario or "").strip()
        if not _PATRON_USUARIO.match(nombre_usuario):
            raise SeguridadError("El usuario debe tener de 3 a 60 caracteres: letras, números, punto, guion o guion bajo.")
        if not (nombre or "").strip():
            raise SeguridadError("Escriba el nombre de la persona.")
        _validar_clave(clave)
        usuario_id = str(uuid.uuid4())
        try:
            with self.motor.begin() as conexion:
                conexion.execute(insert(usuario).values(
                    id=usuario_id, usuario=nombre_usuario, nombre=nombre.strip()[:120], clave=cifrar_clave(clave),
                    activo=True, creado_en=_ahora()))
                self._reemplazar_rol(conexion, usuario_id, lista_rol_id)
        except IntegrityError as exc:
            raise SeguridadError("Ya existe un usuario con ese nombre de usuario.") from exc
        return self.obtener_usuario(usuario_id)

    def actualizar_usuario(
        self, usuario_id: str, *, nombre: str | None = None, activo: bool | None = None,
        clave: str | None = None, lista_rol_id: list[str] | None = None,
    ) -> dict[str, Any]:
        if self.obtener_usuario(usuario_id) is None:
            raise SeguridadError("El usuario no existe.", no_encontrado=True)
        valores: dict[str, Any] = {}
        if nombre is not None:
            if not nombre.strip():
                raise SeguridadError("Escriba el nombre de la persona.")
            valores["nombre"] = nombre.strip()[:120]
        if activo is not None:
            valores["activo"] = activo
        if clave:
            _validar_clave(clave)
            valores["clave"] = cifrar_clave(clave)
        with self.motor.begin() as conexion:
            if valores:
                conexion.execute(update(usuario).where(usuario.c.id == usuario_id).values(**valores))
            if lista_rol_id is not None:
                self._reemplazar_rol(conexion, usuario_id, lista_rol_id)
            self._exigir_administrador(conexion)
        return self.obtener_usuario(usuario_id)

    def _reemplazar_rol(self, conexion, usuario_id: str, lista_rol_id: list[str]) -> None:
        validos = set(conexion.execute(select(rol.c.id).where(rol.c.id.in_(list(lista_rol_id or [])))).scalars())
        if len(validos) != len(set(lista_rol_id or [])):
            raise SeguridadError("Alguno de los roles no existe.")
        conexion.execute(delete(usuario_rol).where(usuario_rol.c.usuario_id == usuario_id))
        for rol_id in sorted(validos):
            conexion.execute(insert(usuario_rol).values(usuario_id=usuario_id, rol_id=rol_id))

    def _exigir_administrador(self, conexion) -> None:
        """Siempre debe quedar al menos una persona activa que pueda asignar roles y acciones."""
        consulta = (
            select(usuario.c.id).join(usuario_rol, usuario_rol.c.usuario_id == usuario.c.id)
            .join(rol_accion, rol_accion.c.rol_id == usuario_rol.c.rol_id)
            .where(usuario.c.activo.is_(True), rol_accion.c.accion == ACCION.ROL_ADMINISTRAR).limit(1)
        )
        if conexion.execute(consulta).first() is None:
            raise SeguridadError("El cambio dejaría el sistema sin nadie que pueda administrar roles. No se aplicó.")

    # --- Roles --------------------------------------------------------
    def listar_rol(self) -> list[dict[str, Any]]:
        with self.motor.connect() as conexion:
            lista_fila = conexion.execute(select(rol).order_by(rol.c.nombre)).all()
            lista_asignacion = conexion.execute(select(rol_accion)).all()
            lista_conteo = conexion.execute(select(usuario_rol.c.rol_id)).scalars().all()
        acciones_por_rol: dict[str, list[str]] = {}
        for fila in lista_asignacion:
            if fila.accion in CODIGO_ACCION:
                acciones_por_rol.setdefault(fila.rol_id, []).append(fila.accion)
        return [{
            "id": fila.id, "nombre": fila.nombre, "descripcion": fila.descripcion or "",
            "acciones": sorted(acciones_por_rol.get(fila.id, [])),
            "usuarios": lista_conteo.count(fila.id),
        } for fila in lista_fila]

    def _obtener_rol(self, rol_id: str) -> dict[str, Any]:
        encontrado = next((item for item in self.listar_rol() if item["id"] == rol_id), None)
        if encontrado is None:
            raise SeguridadError("El rol no existe.", no_encontrado=True)
        return encontrado

    def crear_rol(self, nombre: str, descripcion: str, lista_accion: list[str]) -> dict[str, Any]:
        if not (nombre or "").strip():
            raise SeguridadError("Escriba el nombre del rol.")
        rol_id = str(uuid.uuid4())
        try:
            with self.motor.begin() as conexion:
                conexion.execute(insert(rol).values(
                    id=rol_id, nombre=nombre.strip()[:80], descripcion=(descripcion or "").strip()[:300], creado_en=_ahora()))
                self._reemplazar_accion(conexion, rol_id, lista_accion)
        except IntegrityError as exc:
            raise SeguridadError("Ya existe un rol con ese nombre.") from exc
        return self._obtener_rol(rol_id)

    def actualizar_rol(
        self, rol_id: str, *, nombre: str | None = None, descripcion: str | None = None,
        lista_accion: list[str] | None = None,
    ) -> dict[str, Any]:
        self._obtener_rol(rol_id)
        valores: dict[str, Any] = {}
        if nombre is not None:
            if not nombre.strip():
                raise SeguridadError("Escriba el nombre del rol.")
            valores["nombre"] = nombre.strip()[:80]
        if descripcion is not None:
            valores["descripcion"] = descripcion.strip()[:300]
        try:
            with self.motor.begin() as conexion:
                if valores:
                    conexion.execute(update(rol).where(rol.c.id == rol_id).values(**valores))
                if lista_accion is not None:
                    self._reemplazar_accion(conexion, rol_id, lista_accion)
                self._exigir_administrador(conexion)
        except IntegrityError as exc:
            raise SeguridadError("Ya existe un rol con ese nombre.") from exc
        return self._obtener_rol(rol_id)

    def eliminar_rol(self, rol_id: str) -> None:
        self._obtener_rol(rol_id)
        with self.motor.begin() as conexion:
            conexion.execute(delete(usuario_rol).where(usuario_rol.c.rol_id == rol_id))
            conexion.execute(delete(rol_accion).where(rol_accion.c.rol_id == rol_id))
            conexion.execute(delete(rol).where(rol.c.id == rol_id))
            self._exigir_administrador(conexion)

    def _reemplazar_accion(self, conexion, rol_id: str, lista_accion: list[str]) -> None:
        desconocida = set(lista_accion or []) - CODIGO_ACCION
        if desconocida:
            raise SeguridadError("Alguna de las acciones no existe en el catálogo.")
        conexion.execute(delete(rol_accion).where(rol_accion.c.rol_id == rol_id))
        for codigo in sorted(set(lista_accion or [])):
            conexion.execute(insert(rol_accion).values(rol_id=rol_id, accion=codigo))
