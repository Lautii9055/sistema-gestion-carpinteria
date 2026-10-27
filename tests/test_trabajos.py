"""Pruebas de trabajos: estados, montos, fechas y auditoría (RF-12, RF-25 a RF-28)."""
from datetime import date, datetime, time
from decimal import Decimal as D

import pytest

from carpinteria.negocio.clientes import ServicioClientes
from carpinteria.negocio.entidades import Cliente, Obra, Sesion, Trabajo, Usuario
from carpinteria.negocio.trabajos import (ErrorTrabajos, ServicioTrabajos, formato_pesos, leer_fecha,
                                          leer_monto)

from fakes import (AuditoriaEnMemoria, ClientesEnMemoria, ObrasEnMemoria, ParametrosEnMemoria,
                   TrabajosEnMemoria)

HOY = date(2026, 11, 20)
PRESUPUESTO = date(2026, 10, 26)   # para probar fechas pasadas: trabajo anotado tarde


@pytest.fixture
def entorno():
    obras = ObrasEnMemoria()
    clientes = ClientesEnMemoria(obras)
    trabajos = TrabajosEnMemoria(clientes, obras, reloj=lambda: datetime.combine(HOY, time(9)))
    auditoria = AuditoriaEnMemoria()
    servicio = ServicioTrabajos(trabajos, clientes, obras, auditoria, ParametrosEnMemoria(),
                                hoy=lambda: HOY, equipo="PC-PRUEBA")
    id_cliente = ServicioClientes(clientes, obras).crear(
        Cliente(None, "Martín", "Ferreyra", "11 5555-0142"),
        Obra(None, None, "Barrio Los Lagos", "Nordelta"))
    id_obra = obras.listar_por_cliente(id_cliente)[0].id
    sesion = Sesion(Usuario(1, "lautaro", "Lautaro Zanino", "x", False, True, 0, None, None), None, 0, False)
    return servicio, trabajos, clientes, auditoria, sesion, id_obra


def _estado(servicio, nombre):
    return servicio.estado_por_nombre(nombre).id


# ---------- montos y fechas escritos a mano ----------
@pytest.mark.parametrize("texto, esperado", [
    ("2.800.000", D("2800000.00")), ("2800000", D("2800000.00")), ("$ 1.250,50", D("1250.50")),
    ("900.5", D("900.50")), ("", None), ("  ", None),
])
def test_leer_monto(texto, esperado):
    assert leer_monto(texto) == esperado


@pytest.mark.parametrize("texto", ["abc", "-5", "1,234", "1.2.3", "NaN", "Infinity", "99999999999"])
def test_leer_monto_rechaza(texto):
    with pytest.raises(ErrorTrabajos):
        leer_monto(texto)


def test_formato_pesos():
    assert formato_pesos(D("2800000")) == "$ 2.800.000"
    assert formato_pesos(D("1250.5")) == "$ 1.250,50"
    assert formato_pesos(None) == "—"


@pytest.mark.parametrize("texto, esperado", [
    ("05/11/2026", date(2026, 11, 5)), ("5-11-26", date(2026, 11, 5)), ("", None)])
def test_leer_fecha(texto, esperado):
    assert leer_fecha(texto) == esperado


@pytest.mark.parametrize("texto", ["31/02/2026", "2026-11-05", "mañana"])
def test_leer_fecha_rechaza(texto):
    with pytest.raises(ErrorTrabajos, match="dd/mm/aaaa"):
        leer_fecha(texto)


# ---------- alta ----------
def test_alta_nace_presupuestado_y_audita_el_monto(entorno):
    servicio, trabajos, _, auditoria, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "  Cocina   completa ", D(2800000), D(1680000))
    detalle = servicio.detalle(id_)
    assert detalle.estado.nombre == "Presupuestado"
    assert detalle.trabajo.descripcion == "Cocina completa"
    assert detalle.trabajo.saldo == D(1120000)
    assert auditoria.codigos() == ["CAMBIO_MONTO"]


