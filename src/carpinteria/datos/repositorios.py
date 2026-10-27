"""Repositorios sobre SQL Server.

Implementan los contratos de negocio/puertos.py. Todas las consultas son
parametrizadas: los valores viajan separados del SQL (marcadores ?), así que un
dato ingresado por el usuario nunca puede convertirse en código (RNF-05.3).
"""
from datetime import datetime
from decimal import Decimal

from carpinteria.datos.conexion import conexion_abierta
from carpinteria.negocio.entidades import EventoAuditoria, TipoEvento, Usuario

_COLUMNAS_USUARIO = """
    id_usuario, nombre_usuario_usu, nombre_completo_usu, hash_contrasena_usu,
    debe_cambiar_contrasena_usu, es_activo_usu, intentos_fallidos_usu,
    bloqueado_hasta_usu, ultimo_ingreso_usu
"""


def _a_usuario(fila) -> Usuario:
    return Usuario(
        id=fila.id_usuario,
        nombre_usuario=fila.nombre_usuario_usu,
        nombre_completo=fila.nombre_completo_usu,
        hash_contrasena=fila.hash_contrasena_usu,
        debe_cambiar_contrasena=bool(fila.debe_cambiar_contrasena_usu),
        es_activo=bool(fila.es_activo_usu),
        intentos_fallidos=fila.intentos_fallidos_usu,
        bloqueado_hasta=fila.bloqueado_hasta_usu,
        ultimo_ingreso=fila.ultimo_ingreso_usu,
    )


class RepositorioUsuariosSql:
    def buscar_por_nombre(self, nombre_usuario: str) -> Usuario | None:
        with conexion_abierta() as cn:
            fila = cn.cursor().execute(
                f"SELECT {_COLUMNAS_USUARIO} FROM dbo.Usuario WHERE nombre_usuario_usu = ?",
                nombre_usuario,
            ).fetchone()
        return _a_usuario(fila) if fila else None

    def buscar_por_id(self, id_usuario: int) -> Usuario | None:
        with conexion_abierta() as cn:
            fila = cn.cursor().execute(
                f"SELECT {_COLUMNAS_USUARIO} FROM dbo.Usuario WHERE id_usuario = ?",
                id_usuario,
            ).fetchone()
        return _a_usuario(fila) if fila else None

    def registrar_fallo(self, id_usuario: int, intentos: int, bloqueado_hasta: datetime | None) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Usuario SET intentos_fallidos_usu = ?, bloqueado_hasta_usu = ? "
                "WHERE id_usuario = ?",
                intentos, bloqueado_hasta, id_usuario,
            )

    def registrar_ingreso_exitoso(self, id_usuario: int, fecha: datetime) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Usuario SET intentos_fallidos_usu = 0, bloqueado_hasta_usu = NULL, "
                "ultimo_ingreso_usu = ? WHERE id_usuario = ?",
                fecha, id_usuario,
            )

    def cambiar_contrasena(self, id_usuario: int, hash_contrasena: str, fecha: datetime) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Usuario SET hash_contrasena_usu = ?, debe_cambiar_contrasena_usu = 0, "
                "fecha_cambio_contrasena_usu = ? WHERE id_usuario = ?",
                hash_contrasena, fecha, id_usuario,
            )


    def listar(self) -> list[Usuario]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(f"SELECT {_COLUMNAS_USUARIO} FROM dbo.Usuario").fetchall()
        return [_a_usuario(f) for f in filas]

    def crear(self, nombre_usuario: str, nombre_completo: str, hash_contrasena: str) -> int:
        with conexion_abierta() as cn:
            return cn.cursor().execute(
                "INSERT INTO dbo.Usuario (nombre_usuario_usu, hash_contrasena_usu, "
                "debe_cambiar_contrasena_usu, nombre_completo_usu) "
                "OUTPUT INSERTED.id_usuario VALUES (?, ?, 1, ?)",
                nombre_usuario, hash_contrasena, nombre_completo,
            ).fetchone()[0]

    def asignar_contrasena_provisoria(self, id_usuario: int, hash_contrasena: str) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Usuario SET hash_contrasena_usu = ?, debe_cambiar_contrasena_usu = 1, "
                "intentos_fallidos_usu = 0, bloqueado_hasta_usu = NULL WHERE id_usuario = ?",
                hash_contrasena, id_usuario,
            )

    def cambiar_estado(self, id_usuario: int, activo: bool) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Usuario SET es_activo_usu = ? WHERE id_usuario = ?",
                1 if activo else 0, id_usuario,
            )


