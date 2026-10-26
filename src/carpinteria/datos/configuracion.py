"""Configuración de la conexión a la base de datos.

Acá solo hay datos que NO son secretos (servidor, base, usuario, driver).
La contraseña nunca está en el código: se guarda en el Administrador de
credenciales de Windows (ver credenciales.py).

Cada valor se puede cambiar con una variable de entorno, por ejemplo para
instalar el sistema en otra PC con otro nombre de instancia, sin tocar el código.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfiguracionBD:
    servidor: str
    base_de_datos: str
    usuario: str
    driver: str


def cargar_configuracion() -> ConfiguracionBD:
    return ConfiguracionBD(
        servidor=os.environ.get("CARPINTERIA_SERVIDOR", r"localhost\SQLEXPRESS"),
        base_de_datos=os.environ.get("CARPINTERIA_BASE", "Carpinteria"),
        usuario=os.environ.get("CARPINTERIA_USUARIO_BD", "app_carpinteria"),
        driver=os.environ.get("CARPINTERIA_DRIVER", "ODBC Driver 18 for SQL Server"),
    )