def test_alta_sin_montos_no_audita(entorno):
    servicio, _, _, auditoria, sesion, id_obra = entorno
    servicio.crear(sesion, id_obra, "Placard")
    assert auditoria.codigos() == []


def test_no_se_cargan_trabajos_a_un_cliente_dado_de_baja(entorno):
    servicio, _, clientes, _, sesion, id_obra = entorno
    clientes.cambiar_estado(1, False)
    with pytest.raises(ErrorTrabajos, match="dado de baja"):
        servicio.crear(sesion, id_obra, "Placard")


@pytest.mark.parametrize("total, sena, mensaje", [
    (None, D(10), "monto total"), (D(100), D(200), "mayor"),
])
def test_validacion_de_montos(entorno, total, sena, mensaje):
    servicio, _, _, _, sesion, id_obra = entorno
    with pytest.raises(ErrorTrabajos, match=mensaje):
        servicio.crear(sesion, id_obra, "Placard", total, sena)


def test_descripcion_obligatoria(entorno):
    servicio, _, _, _, sesion, id_obra = entorno
    with pytest.raises(ErrorTrabajos, match="descripción"):
        servicio.crear(sesion, id_obra, "   ")


def test_sena_sugerida_es_el_60_por_ciento_redondeado(entorno):
    servicio = entorno[0]
    assert servicio.sena_sugerida(D(2800000)) == D(1680000)
    assert servicio.sena_sugerida(D("1000.75")) == D(600)


# ---------- fechas coherentes (RF-26.2) ----------
@pytest.mark.parametrize("fechas, mensaje", [
    ({"fecha_comienzo": date(2026, 11, 5), "fecha_finalizacion": date(2026, 11, 1)}, "finalización"),
    ({"fecha_finalizacion": date(2026, 11, 5), "fecha_entrega": date(2026, 11, 4)}, "entrega"),
    ({"fecha_cobro_sena": date(2026, 11, 5), "fecha_cobro_saldo": date(2026, 11, 1)}, "saldo"),
    ({"fecha_cobro_sena": date(2026, 11, 21)}, "futura"),
    ({"fecha_cobro_sena": date(2026, 10, 23)}, "anterior al presupuesto"),
    ({"fecha_entrega": date(2026, 10, 1)}, "anterior al presupuesto"),
    ({"fecha_cobro_sena": date(2026, 11, 5), "fecha_comienzo": date(2026, 11, 4)}, "confirmación"),
])
def test_fechas_incoherentes(entorno, fechas, mensaje):
    servicio, _, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600), fecha_presupuesto=PRESUPUESTO)
    with pytest.raises(ErrorTrabajos, match=mensaje):
        servicio.actualizar_pagos(sesion, id_, D(1000), D(600), fechas)


def test_entrega_futura_si_se_permite(entorno):
    servicio, trabajos, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina")
    servicio.actualizar_pagos(sesion, id_, None, None, {"fecha_entrega": date(2026, 12, 1)})
    assert trabajos.por_id[id_].fecha_entrega == date(2026, 12, 1)


def test_cambio_de_montos_queda_auditado_con_el_detalle(entorno):
    servicio, _, _, auditoria, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina")
    servicio.actualizar_pagos(sesion, id_, D(2800000), D(1680000), {})
    _, codigo, datos = auditoria.eventos[-1]
    assert codigo == "CAMBIO_MONTO"
    assert datos["detalle"] == "Total: — → $ 2.800.000; Seña: — → $ 1.680.000"
    assert datos["entidad"] == "Trabajo" and datos["id_entidad"] == id_
    servicio.actualizar_pagos(sesion, id_, D(2800000), D(1680000), {"fecha_comienzo": HOY})
    assert len(auditoria.eventos) == 1  # sin cambio de montos, no se audita de nuevo


