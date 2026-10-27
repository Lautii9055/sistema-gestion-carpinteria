"""Repositorios de clientes y obras sobre SQL Server.

Búsqueda segura: cada palabra viaja como parámetro y además se "escapan" los
comodines de LIKE (%, _ y [). Así, si alguien escribe "100%" se busca el texto
"100%" y no "100 seguido de cualquier cosa". La collation de la base
(Modern_Spanish_CI_AI) hace que no importen mayúsculas ni tildes.
"""
from carpinteria.datos.conexion import conexion_abierta
from carpinteria.negocio.entidades import Cliente, ClienteResumen, Obra, TrabajoResumen

# Teléfono sin espacios, guiones, + ni paréntesis, para comparar solo los números.
_TELEFONO_SOLO_DIGITOS = ("REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(c.telefono_cli, ' ', ''), "
                          "'-', ''), '+', ''), '(', ''), ')', '')")

_CONDICION_POR_TERMINO = f"""(
       c.nombre_cli   LIKE ? ESCAPE '\\'
    OR c.apellido_cli LIKE ? ESCAPE '\\'
    OR c.email_cli    LIKE ? ESCAPE '\\'
    OR (? <> '' AND {_TELEFONO_SOLO_DIGITOS} LIKE ?)
    OR c.id_cliente = TRY_CAST(? AS INT)
    OR EXISTS (SELECT 1 FROM dbo.Obra o
               WHERE o.id_cliente = c.id_cliente
                 AND (o.direccion_obr LIKE ? ESCAPE '\\'
                      OR o.localidad_obr LIKE ? ESCAPE '\\'
                      OR o.nombre_obr LIKE ? ESCAPE '\\'))
)"""


def escapar_like(texto: str) -> str:
    """Convierte un texto en un patrón "contiene" literal para LIKE."""
    for comodin in ("\\", "%", "_", "["):
        texto = texto.replace(comodin, "\\" + comodin)
    return f"%{texto}%"


def _parametros_termino(termino: str) -> list:
    patron = escapar_like(termino)
    digitos = "".join(ch for ch in termino if ch.isdigit())
    digitos_validos = digitos if len(digitos) >= 3 else ""
    return [patron, patron, patron,
            digitos_validos, f"%{digitos_validos}%",
            termino,
            patron, patron, patron]


def _a_cliente(f) -> Cliente:
    return Cliente(id=f.id_cliente, nombre=f.nombre_cli, apellido=f.apellido_cli,
                   telefono=f.telefono_cli, email=f.email_cli,
                   observaciones=f.observaciones_cli, es_activo=bool(f.es_activo_cli))


_COLUMNAS_CLIENTE = ("c.id_cliente, c.nombre_cli, c.apellido_cli, c.telefono_cli, c.email_cli, "
                     "c.observaciones_cli, c.es_activo_cli")


