"""Pruebas del servicio de autenticación con repositorios en memoria (sin base)."""
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from carpinteria.negocio.autenticacion import (ContrasenaNoValida, CredencialesInvalidas,
                                               ServicioAutenticacion, UsuarioBloqueado,
                                               generar_hash)
from carpinteria.negocio.entidades import Usuario

AHORA = datetime(2026, 10, 26, 18, 0)


class UsuariosEnMemoria:
    def __init__(self, *usuarios: Usuario) -> None:
        self.por_id = {u.id: u for u in usuarios}

    def buscar_por_nombre(self, nombre):
        return next((u for u in self.por_id.values() if u.nombre_usuario.casefold() == nombre.casefold()), None)

    def buscar_por_id(self, id_usuario):
        return self.por_id.get(id_usuario)

    def registrar_fallo(self, id_usuario, intentos, bloqueado_hasta):
        u = self.por_id[id_usuario]
        self.por_id[id_usuario] = replace(u, intentos_fallidos=intentos, bloqueado_hasta=bloqueado_hasta)

    def registrar_ingreso_exitoso(self, id_usuario, fecha):
        u = self.por_id[id_usuario]
        self.por_id[id_usuario] = replace(u, intentos_fallidos=0, bloqueado_hasta=None, ultimo_ingreso=fecha)

    def cambiar_contrasena(self, id_usuario, hash_contrasena, fecha):
        u = self.por_id[id_usuario]
        self.por_id[id_usuario] = replace(u, hash_contrasena=hash_contrasena, debe_cambiar_contrasena=False)


class AuditoriaEnMemoria:
    def __init__(self, reloj) -> None:
        self.eventos = []
        self._reloj = reloj

    def registrar(self, codigo_evento, **datos):
        self.eventos.append((self._reloj(), codigo_evento, datos))

    def contar_ingresos_fallidos(self, id_usuario, desde):
        return sum(1 for fecha, codigo, d in self.eventos
                   if codigo == "LOGIN_FALLIDO" and d.get("id_usuario") == id_usuario
                   and (desde is None or fecha > desde))

    def codigos(self):
        return [codigo for _, codigo, _ in self.eventos]


class ParametrosEnMemoria:
    valores = {"max_intentos_login": Decimal(5), "minutos_bloqueo": Decimal(15),
               "largo_minimo_contrasena": Decimal(10)}

    def obtener(self, clave):
        return self.valores.get(clave)


class Reloj:
    def __init__(self) -> None:
        self.ahora = AHORA

    def __call__(self):
        return self.ahora


HASH_LAUTARO = generar_hash("Correcta.2026")


@pytest.fixture
def entorno():
    reloj = Reloj()
    usuarios = UsuariosEnMemoria(Usuario(
        id=1, nombre_usuario="lautaro", nombre_completo="Lautaro Zanino",
        hash_contrasena=HASH_LAUTARO, debe_cambiar_contrasena=False, es_activo=True,
        intentos_fallidos=0, bloqueado_hasta=None, ultimo_ingreso=AHORA - timedelta(days=3),
    ))
    auditoria = AuditoriaEnMemoria(reloj)
    servicio = ServicioAutenticacion(usuarios, auditoria, ParametrosEnMemoria(), reloj=reloj, equipo="PC-PRUEBA")
    return servicio, usuarios, auditoria, reloj


def test_ingreso_correcto_registra_el_evento_y_actualiza_el_ultimo_ingreso(entorno):
    servicio, usuarios, auditoria, _ = entorno
    sesion = servicio.ingresar("lautaro", "Correcta.2026")
    assert sesion.usuario.nombre_completo == "Lautaro Zanino"
    assert sesion.ultimo_ingreso_anterior == AHORA - timedelta(days=3)
    assert usuarios.por_id[1].ultimo_ingreso == AHORA
    assert auditoria.codigos() == ["LOGIN_OK"]


def test_el_usuario_no_distingue_mayusculas_ni_espacios(entorno):
    servicio, *_ = entorno
    assert servicio.ingresar("  LAUTARO ", "Correcta.2026").usuario.id == 1


def test_contrasena_incorrecta_da_un_mensaje_generico_y_suma_un_intento(entorno):
    servicio, usuarios, auditoria, _ = entorno
    with pytest.raises(CredencialesInvalidas, match="Usuario o contraseña incorrectos"):
        servicio.ingresar("lautaro", "otra")
    assert usuarios.por_id[1].intentos_fallidos == 1
    assert auditoria.codigos() == ["LOGIN_FALLIDO"]


