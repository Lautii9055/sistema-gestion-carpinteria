"""Contratos que la capa de negocio necesita de la capa de datos.

La lógica depende de estas interfaces y no de SQL Server (principio de
inversión de dependencias, la "D" de SOLID). Por eso las pruebas pueden usar
repositorios en memoria y la lógica se prueba sin una base de datos.
"""
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from carpinteria.negocio.entidades import Usuario


class RepositorioUsuarios(Protocol):
    def buscar_por_nombre(self, nombre_usuario: str) -> Usuario | None: ...
    def buscar_por_id(self, id_usuario: int) -> Usuario | None: ...
    def registrar_fallo(self, id_usuario: int, intentos: int, bloqueado_hasta: datetime | None) -> None: ...
    def registrar_ingreso_exitoso(self, id_usuario: int, fecha: datetime) -> None: ...
    def cambiar_contrasena(self, id_usuario: int, hash_contrasena: str, fecha: datetime) -> None: ...


class RepositorioAuditoria(Protocol):
    def registrar(self, codigo_evento: str, *, id_usuario: int | None = None,
                  usuario_ingresado: str | None = None, entidad: str | None = None,
                  id_entidad: int | None = None, detalle: str | None = None,
                  equipo: str | None = None) -> None: ...
    def contar_ingresos_fallidos(self, id_usuario: int, desde: datetime | None) -> int: ...


class RepositorioParametros(Protocol):
    def obtener(self, clave: str) -> Decimal | None: ...