# ---------- estados (RF-25, RF-26.3) ----------
def test_avance_de_estados_y_fecha_sugerida(entorno):
    servicio, trabajos, _, auditoria, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600))
    estado = servicio.detalle(id_).estado
    recorrido = []
    while (siguiente := servicio.estado_siguiente(estado)) is not None:
        servicio.cambiar_estado(sesion, id_, siguiente.id, HOY)
        estado = servicio.detalle(id_).estado
        recorrido.append(estado.nombre)
    assert recorrido == ["Confirmado", "En producción", "Terminado", "Instalado", "Cobrado"]
    t = trabajos.por_id[id_]
    assert t.fecha_cobro_sena == t.fecha_comienzo == t.fecha_entrega == t.fecha_cobro_saldo == HOY
    assert t.pendiente_de_cobro == 0
    assert auditoria.codigos().count("CAMBIO_ESTADO_TRABAJO") == 5
    assert auditoria.eventos[-1][2]["detalle"] == "Instalado → Cobrado"


def test_cambiar_estado_sin_fecha_no_la_borra(entorno):
    servicio, trabajos, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", fecha_presupuesto=PRESUPUESTO)
    servicio.actualizar_pagos(sesion, id_, None, None, {"fecha_comienzo": date(2026, 11, 1)})
    servicio.cambiar_estado(sesion, id_, _estado(servicio, "Confirmado"), None)
    servicio.cambiar_estado(sesion, id_, _estado(servicio, "En producción"), None)
    assert trabajos.por_id[id_].fecha_comienzo == date(2026, 11, 1)


def test_no_se_saltean_estados(entorno):
    servicio, _, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600))
    servicio.registrar_cobro(sesion, id_, "fecha_cobro_sena", HOY)
    with pytest.raises(ErrorTrabajos, match="de a uno"):
        servicio.cambiar_estado(sesion, id_, _estado(servicio, "Cobrado"), HOY)


def test_volver_un_paso_borra_la_fecha_de_ese_paso(entorno):
    servicio, trabajos, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", fecha_presupuesto=PRESUPUESTO)
    for nombre, fecha in (("Confirmado", None), ("En producción", date(2026, 11, 2)),
                          ("Terminado", date(2026, 11, 10))):
        servicio.cambiar_estado(sesion, id_, _estado(servicio, nombre), fecha)
    servicio.cambiar_estado(sesion, id_, _estado(servicio, "En producción"))
    t = trabajos.por_id[id_]
    assert t.fecha_finalizacion is None and t.fecha_comienzo == date(2026, 11, 2)
    assert servicio.detalle(id_).estado.nombre == "En producción"


def test_no_vuelve_a_presupuestado_con_la_sena_cobrada(entorno):
    servicio, _, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600))
    servicio.registrar_cobro(sesion, id_, "fecha_cobro_sena", HOY)
    with pytest.raises(ErrorTrabajos, match="seña figura cobrada"):
        servicio.cambiar_estado(sesion, id_, _estado(servicio, "Presupuestado"))


def test_cobrar_la_sena_confirma_el_trabajo(entorno):
    servicio, trabajos, _, auditoria, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600), fecha_presupuesto=PRESUPUESTO)
    assert servicio.registrar_cobro(sesion, id_, "fecha_cobro_sena", date(2026, 10, 27)) is True
    assert servicio.detalle(id_).estado.nombre == "Confirmado"
    assert trabajos.por_id[id_].fecha_cobro_sena == date(2026, 10, 27)
    assert auditoria.eventos[-1][2]["detalle"] == "Presupuestado → Confirmado"


def test_pago_total_anticipado_no_cambia_el_estado(entorno):
    servicio, trabajos, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600), fecha_presupuesto=PRESUPUESTO)
    with pytest.raises(ErrorTrabajos, match="Primero confirmá"):
        servicio.registrar_cobro(sesion, id_, "fecha_cobro_saldo", date(2026, 10, 27))
    servicio.registrar_cobro(sesion, id_, "fecha_cobro_sena", date(2026, 10, 27))
    assert servicio.registrar_cobro(sesion, id_, "fecha_cobro_saldo", date(2026, 10, 27)) is False
    assert servicio.detalle(id_).estado.nombre == "Confirmado"
    assert trabajos.por_id[id_].pendiente_de_cobro == 0
    # Sigue su curso; al llegar a cobrado conserva la fecha del pago anticipado.
    for nombre in ("En producción", "Terminado", "Instalado", "Cobrado"):
        servicio.cambiar_estado(sesion, id_, _estado(servicio, nombre), None)
    assert trabajos.por_id[id_].fecha_cobro_saldo == date(2026, 10, 27)


