"""Repositorio del catálogo de placas y listones sobre SQL Server.

El catálogo es chico (decenas o cientos de filas): se lee completo y se filtra
en la capa de negocio. Todo valor viaja como parámetro.
"""
from carpinteria.datos.conexion import conexion_abierta
from carpinteria.negocio.entidades import ColorPlaca, Liston, MarcaPlaca, Placa

# Una placa está "en uso" si la referencia cualquier parte de un trabajo o un retazo.
_PLACA_EN_USO = """(
       EXISTS (SELECT 1 FROM dbo.Modulo m WHERE p.id_placa IN (m.id_placa, m.id_placa_frentes,
                                                                m.id_placa_cajones, m.id_placa_fondo))
    OR EXISTS (SELECT 1 FROM dbo.Zocalo z WHERE p.id_placa IN (z.id_placa, z.id_placa_oculta))
    OR EXISTS (SELECT 1 FROM dbo.Cajon c WHERE c.id_placa_piso = p.id_placa)
    OR EXISTS (SELECT 1 FROM dbo.Pieza pz WHERE pz.id_material = p.id_placa)
    OR EXISTS (SELECT 1 FROM dbo.Retazo r WHERE r.id_placa = p.id_placa))"""


class RepositorioMaterialesSql:
    # ---------- marcas ----------
    def marcas(self) -> list[MarcaPlaca]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                "SELECT id_marca_placa, nombre_mpl, es_activo_mpl FROM dbo.Marca_Placa").fetchall()
        return [MarcaPlaca(f[0], f[1], bool(f[2])) for f in filas]

    def crear_marca(self, marca: MarcaPlaca) -> int:
        with conexion_abierta() as cn:
            return cn.cursor().execute(
                "INSERT INTO dbo.Marca_Placa (nombre_mpl) OUTPUT INSERTED.id_marca_placa VALUES (?)",
                marca.nombre).fetchone()[0]

    def actualizar_marca(self, marca: MarcaPlaca) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("UPDATE dbo.Marca_Placa SET nombre_mpl = ?, es_activo_mpl = ? "
                                "WHERE id_marca_placa = ?", marca.nombre, 1 if marca.es_activo else 0, marca.id)

    def eliminar_marca(self, id_marca: int) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Marca_Placa WHERE id_marca_placa = ?", id_marca)

    def marca_en_uso(self, id_marca: int) -> bool:
        with conexion_abierta() as cn:
            return cn.cursor().execute("SELECT COUNT(*) FROM dbo.Color_Placa WHERE id_marca_placa = ?",
                                       id_marca).fetchone()[0] > 0

    # ---------- colores ----------
    def colores(self) -> list[ColorPlaca]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                """SELECT c.id_color_placa, c.id_marca_placa, c.nombre_cpl, c.codigo_cpl, c.tiene_veta_cpl,
                          c.es_activo_cpl, m.nombre_mpl, m.es_activo_mpl
                   FROM dbo.Color_Placa c JOIN dbo.Marca_Placa m ON m.id_marca_placa = c.id_marca_placa"""
            ).fetchall()
        return [ColorPlaca(f[0], f[1], f[2], f[3], bool(f[4]), bool(f[5]), f[6], bool(f[7])) for f in filas]

    def crear_color(self, color: ColorPlaca) -> int:
        with conexion_abierta() as cn:
            return cn.cursor().execute(
                "INSERT INTO dbo.Color_Placa (id_marca_placa, nombre_cpl, codigo_cpl, tiene_veta_cpl) "
                "OUTPUT INSERTED.id_color_placa VALUES (?, ?, ?, ?)",
                color.id_marca, color.nombre, color.codigo, 1 if color.tiene_veta else 0).fetchone()[0]

    def actualizar_color(self, color: ColorPlaca) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Color_Placa SET id_marca_placa = ?, nombre_cpl = ?, codigo_cpl = ?, "
                "tiene_veta_cpl = ?, es_activo_cpl = ? WHERE id_color_placa = ?",
                color.id_marca, color.nombre, color.codigo, 1 if color.tiene_veta else 0,
                1 if color.es_activo else 0, color.id)

    def eliminar_color(self, id_color: int) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Color_Placa WHERE id_color_placa = ?", id_color)

    def color_en_uso(self, id_color: int) -> bool:
        with conexion_abierta() as cn:
            return cn.cursor().execute(
                """SELECT CASE WHEN EXISTS (SELECT 1 FROM dbo.Placa WHERE id_color_placa = ?)
                                 OR EXISTS (SELECT 1 FROM dbo.Pieza WHERE id_color_placa_filo = ?)
                               THEN 1 ELSE 0 END""", id_color, id_color).fetchone()[0] == 1

    # ---------- placas ----------
    def placas(self) -> list[Placa]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                f"""SELECT p.id_placa, p.id_color_placa, p.espesor_pla, p.largo_pla, p.ancho_pla, p.es_activo_pla,
                           c.id_marca_placa, c.nombre_cpl, c.codigo_cpl, c.tiene_veta_cpl, c.es_activo_cpl,
                           m.nombre_mpl, m.es_activo_mpl,
                           CASE WHEN {_PLACA_EN_USO} THEN 1 ELSE 0 END AS en_uso
                    FROM dbo.Placa p
                    JOIN dbo.Color_Placa c ON c.id_color_placa = p.id_color_placa
                    JOIN dbo.Marca_Placa m ON m.id_marca_placa = c.id_marca_placa"""
            ).fetchall()
        return [Placa(f[0], f[1], f[2], f[3], f[4], bool(f[5]),
                      ColorPlaca(f[1], f[6], f[7], f[8], bool(f[9]), bool(f[10]), f[11], bool(f[12])),
                      bool(f[13])) for f in filas]

    def crear_placa(self, placa: Placa) -> int:
        # Generalización Material → Placa: las dos filas en la misma transacción.
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            nuevo = cursor.execute("INSERT INTO dbo.Material (tipo_mat) OUTPUT INSERTED.id_material "
                                   "VALUES ('PLACA')").fetchone()[0]
            cursor.execute("INSERT INTO dbo.Placa (id_placa, id_color_placa, espesor_pla, largo_pla, ancho_pla) "
                           "VALUES (?, ?, ?, ?, ?)", nuevo, placa.id_color, placa.espesor, placa.largo, placa.ancho)
        return nuevo

    def actualizar_placa(self, placa: Placa) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Placa SET id_color_placa = ?, espesor_pla = ?, largo_pla = ?, ancho_pla = ?, "
                "es_activo_pla = ? WHERE id_placa = ?",
                placa.id_color, placa.espesor, placa.largo, placa.ancho, 1 if placa.es_activo else 0, placa.id)

    def eliminar_placa(self, id_placa: int) -> None:
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            cursor.execute("DELETE FROM dbo.Placa WHERE id_placa = ?", id_placa)
            cursor.execute("DELETE FROM dbo.Material WHERE id_material = ? AND tipo_mat = 'PLACA'", id_placa)

    # ---------- listones ----------
    def listones(self) -> list[Liston]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                """SELECT l.id_liston, l.nombre_lis, l.seccion_ancho_pulg_lis, l.seccion_alto_pulg_lis,
                          l.es_activo_lis,
                          CASE WHEN EXISTS (SELECT 1 FROM dbo.Modulo m WHERE m.id_liston = l.id_liston)
                                 OR EXISTS (SELECT 1 FROM dbo.Pieza pz WHERE pz.id_material = l.id_liston)
                               THEN 1 ELSE 0 END
                   FROM dbo.Liston l""").fetchall()
        return [Liston(f[0], f[1], f[2], f[3], bool(f[4]), bool(f[5])) for f in filas]

    def crear_liston(self, liston: Liston) -> int:
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            nuevo = cursor.execute("INSERT INTO dbo.Material (tipo_mat) OUTPUT INSERTED.id_material "
                                   "VALUES ('LISTON')").fetchone()[0]
            cursor.execute("INSERT INTO dbo.Liston (id_liston, nombre_lis, seccion_ancho_pulg_lis, "
                           "seccion_alto_pulg_lis) VALUES (?, ?, ?, ?)",
                           nuevo, liston.nombre, liston.ancho_pulgadas, liston.alto_pulgadas)
        return nuevo

    def actualizar_liston(self, liston: Liston) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Liston SET nombre_lis = ?, seccion_ancho_pulg_lis = ?, seccion_alto_pulg_lis = ?, "
                "es_activo_lis = ? WHERE id_liston = ?",
                liston.nombre, liston.ancho_pulgadas, liston.alto_pulgadas, 1 if liston.es_activo else 0,
                liston.id)

    def eliminar_liston(self, id_liston: int) -> None:
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            cursor.execute("DELETE FROM dbo.Liston WHERE id_liston = ?", id_liston)
            cursor.execute("DELETE FROM dbo.Material WHERE id_material = ? AND tipo_mat = 'LISTON'", id_liston)
