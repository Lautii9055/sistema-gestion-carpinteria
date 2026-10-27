"""Pruebas de la gestión de usuarios y de la consulta de auditoría."""
from datetime import timedelta

import bcrypt
import pytest

from carpinteria.negocio.auditoria import ServicioAuditoria
from carpinteria.negocio.autenticacion import (ContrasenaNoValida, ServicioAutenticacion,
                                               generar_hash)
from carpinteria.negocio.entidades import Sesion, Usuario
from carpinteria.negocio.usuarios import (ErrorUsuarios, ServicioUsuarios,
                                          generar_contrasena_provisoria)

from fakes import AHORA, AuditoriaEnMemoria, ParametrosEnMemoria, Reloj, UsuariosEnMemoria


def _usuario(id_, nombre, completo, clave="Correcta.2026", activo=True):
    return Usuario(id_, nombre, completo, generar_hash(clave), False, activo, 0, None, None)


@pytest.fixture
def entorno():
    usuarios = UsuariosEnMemoria(
        _usuario(1, "lautaro", "Lautaro Zanino"),
        _usuario(2, "ricardo", "Ricardo Zanino"),
    )
    auditoria = AuditoriaEnMemoria()
    servicio = ServicioUsuarios(usuarios, auditoria, equipo="PC-PRUEBA")
    sesion = Sesion(usuarios.por_id[1], None, 0, False)
    return servicio, usuarios, auditoria, sesion


def test_la_contrasena_provisoria_es_aleatoria_y_fuerte():
    claves = {generar_contrasena_provisoria() for _ in range(50)}
    assert len(claves) == 50  # no se repiten
    for clave in claves:
        assert len(clave) == 12
        assert any(c.isupper() for c in clave) and any(c.islower() for c in clave)
        assert any(c.isdigit() for c in clave)
        assert not set(clave) & set("0O1lI")  # sin caracteres confusos


def test_alta_crea_el_usuario_con_contrasena_provisoria(entorno):
    servicio, usuarios, auditoria, sesion = entorno
    provisoria = servicio.crear(sesion, "  Marta ", "  Marta   Gómez ")
    nuevo = usuarios.buscar_por_nombre("marta")
    assert nuevo.nombre_completo == "Marta Gómez"
    assert nuevo.debe_cambiar_contrasena
    assert bcrypt.checkpw(provisoria.encode(), nuevo.hash_contrasena.encode())
    _, codigo, datos = auditoria.eventos[-1]
    assert codigo == "ALTA_USUARIO" and datos["id_usuario"] == 1 and datos["id_entidad"] == nuevo.id


@pytest.mark.parametrize("nombre", ["ab", "con espacio", "tildé", "x" * 31, "-guion"])
def test_alta_rechaza_nombres_de_usuario_invalidos(entorno, nombre):
    servicio, _, _, sesion = entorno
    with pytest.raises(ErrorUsuarios):
        servicio.crear(sesion, nombre, "Alguien")


def test_alta_rechaza_un_usuario_repetido(entorno):
    servicio, _, _, sesion = entorno
    with pytest.raises(ErrorUsuarios, match="Ya existe"):
        servicio.crear(sesion, "RICARDO", "Otro Ricardo")


def test_blanquear_asigna_provisoria_y_desbloquea(entorno):
    servicio, usuarios, auditoria, sesion = entorno
    usuarios.registrar_fallo(2, 0, AHORA + timedelta(minutes=10))
    provisoria = servicio.blanquear_contrasena(sesion, 2)
    ricardo = usuarios.por_id[2]
    assert ricardo.debe_cambiar_contrasena and ricardo.bloqueado_hasta is None
    assert bcrypt.checkpw(provisoria.encode(), ricardo.hash_contrasena.encode())
    assert auditoria.codigos()[-1] == "BLANQUEO_CONTRASENA"


def test_no_se_puede_blanquear_la_propia_contrasena(entorno):
    servicio, _, _, sesion = entorno
    with pytest.raises(ErrorUsuarios, match="Mi contraseña"):
        servicio.blanquear_contrasena(sesion, 1)


def test_baja_y_reactivacion_quedan_auditadas(entorno):
    servicio, usuarios, auditoria, sesion = entorno
    servicio.dar_de_baja(sesion, 2)
    assert not usuarios.por_id[2].es_activo
    servicio.reactivar(sesion, 2)
    assert usuarios.por_id[2].es_activo
    assert auditoria.codigos()[-2:] == ["BAJA_USUARIO", "REACTIVACION_USUARIO"]


def test_nadie_puede_darse_de_baja_a_si_mismo(entorno):
    servicio, _, _, sesion = entorno
    with pytest.raises(ErrorUsuarios, match="vos mismo"):
        servicio.dar_de_baja(sesion, 1)


def test_siempre_queda_al_menos_un_usuario_activo(entorno):
    servicio, usuarios, _, _ = entorno
    usuarios.cambiar_estado(1, False)  # solo queda Ricardo activo
    sesion_de_otro = Sesion(_usuario(9, "tecnico", "Técnico"), None, 0, False)
    with pytest.raises(ErrorUsuarios, match="al menos un usuario activo"):
        servicio.dar_de_baja(sesion_de_otro, 2)


def test_el_listado_muestra_primero_los_activos(entorno):
    servicio, usuarios, _, sesion = entorno
    servicio.dar_de_baja(sesion, 2)
    servicio.crear(sesion, "ana", "Ana Pérez")
    assert [u.nombre_usuario for u in servicio.listar()] == ["ana", "lautaro", "ricardo"]


def test_cambiar_la_propia_contrasena_exige_la_actual():
    usuarios = UsuariosEnMemoria(_usuario(1, "lautaro", "Lautaro Zanino"))
    servicio = ServicioAutenticacion(usuarios, AuditoriaEnMemoria(), ParametrosEnMemoria(),
                                     reloj=Reloj(), equipo="PC")
    with pytest.raises(ContrasenaNoValida, match="actual no es correcta"):
        servicio.cambiar_contrasena_propia(1, "equivocada", "Nueva.Clave.26", "Nueva.Clave.26")
    servicio.cambiar_contrasena_propia(1, "Correcta.2026", "Nueva.Clave.26", "Nueva.Clave.26")
    assert servicio.ingresar("lautaro", "Nueva.Clave.26")


def test_la_auditoria_filtra_por_periodo_y_por_criticos():
    reloj = Reloj()
    auditoria = AuditoriaEnMemoria(reloj)
    reloj.ahora = AHORA - timedelta(days=10)
    auditoria.registrar("LOGIN_OK", id_usuario=1)
    reloj.ahora = AHORA
    auditoria.registrar("LOGIN_FALLIDO", id_usuario=1)
    auditoria.registrar("USUARIO_BLOQUEADO", id_usuario=1)
    consulta = ServicioAuditoria(auditoria, reloj=reloj)
    assert len(consulta.consultar("Todo")) == 3
    assert len(consulta.consultar("Últimos 7 días")) == 2
    assert [e.codigo for e in consulta.consultar("Hoy", solo_criticos=True)] == ["USUARIO_BLOQUEADO"]
    assert consulta.consultar("Hoy")[0].codigo == "USUARIO_BLOQUEADO"  # lo más reciente primero
