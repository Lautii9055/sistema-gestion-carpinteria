"""Repositorio de trabajos sobre SQL Server.

Igual que en clientes: todo viaja como parámetro, los comodines de LIKE se
neutralizan y los filtros opcionales usan "? IS NULL OR ..." para que la
consulta tenga siempre la misma forma.
"""
from datetime import date

from carpinteria.datos.conexion import conexion_abierta
from carpinteria.datos.repositorios_clientes import escapar_like
from carpinteria.negocio.entidades import Cliente, DetalleTrabajo, EstadoTrabajo, Obra, Trabajo
from carpinteria.negocio.trabajos import ESTADOS_SIN_COBRO

_SELECT = """
SELECT {top} t.id_trabajo, t.id_obra, t.id_estado_trabajo, t.descripcion_tra, t.monto_total_tra,
       t.monto_sena_tra, t.fecha_alta_tra, t.fecha_cobro_sena_tra, t.fecha_comienzo_tra,
       t.fecha_finalizacion_tra, t.fecha_entrega_tra, t.fecha_cobro_saldo_tra, t.observaciones_tra,
       t.fecha_presupuesto_tra, t.entrega_aproximada_tra,
       e.nombre_etr, e.orden_etr,
       o.id_cliente, o.nombre_obr, o.direccion_obr, o.localidad_obr, o.observaciones_obr,
       c.nombre_cli, c.apellido_cli, c.telefono_cli, c.email_cli, c.observaciones_cli, c.es_activo_cli
FROM dbo.Trabajo t
JOIN dbo.Estado_Trabajo e ON e.id_estado_trabajo = t.id_estado_trabajo
JOIN dbo.Obra o           ON o.id_obra = t.id_obra
JOIN dbo.Cliente c        ON c.id_cliente = o.id_cliente
"""

_CONDICION_POR_TERMINO = """(
       t.descripcion_tra LIKE ? ESCAPE '\\'
    OR c.nombre_cli      LIKE ? ESCAPE '\\'
    OR c.apellido_cli    LIKE ? ESCAPE '\\'
    OR o.direccion_obr   LIKE ? ESCAPE '\\'
    OR o.localidad_obr   LIKE ? ESCAPE '\\'
    OR o.nombre_obr      LIKE ? ESCAPE '\\'
    OR e.nombre_etr      LIKE ? ESCAPE '\\'
    OR t.id_trabajo = TRY_CAST(? AS INT)
)"""

# Algo por cobrar: trabajo confirmado (o más) con seña o saldo sin fecha de cobro.
_POR_COBRAR = """(
    e.nombre_etr NOT IN (?, ?) AND t.monto_total_tra IS NOT NULL AND (
        (t.fecha_cobro_sena_tra IS NULL AND ISNULL(t.monto_sena_tra, 0) > 0)
     OR (t.fecha_cobro_saldo_tra IS NULL AND t.monto_total_tra - ISNULL(t.monto_sena_tra, 0) > 0))
)"""


def _a_detalle(f) -> DetalleTrabajo:
    trabajo = Trabajo(f.id_trabajo, f.id_obra, f.id_estado_trabajo, f.descripcion_tra,
                      f.monto_total_tra, f.monto_sena_tra, f.fecha_alta_tra, f.fecha_cobro_sena_tra,
                      f.fecha_comienzo_tra, f.fecha_finalizacion_tra, f.fecha_entrega_tra,
                      f.fecha_cobro_saldo_tra, f.observaciones_tra, f.fecha_presupuesto_tra,
                      bool(f.entrega_aproximada_tra))
    estado = EstadoTrabajo(f.id_estado_trabajo, f.nombre_etr, f.orden_etr)
    obra = Obra(f.id_obra, f.id_cliente, f.direccion_obr, f.localidad_obr, f.nombre_obr,
                f.observaciones_obr)
    cliente = Cliente(f.id_cliente, f.nombre_cli, f.apellido_cli, f.telefono_cli, f.email_cli,
                      f.observaciones_cli, bool(f.es_activo_cli))
    return DetalleTrabajo(trabajo, estado, obra, cliente)


