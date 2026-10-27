"""Pruebas de clientes y obras (RF-04 a RF-07) y de la búsqueda segura."""
import pytest

from carpinteria.datos.repositorios_clientes import escapar_like
from carpinteria.negocio.clientes import (LIMITE_RESULTADOS, ErrorClientes, ServicioClientes,
                                          terminos_de_busqueda)
from carpinteria.negocio.entidades import Cliente, Obra, TrabajoResumen

from fakes import AHORA, ClientesEnMemoria, ObrasEnMemoria


@pytest.fixture
def entorno():
    obras = ObrasEnMemoria()
    clientes = ClientesEnMemoria(obras)
    return ServicioClientes(clientes, obras), clientes, obras


def _cliente(nombre="María", apellido="González", telefono="11 4567-8901", **otros):
    return Cliente(None, nombre, apellido, telefono, **otros)


def _obra(direccion="Av. Cazón 1234", localidad="Tigre", **otros):
    return Obra(None, None, direccion, localidad, **otros)


# ---------- alta y validaciones ----------
def test_crea_cliente_con_primera_obra_y_limpia_los_datos(entorno):
    servicio, clientes, obras = entorno
    id_ = servicio.crear(_cliente(nombre="  María  ", email="  Maria@Gmail.com "), _obra())
    guardado = clientes.por_id[id_]
    assert guardado.nombre == "María"
    assert guardado.email == "maria@gmail.com"
    assert [o.direccion for o in obras.listar_por_cliente(id_)] == ["Av. Cazón 1234"]


def test_crea_cliente_sin_obra(entorno):
    servicio, _, obras = entorno
    id_ = servicio.crear(_cliente())
    assert obras.listar_por_cliente(id_) == []


@pytest.mark.parametrize("cambios, mensaje", [
    ({"nombre": " "}, "nombre"),
    ({"apellido": ""}, "apellido"),
    ({"telefono": "abc123"}, "teléfono"),
    ({"telefono": "12-34"}, "teléfono"),
    ({"email": "maria@"}, "email"),
    ({"nombre": "x" * 51}, "50"),
    ({"observaciones": "x" * 501}, "500"),
])
def test_rechaza_datos_invalidos(entorno, cambios, mensaje):
    servicio, _, _ = entorno
    with pytest.raises(ErrorClientes, match=mensaje):
        servicio.crear(_cliente(**cambios))


def test_obra_invalida_no_guarda_el_cliente(entorno):
    servicio, clientes, _ = entorno
    with pytest.raises(ErrorClientes, match="localidad"):
        servicio.crear(_cliente(), _obra(localidad=""))
    assert clientes.por_id == {}


def test_telefono_repetido_aunque_este_escrito_distinto(entorno):
    servicio, _, _ = entorno
    servicio.crear(_cliente())
    with pytest.raises(ErrorClientes, match="María González"):
        servicio.crear(_cliente(nombre="Otra", telefono="(11) 4567 8901"))


def test_modificar_conservando_su_propio_telefono(entorno):
    servicio, clientes, _ = entorno
    id_ = servicio.crear(_cliente())
    servicio.actualizar(Cliente(id_, "María José", "González", "11 4567-8901"))
    assert clientes.por_id[id_].nombre == "María José"


# ---------- baja lógica ----------
def test_baja_y_reactivacion(entorno):
    servicio, _, _ = entorno
    id_ = servicio.crear(_cliente())
    servicio.dar_de_baja(id_)
    assert servicio.buscar("") == []
    assert len(servicio.buscar("", incluir_inactivos=True)) == 1
    servicio.reactivar(id_)
    assert len(servicio.buscar("")) == 1


# ---------- búsqueda ----------
def test_busqueda_por_fragmentos_sin_tildes_ni_mayusculas(entorno):
    servicio, _, _ = entorno
    servicio.crear(_cliente(), _obra())
    servicio.crear(_cliente("Jorge", "Pérez", "11 2222-3333"), _obra("Libertad 50", "San Fernando"))
    assert [r.cliente.apellido for r in servicio.buscar("gonza")] == ["González"]
    assert [r.cliente.apellido for r in servicio.buscar("PEREZ")] == ["Pérez"]
    assert [r.cliente.apellido for r in servicio.buscar("cazon")] == ["González"]       # por la obra
    assert [r.cliente.apellido for r in servicio.buscar("maria tigre")] == ["González"]  # dos palabras
    assert servicio.buscar("maria fernando") == []                                     # todas deben coincidir
    assert [r.cliente.apellido for r in servicio.buscar("45678")] == ["González"]       # por teléfono


def test_terminos_de_busqueda_se_limitan(entorno):
    assert terminos_de_busqueda("  a   b  ") == ["a", "b"]
    assert terminos_de_busqueda("") == []
    assert len(terminos_de_busqueda("a b c d e f g")) == 5
    servicio, clientes, _ = entorno
    servicio.buscar("x")
    assert clientes.ultimo_limite == LIMITE_RESULTADOS


@pytest.mark.parametrize("texto, patron", [
    ("gonz", "%gonz%"),
    ("100%", "%100\\%%"),
    ("a_b", "%a\\_b%"),
    ("[x]", "%\\[x]%"),
    ("c:\\", "%c:\\\\%"),
])
def test_escapar_like_trata_los_comodines_como_texto(texto, patron):
    assert escapar_like(texto) == patron


# ---------- obras y ficha ----------
def test_no_permite_la_misma_obra_dos_veces(entorno):
    servicio, _, _ = entorno
    id_ = servicio.crear(_cliente(), _obra())
    with pytest.raises(ErrorClientes, match="ya tiene una obra"):
        servicio.agregar_obra(Obra(None, id_, "av. cazon 1234", "TIGRE"))
    otra = servicio.agregar_obra(Obra(None, id_, "Av. Cazón 1234", "Nordelta", alias="Casa nueva"))
    assert otra


def test_editar_obra_sin_chocar_consigo_misma(entorno):
    servicio, _, obras = entorno
    id_ = servicio.crear(_cliente(), _obra())
    obra = obras.listar_por_cliente(id_)[0]
    servicio.actualizar_obra(Obra(obra.id, id_, obra.direccion, obra.localidad, alias="Casa"))
    assert obras.por_id[obra.id].titulo == "Casa"


def test_ficha_con_historial_de_trabajos(entorno):
    servicio, _, obras = entorno
    id_ = servicio.crear(_cliente(), _obra())
    obra = obras.listar_por_cliente(id_)[0]
    obras.trabajos[obra.id] = [TrabajoResumen(7, "Bajo mesada", "Entregado", AHORA)]
    ficha = servicio.ficha(id_)
    assert ficha.cliente.nombre_completo == "María González"
    assert ficha.obras[0].trabajos[0].descripcion == "Bajo mesada"


def test_ficha_de_cliente_inexistente(entorno):
    servicio, _, _ = entorno
    with pytest.raises(ErrorClientes, match="no existe"):
        servicio.ficha(99)
