"""Conexión a SQL Server.

Es el único lugar del sistema que arma la cadena de conexión. Los repositorios
piden una conexión con obtener_conexion() y no saben nada de servidores,
drivers ni contraseñas.
"""
import pyodbc

from carpinteria.datos.configuracion import ConfiguracionBD, cargar_configuracion
from carpinteria.datos.credenciales import obtener_contrasena


class ErrorConexion(Exception):
    """No se pudo conectar a la base. El mensaje es apto para mostrar al usuario:
    nunca incluye la contraseña ni la cadena de conexión."""


def _escapar(valor: str) -> str:
    """Encierra un valor entre llaves para la cadena ODBC.

    Así una contraseña con ';' o '=' no puede "romper" la cadena ni agregarle
    parámetros (es la misma idea que las consultas parametrizadas contra la
    inyección SQL). Dentro de las llaves, una '}' se escribe '}}'.
    """
    return "{" + valor.replace("}", "}}") + "}"


def armar_cadena_conexion(config: ConfiguracionBD, contrasena: str) -> str:
    partes = [
        f"DRIVER={_escapar(config.driver)}",
        f"SERVER={_escapar(config.servidor)}",
        f"DATABASE={_escapar(config.base_de_datos)}",
        f"UID={_escapar(config.usuario)}",
        f"PWD={_escapar(contrasena)}",
        # El driver 18 cifra la conexión por defecto. La instancia local usa un
        # certificado autofirmado, por eso se confía en él. Si la base pasara a
        # otra PC de la red, habría que instalar un certificado válido y quitar
        # TrustServerCertificate.
        "Encrypt=yes",
        "TrustServerCertificate=yes",
        "APP=SistemaCarpinteria",
    ]
    return ";".join(partes) + ";"


def obtener_conexion(config: ConfiguracionBD | None = None,
                     contrasena: str | None = None) -> pyodbc.Connection:
    """Abre una conexión con el usuario de la aplicación (mínimo privilegio).

    Si no se pasa la contraseña, se toma del Administrador de credenciales.
    """
    config = config or cargar_configuracion()
    contrasena = contrasena if contrasena is not None else obtener_contrasena(config.usuario)
    if not contrasena:
        raise ErrorConexion(
            "La conexión a la base no está configurada. "
            "Ejecutá: python scripts/configurar_credenciales.py"
        )
    try:
        return pyodbc.connect(armar_cadena_conexion(config, contrasena), timeout=5)
    except pyodbc.Error as error:
        # Se traduce el error sin propagar la cadena de conexión.
        estado = error.args[0] if error.args else ""
        if estado == "28000":
            raise ErrorConexion("Usuario o contraseña de la base incorrectos.") from None
        raise ErrorConexion(
            "No se pudo conectar a la base de datos. "
            "Verificá que SQL Server esté iniciado."
        ) from None