def test_usuario_inexistente_da_el_mismo_mensaje_y_queda_auditado(entorno):
    servicio, _, auditoria, _ = entorno
    with pytest.raises(CredencialesInvalidas, match="Usuario o contraseña incorrectos"):
        servicio.ingresar("intruso", "lo-que-sea")
    _, codigo, datos = auditoria.eventos[0]
    assert codigo == "LOGIN_FALLIDO" and datos["usuario_ingresado"] == "intruso"


def test_cinco_fallos_seguidos_bloquean_al_usuario(entorno):
    servicio, usuarios, auditoria, _ = entorno
    for _ in range(4):
        with pytest.raises(CredencialesInvalidas):
            servicio.ingresar("lautaro", "mal")
    with pytest.raises(UsuarioBloqueado) as error:
        servicio.ingresar("lautaro", "mal")
    assert error.value.minutos == 15
    assert usuarios.por_id[1].bloqueado_hasta == AHORA + timedelta(minutes=15)
    assert "USUARIO_BLOQUEADO" in auditoria.codigos()


def test_durante_el_bloqueo_ni_la_contrasena_correcta_permite_entrar(entorno):
    servicio, _, _, reloj = entorno
    for _ in range(5):
        with pytest.raises((CredencialesInvalidas, UsuarioBloqueado)):
            servicio.ingresar("lautaro", "mal")
    reloj.ahora = AHORA + timedelta(minutes=10)
    with pytest.raises(UsuarioBloqueado) as error:
        servicio.ingresar("lautaro", "Correcta.2026")
    assert error.value.minutos == 5


def test_al_vencer_el_bloqueo_se_puede_entrar_y_se_informan_los_fallidos(entorno):
    servicio, _, _, reloj = entorno
    for _ in range(5):
        with pytest.raises((CredencialesInvalidas, UsuarioBloqueado)):
            servicio.ingresar("lautaro", "mal")
    reloj.ahora = AHORA + timedelta(minutes=16)
    sesion = servicio.ingresar("lautaro", "Correcta.2026")
    assert sesion.intentos_fallidos_desde_entonces == 5


def test_usuario_dado_de_baja_no_puede_entrar(entorno):
    servicio, usuarios, _, _ = entorno
    usuarios.por_id[1] = replace(usuarios.por_id[1], es_activo=False)
    with pytest.raises(CredencialesInvalidas):
        servicio.ingresar("lautaro", "Correcta.2026")


def test_la_politica_rechaza_contrasenas_debiles(entorno):
    servicio, usuarios, _, _ = entorno
    usuario = usuarios.por_id[1]
    assert servicio.validar_contrasena_nueva(usuario, "corta", "corta")
    assert servicio.validar_contrasena_nueva(usuario, "LAUTARO", "LAUTARO")
    assert servicio.validar_contrasena_nueva(usuario, "Diferente.2026", "Diferente.2027")
    assert servicio.validar_contrasena_nueva(usuario, "Correcta.2026", "Correcta.2026")  # igual a la actual
    assert servicio.validar_contrasena_nueva(usuario, "Taller.Zanino.26", "Taller.Zanino.26") == []


def test_cambiar_contrasena_guarda_un_hash_nuevo_y_audita(entorno):
    servicio, usuarios, auditoria, _ = entorno
    servicio.cambiar_contrasena(1, "Taller.Zanino.26", "Taller.Zanino.26")
    assert usuarios.por_id[1].hash_contrasena != HASH_LAUTARO
    assert "Taller.Zanino.26" not in usuarios.por_id[1].hash_contrasena
    assert servicio.ingresar("lautaro", "Taller.Zanino.26")
    assert "CAMBIO_CONTRASENA" in auditoria.codigos()


def test_cambiar_contrasena_invalida_no_modifica_nada(entorno):
    servicio, usuarios, _, _ = entorno
    with pytest.raises(ContrasenaNoValida):
        servicio.cambiar_contrasena(1, "corta", "corta")
    assert usuarios.por_id[1].hash_contrasena == HASH_LAUTARO


def test_el_hash_del_usuario_inicial_corresponde_a_la_contrasena_provisoria():
    # Hash cargado por database/03_datos_iniciales.sql para el usuario admin.
    hash_admin = "$2b$12$x5sQjw8cM3/NzwmRyNf0hOutyGWaR9aO8j7INOoonCo5MlV9AQ3D2"
    import bcrypt
    assert bcrypt.checkpw(b"Cambiar.123", hash_admin.encode())
