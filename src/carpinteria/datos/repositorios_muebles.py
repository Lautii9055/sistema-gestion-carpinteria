"""Repositorio de muebles, módulos, cajones, zócalos y piezas sobre SQL Server.

Las FK de Pieza hacia sus dueños son NO ACTION (SQL Server no admite varios
caminos de borrado en cascada), por eso acá se borran primero las piezas y
después el dueño, siempre dentro de una transacción.
"""
from carpinteria.datos.conexion import conexion_abierta
from carpinteria.negocio.entidades import CajonGuardado, Cantos, ModuloGuardado, Mueble, PiezaGuardada, ZocaloGuardado

_COLUMNAS_PIEZA = """p.id_pieza, tp.nombre_tpi, p.id_material, p.cantidad_pie, p.medida_1_pie, p.medida_2_pie,
       p.id_mueble, p.id_modulo, p.id_cajon, p.id_zocalo, c.orden_caj, p.id_tipo_filo,
       p.lleva_filo_superior_pie, p.lleva_filo_inferior_pie, p.lleva_filo_izquierdo_pie, p.lleva_filo_derecho_pie,
       p.id_color_placa_filo, p.id_color_laca, p.id_terminacion_laca, p.descripcion_pie,
       p.es_editada_manualmente_pie, COALESCE(mp.cantidad_mod, mc.cantidad_mod, 1)"""
_DESDE_PIEZA = """FROM dbo.Pieza p
JOIN dbo.Tipo_Pieza tp ON tp.id_tipo_pieza = p.id_tipo_pieza
LEFT JOIN dbo.Cajon c  ON c.id_cajon = p.id_cajon
LEFT JOIN dbo.Modulo mp ON mp.id_modulo = p.id_modulo
LEFT JOIN dbo.Modulo mc ON mc.id_modulo = c.id_modulo"""

# Piezas de un trabajo: sueltas, de sus módulos, de los cajones de esos módulos y de sus zócalos.
_PIEZAS_DEL_TRABAJO = """
WITH m AS (SELECT id_mueble FROM dbo.Mueble WHERE id_trabajo = ?),
     mo AS (SELECT id_modulo FROM dbo.Modulo WHERE id_mueble IN (SELECT id_mueble FROM m))
SELECT {columnas} {desde}
WHERE p.id_mueble IN (SELECT id_mueble FROM m)
   OR p.id_modulo IN (SELECT id_modulo FROM mo)
   OR p.id_cajon  IN (SELECT id_cajon FROM dbo.Cajon WHERE id_modulo IN (SELECT id_modulo FROM mo))
   OR p.id_zocalo IN (SELECT id_zocalo FROM dbo.Zocalo WHERE id_mueble IN (SELECT id_mueble FROM m))
ORDER BY p.id_pieza"""


def _bit(valor: bool) -> int:
    return 1 if valor else 0


def _a_pieza(f) -> PiezaGuardada:
    return PiezaGuardada(f[0], f[1], f[2], f[3], f[4], f[5], id_mueble=f[6], id_modulo=f[7], id_cajon=f[8],
                         id_zocalo=f[9], orden_cajon=f[10], id_tipo_filo=f[11],
                         cantos=Cantos(bool(f[12]), bool(f[13]), bool(f[14]), bool(f[15])),
                         id_color_filo=f[16], id_color_laca=f[17], id_terminacion=f[18], descripcion=f[19],
                         editada=bool(f[20]), veces=f[21])


def _insertar_pieza(cursor, p: PiezaGuardada, *, id_mueble=None, id_modulo=None, id_cajon=None,
                    id_zocalo=None) -> int:
    c = p.cantos
    return cursor.execute(
        """INSERT INTO dbo.Pieza (id_mueble, id_modulo, id_cajon, id_zocalo, id_tipo_pieza, id_material,
                                  id_tipo_filo, id_color_placa_filo, id_color_laca, id_terminacion_laca,
                                  descripcion_pie, cantidad_pie, medida_1_pie, medida_2_pie,
                                  lleva_filo_superior_pie, lleva_filo_inferior_pie, lleva_filo_izquierdo_pie,
                                  lleva_filo_derecho_pie, es_editada_manualmente_pie)
           OUTPUT INSERTED.id_pieza
           VALUES (?, ?, ?, ?, (SELECT id_tipo_pieza FROM dbo.Tipo_Pieza WHERE nombre_tpi = ?), ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?, ?, ?)""",
        id_mueble if id_mueble is not None else p.id_mueble,
        id_modulo if id_modulo is not None else p.id_modulo,
        id_cajon if id_cajon is not None else p.id_cajon,
        id_zocalo if id_zocalo is not None else p.id_zocalo,
        p.tipo, p.id_material, p.id_tipo_filo, p.id_color_filo, p.id_color_laca, p.id_terminacion,
        p.descripcion, p.cantidad, p.medida_1, p.medida_2, _bit(c.superior), _bit(c.inferior), _bit(c.izquierdo),
        _bit(c.derecho), _bit(p.editada)).fetchone()[0]