class RepositorioClientesSql:
    def buscar(self, terminos: list[str], incluir_inactivos: bool, limite: int) -> list[ClienteResumen]:
        condiciones = "".join(f"\n  AND {_CONDICION_POR_TERMINO}" for _ in terminos)
        sql = f"""
            SELECT TOP (?) {_COLUMNAS_CLIENTE},
                   (SELECT COUNT(*) FROM dbo.Obra o WHERE o.id_cliente = c.id_cliente) AS cantidad_obras,
                   (SELECT TOP (1) o.direccion_obr + N', ' + o.localidad_obr FROM dbo.Obra o
                    WHERE o.id_cliente = c.id_cliente ORDER BY o.id_obra) AS primera_direccion
            FROM dbo.Cliente c
            WHERE (? = 1 OR c.es_activo_cli = 1){condiciones}
            ORDER BY c.es_activo_cli DESC, c.apellido_cli, c.nombre_cli"""
        parametros = [limite, 1 if incluir_inactivos else 0]
        for termino in terminos:
            parametros += _parametros_termino(termino)
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(sql, *parametros).fetchall()
        return [ClienteResumen(_a_cliente(f), f.cantidad_obras, f.primera_direccion) for f in filas]

    def obtener(self, id_cliente: int) -> Cliente | None:
        with conexion_abierta() as cn:
            fila = cn.cursor().execute(
                f"SELECT {_COLUMNAS_CLIENTE} FROM dbo.Cliente c WHERE c.id_cliente = ?", id_cliente
            ).fetchone()
        return _a_cliente(fila) if fila else None

    def buscar_por_telefono(self, digitos: str) -> list[Cliente]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                f"SELECT {_COLUMNAS_CLIENTE} FROM dbo.Cliente c WHERE {_TELEFONO_SOLO_DIGITOS} = ?",
                digitos,
            ).fetchall()
        return [_a_cliente(f) for f in filas]

    def crear(self, cliente: Cliente, obra_inicial: Obra | None) -> int:
        # Cliente y primera obra en la misma transacción: o se guardan los dos o ninguno.
        with conexion_abierta() as cn:
            cursor = cn.cursor()
            nuevo_id = cursor.execute(
                "INSERT INTO dbo.Cliente (nombre_cli, apellido_cli, telefono_cli, email_cli, "
                "observaciones_cli) OUTPUT INSERTED.id_cliente VALUES (?, ?, ?, ?, ?)",
                cliente.nombre, cliente.apellido, cliente.telefono, cliente.email, cliente.observaciones,
            ).fetchone()[0]
            if obra_inicial is not None:
                cursor.execute(
                    "INSERT INTO dbo.Obra (id_cliente, nombre_obr, direccion_obr, localidad_obr, "
                    "observaciones_obr) VALUES (?, ?, ?, ?, ?)",
                    nuevo_id, obra_inicial.alias, obra_inicial.direccion, obra_inicial.localidad,
                    obra_inicial.observaciones,
                )
        return nuevo_id

    def actualizar(self, cliente: Cliente) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Cliente SET nombre_cli = ?, apellido_cli = ?, telefono_cli = ?, "
                "email_cli = ?, observaciones_cli = ? WHERE id_cliente = ?",
                cliente.nombre, cliente.apellido, cliente.telefono, cliente.email,
                cliente.observaciones, cliente.id,
            )

    def cambiar_estado(self, id_cliente: int, activo: bool) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute("UPDATE dbo.Cliente SET es_activo_cli = ? WHERE id_cliente = ?",
                                1 if activo else 0, id_cliente)


def _a_obra(f) -> Obra:
    return Obra(id=f.id_obra, id_cliente=f.id_cliente, direccion=f.direccion_obr,
                localidad=f.localidad_obr, alias=f.nombre_obr, observaciones=f.observaciones_obr)


class RepositorioObrasSql:
    def listar_por_cliente(self, id_cliente: int) -> list[Obra]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                "SELECT id_obra, id_cliente, nombre_obr, direccion_obr, localidad_obr, observaciones_obr "
                "FROM dbo.Obra WHERE id_cliente = ? ORDER BY id_obra", id_cliente,
            ).fetchall()
        return [_a_obra(f) for f in filas]

    def existe(self, id_cliente: int, direccion: str, localidad: str, excluir_id: int | None) -> bool:
        with conexion_abierta() as cn:
            return cn.cursor().execute(
                "SELECT COUNT(*) FROM dbo.Obra WHERE id_cliente = ? AND direccion_obr = ? "
                "AND localidad_obr = ? AND (? IS NULL OR id_obra <> ?)",
                id_cliente, direccion, localidad, excluir_id, excluir_id,
            ).fetchone()[0] > 0

    def crear(self, obra: Obra) -> int:
        with conexion_abierta() as cn:
            return cn.cursor().execute(
                "INSERT INTO dbo.Obra (id_cliente, nombre_obr, direccion_obr, localidad_obr, "
                "observaciones_obr) OUTPUT INSERTED.id_obra VALUES (?, ?, ?, ?, ?)",
                obra.id_cliente, obra.alias, obra.direccion, obra.localidad, obra.observaciones,
            ).fetchone()[0]

    def actualizar(self, obra: Obra) -> None:
        with conexion_abierta() as cn:
            cn.cursor().execute(
                "UPDATE dbo.Obra SET nombre_obr = ?, direccion_obr = ?, localidad_obr = ?, "
                "observaciones_obr = ? WHERE id_obra = ?",
                obra.alias, obra.direccion, obra.localidad, obra.observaciones, obra.id,
            )

    def trabajos_de_la_obra(self, id_obra: int) -> list[TrabajoResumen]:
        with conexion_abierta() as cn:
            filas = cn.cursor().execute(
                """SELECT t.id_trabajo, t.descripcion_tra, e.nombre_etr, t.fecha_alta_tra
                   FROM dbo.Trabajo t
                   JOIN dbo.Estado_Trabajo e ON e.id_estado_trabajo = t.id_estado_trabajo
                   WHERE t.id_obra = ?
                   ORDER BY t.fecha_alta_tra DESC""", id_obra,
            ).fetchall()
        return [TrabajoResumen(f[0], f[1], f[2], f[3]) for f in filas]