class RepositorioTrabajosSql:
    def estados(self) -> list[EstadoTrabajo]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                "SELECT id_estado_trabajo, nombre_etr, orden_etr FROM dbo.Estado_Trabajo ORDER BY orden_etr"
            ).fetchall()
        return [EstadoTrabajo(f[0], f[1], f[2]) for f in filas]

    def buscar(self, terminos: list[str], id_estado: int | None, solo_por_cobrar: bool,
               desde: date | None, limite: int,
               incluir_clientes_inactivos: bool = False) -> list[DetalleTrabajo]:
        condiciones = "".join(f"\n  AND {_CONDICION_POR_TERMINO}" for _ in terminos)
        sql = (_SELECT.format(top="TOP (?)")
               + "WHERE (? = 1 OR c.es_activo_cli = 1)\n"
               + "  AND (? IS NULL OR t.id_estado_trabajo = ?)\n"
               + "  AND (? IS NULL OR t.fecha_presupuesto_tra >= ?)\n"
               + f"  AND (? = 0 OR {_POR_COBRAR})"
               + condiciones
               + "\nORDER BY t.fecha_presupuesto_tra DESC, t.id_trabajo DESC")
        parametros = [limite, 1 if incluir_clientes_inactivos else 0, id_estado, id_estado, desde, desde,
                      1 if solo_por_cobrar else 0, *ESTADOS_SIN_COBRO]
        for termino in terminos:
            patron = escapar_like(termino)
            parametros += [patron] * 7 + [termino]
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(sql, *parametros).fetchall()
        return [_a_detalle(f) for f in filas]

    def activos(self, excluir_estados: tuple[str, ...], limite: int) -> list[DetalleTrabajo]:
        """Trabajos que no terminaron su ciclo (para el inicio)."""
        marcas = ", ".join("?" for _ in excluir_estados)
        sql = (_SELECT.format(top="TOP (?)") + f"WHERE e.nombre_etr NOT IN ({marcas})\n"
               + "ORDER BY t.fecha_presupuesto_tra, t.id_trabajo")
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(sql, limite, *excluir_estados).fetchall()
        return [_a_detalle(f) for f in filas]

    def obtener(self, id_trabajo: int) -> DetalleTrabajo | None:
        with conexion_abierta() as cn:
            fila = cn.cursor().execute(_SELECT.format(top="") + "WHERE t.id_trabajo = ?",
                                       id_trabajo).fetchone()
        return _a_detalle(fila) if fila else None

    def crear(self, trabajo: Trabajo) -> int:
        with conexion_abierta() as cn:
            return cn.cursor().execute(
                "INSERT INTO dbo.Trabajo (id_obra, id_estado_trabajo, descripcion_tra, monto_total_tra, "
                "monto_sena_tra, observaciones_tra, fecha_presupuesto_tra, fecha_entrega_tra, "
                "entrega_aproximada_tra) OUTPUT INSERTED.id_trabajo VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                trabajo.id_obra, trabajo.id_estado, trabajo.descripcion, trabajo.monto_total,
                trabajo.monto_sena, trabajo.observaciones, trabajo.fecha_presupuesto, trabajo.fecha_entrega,
                1 if trabajo.entrega_aproximada else 0,
            ).fetchone()[0]

    def actualizar(self, trabajo: Trabajo) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                """UPDATE dbo.Trabajo SET
                       id_estado_trabajo = ?, descripcion_tra = ?, monto_total_tra = ?, monto_sena_tra = ?,
                       fecha_cobro_sena_tra = ?, fecha_comienzo_tra = ?, fecha_finalizacion_tra = ?,
                       fecha_entrega_tra = ?, fecha_cobro_saldo_tra = ?, observaciones_tra = ?,
                       fecha_presupuesto_tra = ?, entrega_aproximada_tra = ?
                   WHERE id_trabajo = ?""",
                trabajo.id_estado, trabajo.descripcion, trabajo.monto_total, trabajo.monto_sena,
                trabajo.fecha_cobro_sena, trabajo.fecha_comienzo, trabajo.fecha_finalizacion,
                trabajo.fecha_entrega, trabajo.fecha_cobro_saldo, trabajo.observaciones,
                trabajo.fecha_presupuesto, 1 if trabajo.entrega_aproximada else 0, trabajo.id,
            )

    def eliminar(self, id_trabajo: int) -> None:
        # El procedimiento borra el trabajo con todo lo que cuelga de él en una transacción.
        with conexion_abierta() as cn:
            cn.cursor().execute("{CALL dbo.sp_eliminar_trabajo (?)}", id_trabajo)