class RepositorioMueblesSql:
    # ---------- muebles ----------
    def muebles(self, id_trabajo: int) -> list[Mueble]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                "SELECT id_mueble, id_trabajo, nombre_mue, observaciones_mue FROM dbo.Mueble "
                "WHERE id_trabajo = ? ORDER BY id_mueble", id_trabajo).fetchall()
        return [Mueble(*f) for f in filas]

    def mueble(self, id_mueble: int) -> Mueble | None:
        with conexion_abierta() as cn:
            f = cn.cursor().execute("SELECT id_mueble, id_trabajo, nombre_mue, observaciones_mue FROM dbo.Mueble "
                                    "WHERE id_mueble = ?", id_mueble).fetchone()
        return Mueble(*f) if f else None

    def guardar_mueble(self, mueble: Mueble) -> int:
        with conexion_abierta() as cn:
            if mueble.id is None:
                return cn.cursor().execute(
                    "INSERT INTO dbo.Mueble (id_trabajo, nombre_mue, observaciones_mue) OUTPUT INSERTED.id_mueble "
                    "VALUES (?, ?, ?)", mueble.id_trabajo, mueble.nombre, mueble.observaciones).fetchone()[0]
            cn.cursor().execute("UPDATE dbo.Mueble SET nombre_mue = ?, observaciones_mue = ? WHERE id_mueble = ?",
                                mueble.nombre, mueble.observaciones, mueble.id)
            return mueble.id

    def eliminar_mueble(self, id_mueble: int) -> None:
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            cursor.execute(
                """DELETE FROM dbo.Pieza
                   WHERE id_mueble = ?
                      OR id_modulo IN (SELECT id_modulo FROM dbo.Modulo WHERE id_mueble = ?)
                      OR id_cajon IN (SELECT c.id_cajon FROM dbo.Cajon c JOIN dbo.Modulo m ON m.id_modulo = c.id_modulo
                                      WHERE m.id_mueble = ?)
                      OR id_zocalo IN (SELECT id_zocalo FROM dbo.Zocalo WHERE id_mueble = ?)""",
                id_mueble, id_mueble, id_mueble, id_mueble)
            # Módulos, cajones, vetas rotadas y zócalos caen en cascada.
            cursor.execute("DELETE FROM dbo.Mueble WHERE id_mueble = ?", id_mueble)

    # ---------- módulos ----------
    def _leer_modulos(self, condicion: str, valor: int) -> list[ModuloGuardado]:
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            filas = cursor.execute(
                f"""SELECT m.id_modulo, m.id_mueble, ta.nombre_tar, m.id_placa, m.ancho_mod, m.alto_mod,
                           m.profundidad_mod, m.nombre_mod, m.id_estilo_frente, m.id_placa_frentes, m.id_placa_cajones,
                           m.id_placa_fondo, m.id_liston, m.id_color_laca_frentes, m.id_terminacion_laca_frentes,
                           m.lleva_techo_mod, m.ancho_faja_mod, m.cantidad_estantes_mod, m.cantidad_puertas_mod,
                           m.luz_superior_mod, m.luz_inferior_mod, m.luz_entre_frentes_mod,
                           m.luz_izquierda_mod, m.luz_derecha_mod, m.cantidad_mod
                    FROM dbo.Modulo m JOIN dbo.Tipo_Armado ta ON ta.id_tipo_armado = m.id_tipo_armado
                    WHERE {condicion} = ? ORDER BY m.id_modulo""", valor).fetchall()
            resultado = []
            for f in filas:
                cajones = cursor.execute(
                    "SELECT id_cajon, id_tipo_guia, id_placa_piso, alto_caj, largo_guia_caj, alto_frente_caj "
                    "FROM dbo.Cajon WHERE id_modulo = ? ORDER BY orden_caj", f[0]).fetchall()
                rotar = cursor.execute(
                    "SELECT tp.nombre_tpi FROM dbo.Modulo_Veta_Rotada r JOIN dbo.Tipo_Pieza tp "
                    "ON tp.id_tipo_pieza = r.id_tipo_pieza WHERE r.id_modulo = ?", f[0]).fetchall()
                resultado.append(ModuloGuardado(
                    f[0], f[1], f[2], f[3], f[4], f[5], f[6], nombre=f[7], id_estilo=f[8], id_placa_frentes=f[9],
                    id_placa_cajones=f[10], id_placa_fondo=f[11], id_liston=f[12], id_color_laca=f[13],
                    id_terminacion=f[14], lleva_techo=bool(f[15]), ancho_faja=f[16], estantes=f[17], puertas=f[18],
                    luz_superior=f[19], luz_inferior=f[20], luz_entre_frentes=f[21],
                    luz_izquierda=f[22], luz_derecha=f[23], cantidad=f[24],
                    cajones=tuple(CajonGuardado(*c) for c in cajones), rotar=frozenset(r[0] for r in rotar)))
        return resultado

    def modulos(self, id_mueble: int) -> list[ModuloGuardado]:
        return self._leer_modulos("m.id_mueble", id_mueble)

    def modulo(self, id_modulo: int) -> ModuloGuardado | None:
        lista = self._leer_modulos("m.id_modulo", id_modulo)
        return lista[0] if lista else None

    def guardar_modulo(self, m: ModuloGuardado, piezas_nuevas: list[PiezaGuardada]) -> int:
        valores = (m.id_estilo, m.id_placa, m.id_placa_frentes, m.id_placa_cajones, m.id_placa_fondo, m.id_liston,
                   m.id_color_laca, m.id_terminacion, m.nombre, m.ancho, m.alto, m.profundidad, _bit(m.lleva_techo),
                   m.ancho_faja, m.estantes, m.puertas, m.luz_superior, m.luz_inferior, m.luz_entre_frentes,
                   m.luz_izquierda, m.luz_derecha, m.cantidad)
        with conexion_abierta() as cn:   # todo o nada
            cursor = cn.cursor()
            fila = cursor.execute("SELECT id_tipo_armado FROM dbo.Tipo_Armado WHERE nombre_tar = ?", m.armado).fetchone()
            if fila is None:
                raise ValueError(f"Tipo de armado inexistente: {m.armado}")
            if m.id is None:
                id_modulo = cursor.execute(
                    """INSERT INTO dbo.Modulo (id_mueble, id_tipo_armado, id_estilo_frente, id_placa, id_placa_frentes,
                           id_placa_cajones, id_placa_fondo, id_liston, id_color_laca_frentes,
                           id_terminacion_laca_frentes, nombre_mod, ancho_mod, alto_mod, profundidad_mod,
                           lleva_techo_mod, ancho_faja_mod, cantidad_estantes_mod, cantidad_puertas_mod,
                           luz_superior_mod, luz_inferior_mod, luz_entre_frentes_mod,
                           luz_izquierda_mod, luz_derecha_mod, cantidad_mod)
                       OUTPUT INSERTED.id_modulo
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    m.id_mueble, fila[0], *valores).fetchone()[0]
            else:
                id_modulo = m.id
                cursor.execute(
                    """UPDATE dbo.Modulo SET id_tipo_armado = ?, id_estilo_frente = ?, id_placa = ?, id_placa_frentes = ?,
                           id_placa_cajones = ?, id_placa_fondo = ?, id_liston = ?, id_color_laca_frentes = ?,
                           id_terminacion_laca_frentes = ?, nombre_mod = ?, ancho_mod = ?, alto_mod = ?,
                           profundidad_mod = ?, lleva_techo_mod = ?, ancho_faja_mod = ?, cantidad_estantes_mod = ?,
                           cantidad_puertas_mod = ?, luz_superior_mod = ?, luz_inferior_mod = ?, luz_entre_frentes_mod = ?,
                           luz_izquierda_mod = ?, luz_derecha_mod = ?, cantidad_mod = ?
                       WHERE id_modulo = ?""", fila[0], *valores, id_modulo)

            # Cajones por orden (1 = arriba): se actualizan, se agregan o se borran con sus piezas.
            actuales = dict(cursor.execute("SELECT orden_caj, id_cajon FROM dbo.Cajon WHERE id_modulo = ?",
                                           id_modulo).fetchall())
            for orden, id_cajon in list(actuales.items()):
                if orden > len(m.cajones):
                    cursor.execute("DELETE FROM dbo.Pieza WHERE id_cajon = ?", id_cajon)
                    cursor.execute("DELETE FROM dbo.Cajon WHERE id_cajon = ?", id_cajon)
                    del actuales[orden]
            for orden, c in enumerate(m.cajones, 1):
                datos = (c.id_guia, c.id_placa_piso, c.alto_caja, c.alto_frente, c.largo_guia)
                if orden in actuales:
                    cursor.execute("UPDATE dbo.Cajon SET id_tipo_guia = ?, id_placa_piso = ?, alto_caj = ?, "
                                   "alto_frente_caj = ?, largo_guia_caj = ? WHERE id_cajon = ?", *datos, actuales[orden])
                else:
                    actuales[orden] = cursor.execute(
                        "INSERT INTO dbo.Cajon (id_tipo_guia, id_placa_piso, alto_caj, alto_frente_caj, largo_guia_caj, "
                        "id_modulo, orden_caj) OUTPUT INSERTED.id_cajon VALUES (?, ?, ?, ?, ?, ?, ?)",
                        *datos, id_modulo, orden).fetchone()[0]

            cursor.execute("DELETE FROM dbo.Modulo_Veta_Rotada WHERE id_modulo = ?", id_modulo)
            for tipo in sorted(m.rotar):
                cursor.execute("INSERT INTO dbo.Modulo_Veta_Rotada (id_modulo, id_tipo_pieza) "
                               "SELECT ?, id_tipo_pieza FROM dbo.Tipo_Pieza WHERE nombre_tpi = ?", id_modulo, tipo)

            # Las piezas calculadas se regeneran; las editadas a mano se conservan.
            cursor.execute("""DELETE FROM dbo.Pieza WHERE es_editada_manualmente_pie = 0
                                AND (id_modulo = ? OR id_cajon IN (SELECT id_cajon FROM dbo.Cajon WHERE id_modulo = ?))""",
                           id_modulo, id_modulo)
            for p in piezas_nuevas:
                if p.orden_cajon:
                    _insertar_pieza(cursor, p, id_cajon=actuales[p.orden_cajon])
                else:
                    _insertar_pieza(cursor, p, id_modulo=id_modulo)
        return id_modulo

    def eliminar_modulo(self, id_modulo: int) -> None:
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            cursor.execute("DELETE FROM dbo.Pieza WHERE id_modulo = ? "
                           "OR id_cajon IN (SELECT id_cajon FROM dbo.Cajon WHERE id_modulo = ?)", id_modulo, id_modulo)
            cursor.execute("DELETE FROM dbo.Modulo WHERE id_modulo = ?", id_modulo)

    # ---------- zócalos ----------
    _COLUMNAS_ZOCALO = ("id_zocalo, id_mueble, id_placa, largo_zoc, alto_zoc, profundidad_zoc, cantidad_refuerzos_zoc, "
                        "id_placa_oculta, descripcion_zoc")

    def zocalos(self, id_mueble: int) -> list[ZocaloGuardado]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(f"SELECT {self._COLUMNAS_ZOCALO} FROM dbo.Zocalo WHERE id_mueble = ? "
                                        "ORDER BY id_zocalo", id_mueble).fetchall()
        return [ZocaloGuardado(*f) for f in filas]

    def zocalo(self, id_zocalo: int) -> ZocaloGuardado | None:
        with conexion_abierta() as cn:
            f = cn.cursor().execute(f"SELECT {self._COLUMNAS_ZOCALO} FROM dbo.Zocalo WHERE id_zocalo = ?",
                                    id_zocalo).fetchone()
        return ZocaloGuardado(*f) if f else None

    def guardar_zocalo(self, z: ZocaloGuardado, piezas_nuevas: list[PiezaGuardada]) -> int:
        valores = (z.id_placa, z.id_placa_oculta, z.descripcion, z.largo, z.alto, z.profundidad, z.refuerzos)
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            if z.id is None:
                id_zocalo = cursor.execute(
                    "INSERT INTO dbo.Zocalo (id_placa, id_placa_oculta, descripcion_zoc, largo_zoc, alto_zoc, "
                    "profundidad_zoc, cantidad_refuerzos_zoc, id_mueble) OUTPUT INSERTED.id_zocalo "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", *valores, z.id_mueble).fetchone()[0]
            else:
                id_zocalo = z.id
                cursor.execute("UPDATE dbo.Zocalo SET id_placa = ?, id_placa_oculta = ?, descripcion_zoc = ?, "
                               "largo_zoc = ?, alto_zoc = ?, profundidad_zoc = ?, cantidad_refuerzos_zoc = ? "
                               "WHERE id_zocalo = ?", *valores, id_zocalo)
            cursor.execute("DELETE FROM dbo.Pieza WHERE id_zocalo = ? AND es_editada_manualmente_pie = 0", id_zocalo)
            for p in piezas_nuevas:
                _insertar_pieza(cursor, p, id_zocalo=id_zocalo)
        return id_zocalo

    def eliminar_zocalo(self, id_zocalo: int) -> None:
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            cursor.execute("DELETE FROM dbo.Pieza WHERE id_zocalo = ?", id_zocalo)
            cursor.execute("DELETE FROM dbo.Zocalo WHERE id_zocalo = ?", id_zocalo)

    # ---------- piezas ----------
    def _piezas(self, condicion: str, *valores) -> list[PiezaGuardada]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(f"SELECT {_COLUMNAS_PIEZA} {_DESDE_PIEZA} WHERE {condicion} "
                                        "ORDER BY p.id_pieza", *valores).fetchall()
        return [_a_pieza(f) for f in filas]

    def piezas_de_modulo(self, id_modulo: int) -> list[PiezaGuardada]:
        return self._piezas("p.id_modulo = ? OR c.id_modulo = ?", id_modulo, id_modulo)

    def piezas_de_zocalo(self, id_zocalo: int) -> list[PiezaGuardada]:
        return self._piezas("p.id_zocalo = ?", id_zocalo)

    def piezas_de_trabajo(self, id_trabajo: int) -> list[PiezaGuardada]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(_PIEZAS_DEL_TRABAJO.format(columnas=_COLUMNAS_PIEZA, desde=_DESDE_PIEZA),
                                        id_trabajo).fetchall()
        return [_a_pieza(f) for f in filas]

    def pieza(self, id_pieza: int) -> PiezaGuardada | None:
        lista = self._piezas("p.id_pieza = ?", id_pieza)
        return lista[0] if lista else None

    def guardar_pieza(self, p: PiezaGuardada) -> int:
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            if p.id is None:
                return _insertar_pieza(cursor, p)
            c = p.cantos
            cursor.execute(
                """UPDATE dbo.Pieza SET id_material = ?, id_tipo_filo = ?, id_color_placa_filo = ?, id_color_laca = ?,
                       id_terminacion_laca = ?, descripcion_pie = ?, cantidad_pie = ?, medida_1_pie = ?,
                       medida_2_pie = ?, lleva_filo_superior_pie = ?, lleva_filo_inferior_pie = ?,
                       lleva_filo_izquierdo_pie = ?, lleva_filo_derecho_pie = ?, es_editada_manualmente_pie = ?
                   WHERE id_pieza = ?""",
                p.id_material, p.id_tipo_filo, p.id_color_filo, p.id_color_laca, p.id_terminacion, p.descripcion,
                p.cantidad, p.medida_1, p.medida_2, _bit(c.superior), _bit(c.inferior), _bit(c.izquierdo),
                _bit(c.derecho), _bit(p.editada), p.id)
            return p.id

    def eliminar_pieza(self, id_pieza: int) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("DELETE FROM dbo.Pieza WHERE id_pieza = ?", id_pieza)

    def trabajo_de_pieza(self, id_pieza: int) -> int | None:
        with conexion_abierta() as cn:
            fila = cn.cursor().execute(
                """SELECT mu.id_trabajo
                   FROM dbo.Pieza p
                   LEFT JOIN dbo.Cajon c   ON c.id_cajon = p.id_cajon
                   LEFT JOIN dbo.Modulo mo ON mo.id_modulo = COALESCE(p.id_modulo, c.id_modulo)
                   LEFT JOIN dbo.Zocalo z  ON z.id_zocalo = p.id_zocalo
                   JOIN dbo.Mueble mu      ON mu.id_mueble = COALESCE(p.id_mueble, mo.id_mueble, z.id_mueble)
                   WHERE p.id_pieza = ?""", id_pieza).fetchone()
        return fila[0] if fila else None
