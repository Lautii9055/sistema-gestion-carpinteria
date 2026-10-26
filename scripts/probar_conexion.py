"""Prueba la conexión y verifica el mínimo privilegio del usuario de la aplicación.

Uso (con el entorno virtual activo, desde la raíz del proyecto):
    python scripts/probar_conexion.py
"""
from carpinteria.datos.conexion import ErrorConexion, obtener_conexion

# (objeto, permiso, valor esperado) -> 1 = permitido, 0 = denegado
PERMISOS_ESPERADOS = [
    ("dbo.Trabajo",     "SELECT", 1),
    ("dbo.Trabajo",     "DELETE", 1),
    ("dbo.Auditoria",   "INSERT", 1),
    ("dbo.Auditoria",   "UPDATE", 0),
    ("dbo.Auditoria",   "DELETE", 0),
    ("dbo.Tipo_Evento", "INSERT", 0),
]


def main() -> None:
    try:
        conexion = obtener_conexion()
    except ErrorConexion as error:
        print(f"ERROR: {error}")
        return

    try:
        cursor = conexion.cursor()

        cursor.execute("SELECT SUSER_SNAME(), DB_NAME()")
        usuario, base = cursor.fetchone()
        print(f"Conectado como '{usuario}' a la base '{base}'.")

        cursor.execute("SELECT nombre_etr FROM dbo.Estado_Trabajo ORDER BY orden_etr")
        estados = [fila.nombre_etr for fila in cursor.fetchall()]
        print(f"Estados de trabajo cargados ({len(estados)}): {', '.join(estados)}")

        print("\nVerificación de mínimo privilegio:")
        todo_ok = True
        for objeto, permiso, esperado in PERMISOS_ESPERADOS:
            # Consulta parametrizada: los valores viajan aparte del SQL.
            cursor.execute("SELECT HAS_PERMS_BY_NAME(?, 'OBJECT', ?)", objeto, permiso)
            real = cursor.fetchone()[0]
            ok = real == esperado
            todo_ok &= ok
            estado = "permitido" if real == 1 else "denegado "
            print(f"  [{'OK ' if ok else 'MAL'}] {permiso:<6} sobre {objeto:<16} {estado}")

        cursor.execute("SELECT HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'ALTER')")
        puede_alterar = cursor.fetchone()[0]
        todo_ok &= puede_alterar == 0
        print(f"  [{'OK ' if puede_alterar == 0 else 'MAL'}] ALTER  sobre la base          "
              f"{'permitido' if puede_alterar else 'denegado '}")

        print("\nTodo en orden." if todo_ok else "\nHay permisos distintos de los esperados: revisar 05_seguridad.sql.")
    finally:
        conexion.close()


if __name__ == "__main__":
    main()