def test_cobrado_exige_el_cobro_del_saldo(entorno):
    servicio, _, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600))
    servicio.registrar_cobro(sesion, id_, "fecha_cobro_sena", HOY)
    for nombre in ("En producción", "Terminado", "Instalado"):
        servicio.cambiar_estado(sesion, id_, _estado(servicio, nombre), HOY)
    with pytest.raises(ErrorTrabajos, match="saldo"):
        servicio.cambiar_estado(sesion, id_, _estado(servicio, "Cobrado"), None)


def test_estado_alcanzado_no_tiene_fecha_futura(entorno):
    servicio, _, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina")
    servicio.cambiar_estado(sesion, id_, _estado(servicio, "Confirmado"))
    # Prevista (todavía no pasó): se permite.
    servicio.actualizar_pagos(sesion, id_, None, None, {"fecha_comienzo": date(2026, 12, 1)})
    with pytest.raises(ErrorTrabajos, match="no puede ser futura"):
        servicio.cambiar_estado(sesion, id_, _estado(servicio, "En producción"), date(2026, 12, 1))


def test_cancelar_y_retomar(entorno):
    servicio, _, _, _, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600))
    servicio.registrar_cobro(sesion, id_, "fecha_cobro_sena", HOY)
    servicio.cambiar_estado(sesion, id_, _estado(servicio, "En producción"), HOY)
    servicio.cambiar_estado(sesion, id_, _estado(servicio, "Cancelado"))
    detalle = servicio.detalle(id_)
    assert servicio.alcanzados(detalle.estado) == ()
    retomar = servicio.estado_para_retomar(detalle.trabajo)
    assert retomar.nombre == "En producción"
    servicio.cambiar_estado(sesion, id_, retomar.id)
    assert servicio.detalle(id_).estado.nombre == "En producción"


def test_cobrado_no_se_cancela(entorno):
    servicio = entorno[0]
    assert not servicio.puede_cancelarse(servicio.estado_por_nombre("Cobrado"))
    assert servicio.puede_cancelarse(servicio.estado_por_nombre("Instalado"))


def test_cancelado_y_cobrado_no_tienen_siguiente(entorno):
    servicio = entorno[0]
    assert servicio.estado_siguiente(servicio.estado_por_nombre("Cancelado")) is None
    assert servicio.estado_siguiente(servicio.estado_por_nombre("Cobrado")) is None
    assert [e.nombre for e in servicio.recorrido()][-1] == "Cobrado"


# ---------- eliminación ----------
def test_solo_se_eliminan_presupuestados_o_cancelados(entorno):
    servicio, trabajos, _, auditoria, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina")
    servicio.cambiar_estado(sesion, id_, _estado(servicio, "Confirmado"))
    with pytest.raises(ErrorTrabajos, match="cancelalo"):
        servicio.eliminar(sesion, id_)
    servicio.cambiar_estado(sesion, id_, _estado(servicio, "Cancelado"))
    servicio.eliminar(sesion, id_)
    assert id_ not in trabajos.por_id
    assert auditoria.codigos()[-1] == "ELIMINACION_TRABAJO"
    assert "Martín Ferreyra" in auditoria.eventos[-1][2]["detalle"]


