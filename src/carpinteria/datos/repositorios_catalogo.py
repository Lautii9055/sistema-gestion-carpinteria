"""Repositorio de filos, lacas, estilos de frente y guías sobre SQL Server.

Catálogos chicos: se leen completos y se filtran en la capa de negocio. Todo
valor viaja como parámetro. "en_uso" se calcula con EXISTS contra las tablas
de trabajos.
"""
from decimal import Decimal

from carpinteria.datos.conexion import conexion_abierta
from carpinteria.negocio.entidades import (ColorLaca, EstiloFrente, MarcaPintura, PiezaGuia, TerminacionLaca,
                                          TipoFilo, TipoGuia)


def _bit(valor: bool) -> int:
    return 1 if valor else 0


class RepositorioCatalogoSql:
    # ---------- filos ----------
    def filos(self) -> list[TipoFilo]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                """SELECT f.id_tipo_filo, f.nombre_tfi, f.espesor_mm_tfi, f.descuento_por_canto_tfi,
                          CASE WHEN EXISTS (SELECT 1 FROM dbo.Pieza p WHERE p.id_tipo_filo = f.id_tipo_filo)
                               THEN 1 ELSE 0 END
                   FROM dbo.Tipo_Filo f""").fetchall()
        return [TipoFilo(f[0], f[1], f[2], f[3], bool(f[4])) for f in filas]

    def guardar_filo(self, filo: TipoFilo) -> int:
        with conexion_abierta() as cn:
            if filo.id is None:
                return cn.cursor().execute(
                    "INSERT INTO dbo.Tipo_Filo (nombre_tfi, espesor_mm_tfi, descuento_por_canto_tfi) "
                    "OUTPUT INSERTED.id_tipo_filo VALUES (?, ?, ?)",
                    filo.nombre, filo.espesor_mm, filo.descuento_cm).fetchone()[0]
            cn.cursor().execute(
                "UPDATE dbo.Tipo_Filo SET nombre_tfi = ?, espesor_mm_tfi = ?, descuento_por_canto_tfi = ? "
                "WHERE id_tipo_filo = ?", filo.nombre, filo.espesor_mm, filo.descuento_cm, filo.id)
            return filo.id

    def eliminar_filo(self, id_filo: int) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Tipo_Filo WHERE id_tipo_filo = ?", id_filo)

    # ---------- lacas ----------
    def marcas_pintura(self) -> list[MarcaPintura]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                "SELECT id_marca_pintura, nombre_mpi, es_activo_mpi FROM dbo.Marca_Pintura").fetchall()
        return [MarcaPintura(f[0], f[1], bool(f[2])) for f in filas]

    def guardar_marca_pintura(self, marca: MarcaPintura) -> int:
        with conexion_abierta() as cn:
            if marca.id is None:
                return cn.cursor().execute(
                    "INSERT INTO dbo.Marca_Pintura (nombre_mpi) OUTPUT INSERTED.id_marca_pintura VALUES (?)",
                    marca.nombre).fetchone()[0]
            cn.cursor().execute("UPDATE dbo.Marca_Pintura SET nombre_mpi = ?, es_activo_mpi = ? "
                                "WHERE id_marca_pintura = ?", marca.nombre, _bit(marca.es_activo), marca.id)
            return marca.id

    def eliminar_marca_pintura(self, id_marca: int) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Marca_Pintura WHERE id_marca_pintura = ?", id_marca)

    def colores_laca(self) -> list[ColorLaca]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                """SELECT c.id_color_laca, c.id_marca_pintura, c.nombre_cla, c.codigo_cla, c.es_activo_cla,
                          m.nombre_mpi, m.es_activo_mpi,
                          CASE WHEN EXISTS (SELECT 1 FROM dbo.Modulo x WHERE x.id_color_laca_frentes = c.id_color_laca)
                                 OR EXISTS (SELECT 1 FROM dbo.Pieza p WHERE p.id_color_laca = c.id_color_laca)
                               THEN 1 ELSE 0 END
                   FROM dbo.Color_Laca c JOIN dbo.Marca_Pintura m ON m.id_marca_pintura = c.id_marca_pintura"""
            ).fetchall()
        return [ColorLaca(f[0], f[1], f[2], f[3], bool(f[4]), f[5], bool(f[6]), bool(f[7])) for f in filas]

    def guardar_color_laca(self, color: ColorLaca) -> int:
        with conexion_abierta() as cn:
            if color.id is None:
                return cn.cursor().execute(
                    "INSERT INTO dbo.Color_Laca (id_marca_pintura, nombre_cla, codigo_cla) "
                    "OUTPUT INSERTED.id_color_laca VALUES (?, ?, ?)",
                    color.id_marca, color.nombre, color.codigo).fetchone()[0]
            cn.cursor().execute(
                "UPDATE dbo.Color_Laca SET id_marca_pintura = ?, nombre_cla = ?, codigo_cla = ?, es_activo_cla = ? "
                "WHERE id_color_laca = ?", color.id_marca, color.nombre, color.codigo, _bit(color.es_activo), color.id)
            return color.id

    def eliminar_color_laca(self, id_color: int) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Color_Laca WHERE id_color_laca = ?", id_color)

    def terminaciones(self) -> list[TerminacionLaca]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                """SELECT t.id_terminacion_laca, t.nombre_tla, t.es_activo_tla,
                          CASE WHEN EXISTS (SELECT 1 FROM dbo.Modulo x
                                            WHERE x.id_terminacion_laca_frentes = t.id_terminacion_laca)
                                 OR EXISTS (SELECT 1 FROM dbo.Pieza p WHERE p.id_terminacion_laca = t.id_terminacion_laca)
                               THEN 1 ELSE 0 END
                   FROM dbo.Terminacion_Laca t ORDER BY t.id_terminacion_laca""").fetchall()
        return [TerminacionLaca(f[0], f[1], bool(f[2]), bool(f[3])) for f in filas]

    def guardar_terminacion(self, terminacion: TerminacionLaca) -> int:
        with conexion_abierta() as cn:
            if terminacion.id is None:
                return cn.cursor().execute(
                    "INSERT INTO dbo.Terminacion_Laca (nombre_tla) OUTPUT INSERTED.id_terminacion_laca VALUES (?)",
                    terminacion.nombre).fetchone()[0]
            cn.cursor().execute("UPDATE dbo.Terminacion_Laca SET nombre_tla = ?, es_activo_tla = ? "
                                "WHERE id_terminacion_laca = ?",
                                terminacion.nombre, _bit(terminacion.es_activo), terminacion.id)
            return terminacion.id

    def eliminar_terminacion(self, id_terminacion: int) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Terminacion_Laca WHERE id_terminacion_laca = ?", id_terminacion)

    # ---------- estilos de frente ----------
    def estilos(self) -> list[EstiloFrente]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                """SELECT e.id_estilo_frente, e.nombre_efr, e.luz_superior_efr, e.luz_inferior_efr,
                          e.luz_entre_frentes_efr, e.descripcion_efr, e.es_activo_efr,
                          CASE WHEN EXISTS (SELECT 1 FROM dbo.Modulo m WHERE m.id_estilo_frente = e.id_estilo_frente)
                               THEN 1 ELSE 0 END
                   FROM dbo.Estilo_Frente e""").fetchall()
        return [EstiloFrente(f[0], f[1], f[2], f[3], f[4], f[5], bool(f[6]), bool(f[7])) for f in filas]

    def guardar_estilo(self, estilo: EstiloFrente) -> int:
        valores = (estilo.nombre, estilo.luz_superior, estilo.luz_inferior, estilo.luz_entre_frentes,
                   estilo.descripcion)
        with conexion_abierta() as cn:
            if estilo.id is None:
                return cn.cursor().execute(
                    "INSERT INTO dbo.Estilo_Frente (nombre_efr, luz_superior_efr, luz_inferior_efr, "
                    "luz_entre_frentes_efr, descripcion_efr) OUTPUT INSERTED.id_estilo_frente VALUES (?, ?, ?, ?, ?)",
                    *valores).fetchone()[0]
            cn.cursor().execute(
                "UPDATE dbo.Estilo_Frente SET nombre_efr = ?, luz_superior_efr = ?, luz_inferior_efr = ?, "
                "luz_entre_frentes_efr = ?, descripcion_efr = ?, es_activo_efr = ? WHERE id_estilo_frente = ?",
                *valores, _bit(estilo.es_activo), estilo.id)
            return estilo.id

    def eliminar_estilo(self, id_estilo: int) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Estilo_Frente WHERE id_estilo_frente = ?", id_estilo)

    # ---------- guías ----------
    def guias(self) -> list[TipoGuia]:
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            tipos = cursor.execute(
                """SELECT g.id_tipo_guia, g.nombre_tgu, g.marca_tgu, g.espacio_adicional_tgu, g.es_activo_tgu,
                          CASE WHEN EXISTS (SELECT 1 FROM dbo.Cajon c WHERE c.id_tipo_guia = g.id_tipo_guia)
                               THEN 1 ELSE 0 END
                   FROM dbo.Tipo_Guia g""").fetchall()
            largos = cursor.execute("SELECT id_tipo_guia, largo_lgu FROM dbo.Largo_Guia ORDER BY largo_lgu").fetchall()
            piezas = cursor.execute(
                """SELECT pg.id_tipo_guia, pg.id_tipo_pieza, tp.nombre_tpi, pg.cantidad_pgu, pg.descuento_ancho_pgu,
                          pg.descuento_largo_pgu, pg.descuento_alto_pgu, pg.alto_fijo_pgu
                   FROM dbo.Pieza_Guia pg JOIN dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = pg.id_tipo_pieza
                   ORDER BY pg.id_pieza_guia""").fetchall()
        return [TipoGuia(t[0], t[1], t[2], t[3], bool(t[4]), bool(t[5]),
                         tuple(f[1] for f in largos if f[0] == t[0]),
                         tuple(PiezaGuia(f[1], f[2], f[3], f[4], f[5], f[6], f[7]) for f in piezas if f[0] == t[0]))
                for t in tipos]

    def guardar_guia(self, guia: TipoGuia) -> int:
        with conexion_abierta() as cn:
            if guia.id is None:
                return cn.cursor().execute(
                    "INSERT INTO dbo.Tipo_Guia (nombre_tgu, marca_tgu, espacio_adicional_tgu) "
                    "OUTPUT INSERTED.id_tipo_guia VALUES (?, ?, ?)",
                    guia.nombre, guia.marca, guia.espacio_adicional).fetchone()[0]
            cn.cursor().execute(
                "UPDATE dbo.Tipo_Guia SET nombre_tgu = ?, marca_tgu = ?, espacio_adicional_tgu = ?, es_activo_tgu = ? "
                "WHERE id_tipo_guia = ?", guia.nombre, guia.marca, guia.espacio_adicional, _bit(guia.es_activo),
                guia.id)
            return guia.id

    def eliminar_guia(self, id_guia: int) -> None:
        # Largos y piezas de la guía se borran en cascada (FK ON DELETE CASCADE).
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Tipo_Guia WHERE id_tipo_guia = ?", id_guia)

    def copiar_piezas_guia(self, id_origen: int, id_destino: int) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                """INSERT INTO dbo.Pieza_Guia (id_tipo_guia, id_tipo_pieza, cantidad_pgu, descuento_ancho_pgu,
                                               descuento_largo_pgu, descuento_alto_pgu, alto_fijo_pgu)
                   SELECT ?, id_tipo_pieza, cantidad_pgu, descuento_ancho_pgu, descuento_largo_pgu,
                          descuento_alto_pgu, alto_fijo_pgu
                   FROM dbo.Pieza_Guia WHERE id_tipo_guia = ?""", id_destino, id_origen)

    def agregar_largo_guia(self, id_guia: int, largo: Decimal) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("INSERT INTO dbo.Largo_Guia (id_tipo_guia, largo_lgu) VALUES (?, ?)", id_guia, largo)

    def quitar_largo_guia(self, id_guia: int, largo: Decimal) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Largo_Guia WHERE id_tipo_guia = ? AND largo_lgu = ?", id_guia, largo)

    def guardar_pieza_guia(self, id_guia: int, pieza: PiezaGuia) -> None:
        valores = (pieza.cantidad, pieza.descuento_ancho, pieza.descuento_largo, pieza.descuento_alto, pieza.alto_fijo)
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            existe = cursor.execute("SELECT COUNT(*) FROM dbo.Pieza_Guia WHERE id_tipo_guia = ? AND id_tipo_pieza = ?",
                                    id_guia, pieza.id_tipo_pieza).fetchone()[0]
            if existe:
                cursor.execute(
                    "UPDATE dbo.Pieza_Guia SET cantidad_pgu = ?, descuento_ancho_pgu = ?, descuento_largo_pgu = ?, "
                    "descuento_alto_pgu = ?, alto_fijo_pgu = ? WHERE id_tipo_guia = ? AND id_tipo_pieza = ?",
                    *valores, id_guia, pieza.id_tipo_pieza)
            else:
                cursor.execute(
                    "INSERT INTO dbo.Pieza_Guia (cantidad_pgu, descuento_ancho_pgu, descuento_largo_pgu, "
                    "descuento_alto_pgu, alto_fijo_pgu, id_tipo_guia, id_tipo_pieza) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    *valores, id_guia, pieza.id_tipo_pieza)

    def id_tipo_pieza(self, nombre: str) -> int | None:
        with conexion_abierta() as cn:
            fila = cn.cursor().execute("SELECT id_tipo_pieza FROM dbo.Tipo_Pieza WHERE nombre_tpi = ?",
                                       nombre).fetchone()
        return fila[0] if fila else None
