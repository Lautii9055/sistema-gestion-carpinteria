"""Pruebas del resumen del inicio."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal as D

import pytest

from carpinteria.negocio.clientes import ServicioClientes
from carpinteria.negocio.entidades import Cliente, Obra, Sesion, Usuario
from carpinteria.negocio.inicio import ServicioInicio, texto_entregas
from carpinteria.negocio.trabajos import ServicioTrabajos

from fakes import (AuditoriaEnMemoria, ClientesEnMemoria, ObrasEnMemoria, ParametrosEnMemoria,
                   TrabajosEnMemoria)

HOY = date(2026, 11, 20)


@pytest.fixture
def taller():
    obras = ObrasEnMemoria()
    clientes = ClientesEnMemoria(obras)
    trabajos = TrabajosEnMemoria(clientes, obras, reloj=lambda: datetime.combine(HOY, time(9)))
    servicio = ServicioTrabajos(trabajos, clientes, obras, AuditoriaEnMemoria(), ParametrosEnMemoria(),
                                hoy=lambda: HOY, equipo="PC")
    id_cliente = ServicioClientes(clientes, obras).crear(Cliente(None, "Martín", "Ferreyra", "11 5555-0142"),
                                                         Obra(None, None, "Los Lagos", "Nordelta"))
    obra = obras.listar_por_cliente(id_cliente)[0].id
    sesion = Sesion(Usuario(1, "l", "Lautaro", "x", False, True, 0, None, None), None, 0, False)

    def trabajo(descripcion, hasta, total=None, sena=None, presupuesto=date(2026, 11, 1), entrega=None, **fechas):
        """Crea un trabajo y lo avanza hasta el estado indicado."""
        id_ = servicio.crear(sesion, obra, descripcion, total, sena, fecha_presupuesto=presupuesto)
        estado = servicio.detalle(id_).estado
        while estado.nombre != hasta:
            siguiente = servicio.estado_siguiente(estado)
            fecha = date(2026, 11, 2) if siguiente.nombre in ("Confirmado", "En producción") else HOY
            if siguiente.nombre == "Confirmado" and not sena:
                fecha = None
            servicio.cambiar_estado(sesion, id_, siguiente.id, fecha)
            estado = servicio.detalle(id_).estado
        if fechas:
            servicio.actualizar_pagos(sesion, id_, total, sena, fechas)
        return id_

    return servicio, ServicioInicio(trabajos, hoy=lambda: HOY), trabajo


def test_taller_vacio(taller):
    _, inicio, _ = taller
    r = inicio.resumen()
    assert (r.en_produccion, r.por_cobrar, r.presupuestos_sin_confirmar, r.en_curso, r.alertas) == \
        (0, 0, 0, [], [])
    assert r.dias_presupuesto_mas_antiguo is None


def test_resumen(taller):
    servicio, inicio, trabajo = taller
    cocina = trabajo("Cocina", "En producción", D(1000), D(600), fecha_entrega=HOY + timedelta(days=2))
    trabajo("Vestidor", "En producción", D(500), D(300))
    trabajo("Biblioteca", "Presupuestado", presupuesto=date(2026, 11, 10))
    trabajo("Placard", "Presupuestado", presupuesto=date(2026, 11, 1))
    lejos = trabajo("Vanitory", "Confirmado", D(200), D(100), fecha_entrega=HOY + timedelta(days=20))
    cobrado = trabajo("Mesa", "Cobrado", D(100), D(60))
    r = inicio.resumen()
    assert r.en_produccion == 2
    assert [d.trabajo.id for d in r.entregas_proximas] == [cocina]
    assert r.por_cobrar == D(400 + 200 + 100)       # saldos; las señas ya están cobradas
    assert r.trabajos_por_cobrar == 3
    assert (r.presupuestos_sin_confirmar, r.dias_presupuesto_mas_antiguo) == (2, 19)
    ids = [d.trabajo.id for d in r.en_curso]
    assert cobrado not in ids
    assert ids[:2] == [cocina, lejos]               # primero los que tienen entrega más cercana
    assert texto_entregas(r.entregas_proximas, HOY) == "el 22/11"


def test_alertas(taller):
    servicio, inicio, trabajo = taller
    trabajo("Cocina", "En producción", D(1000), D(600), fecha_entrega=date(2026, 11, 19))   # atrasada
    trabajo("Vestidor", "Instalado", D(500), D(300))                                    # saldo
    trabajo("Placard", "Presupuestado", presupuesto=date(2026, 10, 1))                  # sin respuesta
    trabajo("Mesa", "Confirmado")                                                        # sin monto
    titulos = [a.titulo for a in inicio.resumen().alertas]
    assert titulos[:2] == ["Entrega atrasada", "Saldo por cobrar"]    # urgentes primero
    assert set(titulos[2:]) == {"Presupuesto sin respuesta", "Sin monto"}


def test_texto_entregas():
    assert texto_entregas([], HOY) == "sin entregas pactadas"


def test_entrega_por_semana_en_el_inicio(taller):
    servicio, inicio, trabajo = taller
    # Semana del 16/11 (termina el domingo 22): todavía no está atrasada y entra en los próximos 7 días.
    a_tiempo = trabajo("Cocina", "En producción", entrega=None)
    servicio.pactar_entrega(None, a_tiempo, date(2026, 11, 18), aproximada=True)
    # Semana del 09/11 (terminó el 15): atrasada.
    tarde = trabajo("Vestidor", "En producción")
    servicio.pactar_entrega(None, tarde, date(2026, 11, 12), aproximada=True)
    r = inicio.resumen()
    assert [d.trabajo.id for d in r.entregas_proximas] == [a_tiempo]
    assert texto_entregas(r.entregas_proximas, HOY) == "sem. 16/11"
    atrasadas = [a for a in r.alertas if a.titulo == "Entrega atrasada"]
    assert [a.id_trabajo for a in atrasadas] == [tarde]
    assert "semana del 09/11" in atrasadas[0].detalle
