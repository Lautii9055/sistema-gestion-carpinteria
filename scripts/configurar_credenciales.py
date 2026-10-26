"""Configuración inicial: guarda la contraseña de app_carpinteria de forma segura.

Uso (con el entorno virtual activo, desde la raíz del proyecto):
    python scripts/configurar_credenciales.py

La contraseña se escribe sin que se vea en pantalla, se prueba conectándose a la
base y, solo si la conexión funciona, se guarda en el Administrador de
credenciales de Windows.
"""
from getpass import getpass

from carpinteria.datos.conexion import ErrorConexion, obtener_conexion
from carpinteria.datos.configuracion import cargar_configuracion
from carpinteria.datos.credenciales import guardar_contrasena, obtener_contrasena


def main() -> None:
    config = cargar_configuracion()
    print(f"Servidor: {config.servidor} | Base: {config.base_de_datos} | Usuario: {config.usuario}")

    if obtener_contrasena(config.usuario):
        respuesta = input("Ya hay una contraseña guardada. ¿Reemplazarla? (s/n): ")
        if respuesta.strip().lower() != "s":
            print("Sin cambios.")
            return

    contrasena = getpass(f"Contraseña de {config.usuario} (no se muestra al escribir): ")
    if not contrasena:
        print("No se ingresó ninguna contraseña. Sin cambios.")
        return

    print("Probando la conexión...")
    try:
        obtener_conexion(config, contrasena).close()
    except ErrorConexion as error:
        print(f"No se guardó la contraseña: {error}")
        return

    guardar_contrasena(config.usuario, contrasena)
    print("Conexión correcta. Contraseña guardada en el Administrador de credenciales de Windows.")


if __name__ == "__main__":
    main()
