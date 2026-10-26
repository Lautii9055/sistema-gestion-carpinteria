"""Pruebas de la cadena de conexión (no necesitan una base de datos)."""
import pytest

from carpinteria.datos.conexion import ErrorConexion, armar_cadena_conexion, obtener_conexion
from carpinteria.datos.configuracion import ConfiguracionBD

CONFIG = ConfiguracionBD(
    servidor=r"localhost\SQLEXPRESS",
    base_de_datos="Carpinteria",
    usuario="app_carpinteria",
    driver="ODBC Driver 18 for SQL Server",
)


def test_la_cadena_incluye_los_datos_de_conexion():
    cadena = armar_cadena_conexion(CONFIG, "Clave123")
    assert r"SERVER={localhost\SQLEXPRESS}" in cadena
    assert "DATABASE={Carpinteria}" in cadena
    assert "UID={app_carpinteria}" in cadena
    assert "Encrypt=yes" in cadena


def test_una_contrasena_con_punto_y_coma_no_agrega_parametros():
    # Intento de "inyección" en la cadena de conexión: si no se escapara, el
    # ';' cortaría la contraseña y DATABASE=master se tomaría como parámetro.
    maliciosa = "abc;DATABASE=master"
    cadena = armar_cadena_conexion(CONFIG, maliciosa)
    assert "PWD={abc;DATABASE=master}" in cadena
    assert cadena.count("DATABASE=") == 2  # el real y el que quedó encerrado en la contraseña
    assert "DATABASE={Carpinteria}" in cadena


def test_una_llave_de_cierre_en_la_contrasena_se_duplica():
    cadena = armar_cadena_conexion(CONFIG, "ab}c")
    assert "PWD={ab}}c}" in cadena


def test_sin_contrasena_configurada_da_un_error_claro(monkeypatch):
    monkeypatch.setattr("carpinteria.datos.conexion.obtener_contrasena", lambda usuario: None)
    with pytest.raises(ErrorConexion, match="no está configurada"):
        obtener_conexion(CONFIG)