# ---------- búsqueda y cobros pendientes (RF-06, RF-28) ----------
def test_busqueda_y_filtros(entorno):
    servicio, trabajos, _, _, sesion, id_obra = entorno
    cocina = servicio.crear(sesion, id_obra, "Cocina completa", D(1000), D(600))
    placard = servicio.crear(sesion, id_obra, "Placard dormitorio")
    servicio.cambiar_estado(sesion, cocina, _estado(servicio, "Confirmado"), HOY)
    assert [d.trabajo.id for d in servicio.buscar("ferreyra cocina")] == [cocina]
    assert [d.trabajo.id for d in servicio.buscar(str(placard))] == [placard]
    assert sorted(d.trabajo.id for d in servicio.buscar("nordelta")) == [cocina, placard]
    assert [d.trabajo.id for d in servicio.buscar(id_estado=_estado(servicio, "Presupuestado"))] == [placard]
    # La cocina tiene la seña cobrada pero el saldo no: está por cobrar.
    assert [d.trabajo.id for d in servicio.buscar(solo_por_cobrar=True)] == [cocina]
    servicio.buscar(periodo="Últimos 30 días")
    assert trabajos.ultimos_filtros[3] == date(2026, 10, 21)


def test_pendiente_de_cobro():
    t = Trabajo(1, 1, 2, "x", D(1000), D(600), fecha_cobro_sena=HOY)
    assert (t.saldo, t.cobrado, t.pendiente_de_cobro) == (D(400), D(600), D(400))
    assert Trabajo(1, 1, 2, "x").pendiente_de_cobro == 0


# ---------- fecha de presupuesto editable (trabajos anotados tarde) ----------
def test_alta_con_fecha_de_presupuesto_pasada_queda_auditada(entorno):
    servicio, trabajos, _, auditoria, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600), fecha_presupuesto=date(2026, 10, 1))
    t = trabajos.por_id[id_]
    assert t.fecha_presupuesto == date(2026, 10, 1)
    assert t.fecha_alta.date() == HOY        # la fecha de carga no cambia
    assert auditoria.codigos() == ["CAMBIO_FECHA_PRESUPUESTO", "CAMBIO_MONTO"]
    assert auditoria.eventos[0][2]["detalle"] == "Cargado el 20/11/2026 con fecha de presupuesto 01/10/2026"
    # Ahora se puede registrar una seña cobrada antes de cargarlo en el sistema.
    servicio.registrar_cobro(sesion, id_, "fecha_cobro_sena", date(2026, 10, 5))
    assert servicio.detalle(id_).estado.nombre == "Confirmado"


def test_alta_de_hoy_no_audita_la_fecha(entorno):
    servicio, trabajos, _, auditoria, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina")
    assert trabajos.por_id[id_].fecha_presupuesto == HOY
    assert auditoria.codigos() == []


@pytest.mark.parametrize("fecha, mensaje", [(date(2026, 11, 21), "futura"), (date(2009, 12, 31), "2010")])
def test_fecha_de_presupuesto_invalida(entorno, fecha, mensaje):
    servicio, _, _, _, sesion, id_obra = entorno
    with pytest.raises(ErrorTrabajos, match=mensaje):
        servicio.crear(sesion, id_obra, "Cocina", fecha_presupuesto=fecha)


def test_corregir_la_fecha_de_presupuesto_sin_romper_las_demas(entorno):
    servicio, trabajos, _, auditoria, sesion, id_obra = entorno
    id_ = servicio.crear(sesion, id_obra, "Cocina", D(1000), D(600), fecha_presupuesto=PRESUPUESTO)
    servicio.registrar_cobro(sesion, id_, "fecha_cobro_sena", date(2026, 11, 10))
    # Adelantarla: bien. Llevarla después de la seña: no.
    servicio.actualizar_pagos(sesion, id_, D(1000), D(600), {"fecha_presupuesto": date(2026, 11, 1)})
    assert trabajos.por_id[id_].fecha_presupuesto == date(2026, 11, 1)
    assert auditoria.eventos[-1][2]["detalle"] == "Presupuesto: 26/10/2026 → 01/11/2026"
    with pytest.raises(ErrorTrabajos, match="anterior al presupuesto"):
        servicio.actualizar_pagos(sesion, id_, D(1000), D(600), {"fecha_presupuesto": date(2026, 11, 15)})
    with pytest.raises(ErrorTrabajos, match="Completá"):
        servicio.actualizar_pagos(sesion, id_, D(1000), D(600), {"fecha_presupuesto": None})