class RepositorioAuditoriaSql:
    def registrar(self, codigo_evento: str, *, id_usuario: int | None = None,
                  usuario_ingresado: str | None = None, entidad: str | None = None,
                  id_entidad: int | None = None, detalle: str | None = None,
                  equipo: str | None = None) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "{CALL dbo.sp_registrar_evento (?, ?, ?, ?, ?, ?, ?)}",
                codigo_evento, id_usuario, usuario_ingresado, entidad, id_entidad,
                detalle, equipo,
            )

    def contar_ingresos_fallidos(self, id_usuario: int, desde: datetime | None) -> int:
        with conexion_abierta() as cn:
            return cn.cursor().execute(
                """SELECT COUNT(*)
                   FROM dbo.Auditoria a
                   JOIN dbo.Tipo_Evento t ON t.id_tipo_evento = a.id_tipo_evento
                   WHERE t.codigo_tev = 'LOGIN_FALLIDO'
                     AND a.id_usuario = ?
                     AND (? IS NULL OR a.fecha_hora_aud > ?)""",
                id_usuario, desde, desde,
            ).fetchone()[0]


    def listar(self, *, desde: datetime | None = None, id_usuario: int | None = None,
               codigo_evento: str | None = None, solo_criticos: bool = False,
               limite: int = 500) -> list[EventoAuditoria]:
        # Los filtros opcionales se resuelven con "? IS NULL OR ..." para que la
        # consulta sea siempre la misma y todos los valores vayan como parámetros.
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                """SELECT TOP (?) a.fecha_hora_aud, t.codigo_tev, t.descripcion_tev, t.es_critico_tev,
                          u.nombre_completo_usu, a.usuario_ingresado_aud, a.detalle_aud, a.equipo_aud
                   FROM dbo.Auditoria a
                   JOIN dbo.Tipo_Evento t ON t.id_tipo_evento = a.id_tipo_evento
                   LEFT JOIN dbo.Usuario u ON u.id_usuario = a.id_usuario
                   WHERE (? IS NULL OR a.fecha_hora_aud >= ?)
                     AND (? IS NULL OR a.id_usuario = ?)
                     AND (? IS NULL OR t.codigo_tev = ?)
                     AND (? = 0 OR t.es_critico_tev = 1)
                   ORDER BY a.fecha_hora_aud DESC, a.id_auditoria DESC""",
                limite, desde, desde, id_usuario, id_usuario, codigo_evento, codigo_evento,
                1 if solo_criticos else 0,
            ).fetchall()
        return [EventoAuditoria(f[0], f[1], f[2], bool(f[3]), f[4], f[5], f[6], f[7]) for f in filas]

    def tipos_de_evento(self) -> list[TipoEvento]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                "SELECT codigo_tev, descripcion_tev, es_critico_tev FROM dbo.Tipo_Evento "
                "ORDER BY descripcion_tev"
            ).fetchall()
        return [TipoEvento(f[0], f[1], bool(f[2])) for f in filas]


class RepositorioParametrosSql:
    def obtener(self, clave: str) -> Decimal | None:
        with conexion_abierta() as cn:
            fila = cn.cursor().execute(
                "SELECT valor_par FROM dbo.Parametro WHERE clave_par = ?", clave
            ).fetchone()
        return fila[0] if fila else None
