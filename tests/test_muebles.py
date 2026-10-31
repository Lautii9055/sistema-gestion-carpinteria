from dataclasses import replace
"""Guardar el despiece: módulos, zócalos y piezas, recálculo y filos (RF-12 a RF-19)."""
from datetime import date, datetime, time
from decimal import Decimal as D

import pytest

from carpinteria.negocio.clientes import ServicioClientes
from carpinteria.negocio.entidades import (CajonGuardado, Cantos, Cliente, ColorLaca, ColorPlaca, MarcaPlaca, ModuloGuardado,
                                          Obra, Sesion, Usuario, ZocaloGuardado)
from carpinteria.negocio.materiales import ServicioMateriales
from carpinteria.negocio.muebles import ErrorMuebles, ServicioMuebles
from carpinteria.negocio.trabajos import ServicioTrabajos

from fakes import (AuditoriaEnMemoria, CatalogoEnMemoria, ClientesEnMemoria, MaterialesEnMemoria, MueblesEnMemoria,
                   ObrasEnMemoria, ParametrosEnMemoria, TrabajosEnMemoria)

HOY = date(2026, 11, 20)
SIN_FILO, FILO_045, FILO_2 = 1, 2, 3


@pytest.fixture
def taller():
    obras = ObrasEnMemoria()
    clientes = ClientesEnMemoria(obras)
    trabajos = TrabajosEnMemoria(clientes, obras, reloj=lambda: datetime.combine(HOY, time(9)))
    servicio_trabajos = ServicioTrabajos(trabajos, clientes, obras, AuditoriaEnMemoria(), ParametrosEnMemoria(),
                                         hoy=lambda: HOY, equipo="PC")
    ServicioClientes(clientes, obras).crear(Cliente(None, "Martín", "Ferreyra", "11 5555-0142"),
                                            Obra(None, None, "Los Lagos", "Nordelta"))
    sesion = Sesion(Usuario(1, "l", "Lautaro", "x", False, True, 0, None, None), None, 0, False)
    id_trabajo = servicio_trabajos.crear(sesion, 1, "Cocina")

    materiales = MaterialesEnMemoria()
    m = ServicioMateriales(materiales)
    faplac = m.guardar_marca(MarcaPlaca(None, "Faplac"))
    blanco = m.guardar_color(ColorPlaca(None, faplac, "Blanco", None, tiene_veta=False))
    roble = m.guardar_color(ColorPlaca(None, faplac, "Roble", None, tiene_veta=True))
    placas = {"blanco18": m.guardar_placa(None, blanco, "18", "183", "260"),
              "roble18": m.guardar_placa(None, roble, "18", "183", "260"),
              "blanco55": m.guardar_placa(None, blanco, "5,5", "183", "260")}
    catalogo = CatalogoEnMemoria()
    catalogo.colores_[1] = ColorLaca(1, 2, "Gris Topo", "SW 7062")
    repo = MueblesEnMemoria()
    servicio = ServicioMuebles(repo, trabajos, materiales, catalogo, ParametrosEnMemoria())
    id_mueble = servicio.guardar_mueble(None, id_trabajo, "Bajo mesada cocina")
    return {"servicio": servicio, "repo": repo, "placas": placas, "id_mueble": id_mueble, "id_trabajo": id_trabajo,
            "trabajos": servicio_trabajos, "sesion": sesion, "materiales": m, "catalogo": catalogo}


def _modulo(t, **cambios):
    datos = dict(id=None, id_mueble=t["id_mueble"], armado="Módulo", id_placa=t["placas"]["blanco18"],
                 ancho=D(90), alto=D(60), profundidad=D(40), puertas=2, estantes=1,
                 id_placa_frentes=t["placas"]["roble18"], id_placa_fondo=t["placas"]["blanco55"],
                 luz_superior=D("0.4"), luz_inferior=D("0.4"), luz_entre_frentes=D("0.3"))
    datos.update(cambios)
    return ModuloGuardado(**datos)


def _piezas(t, id_modulo):
    return {(p.tipo, p.orden_cajon): p for p in t["repo"].piezas_de_modulo(id_modulo)}


def test_guardar_modulo_genera_piezas_con_su_material(taller):
    t = taller
    id_modulo, avisos = t["servicio"].guardar_modulo(_modulo(t))
    piezas = _piezas(t, id_modulo)
    assert avisos == []
    assert piezas[("Puerta", None)].id_material == t["placas"]["roble18"]
    assert (piezas[("Puerta", None)].medida_1, piezas[("Puerta", None)].medida_2) == (D("59.2"), D("44.5"))
    assert piezas[("Lateral", None)].id_material == t["placas"]["blanco18"]
    assert piezas[("Fondo", None)].id_material == t["placas"]["blanco55"]
    assert (piezas[("Fondo", None)].medida_1, piezas[("Fondo", None)].medida_2) == (D("59.7"), D("89.7"))
    # filos sin definir (RN-08), salvo el fondo, que nunca lleva (RN-08.3)
    assert all(p.id_tipo_filo is None for k, p in piezas.items() if k[0] != "Fondo")
    assert len(t["servicio"].piezas_sin_filo(t["id_trabajo"])) == len(piezas) - 1


def test_veta_rotada_al_cargar_se_respeta_al_recalcular(taller):
    t = taller
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(t, rotar=frozenset({"Fondo"})))
    fondo = _piezas(t, id_modulo)[("Fondo", None)]
    assert (fondo.medida_1, fondo.medida_2) == (D("89.7"), D("59.7"))
    t["servicio"].guardar_modulo(_modulo(t, id=id_modulo, ancho=D(80), rotar=frozenset({"Fondo"})))
    fondo = _piezas(t, id_modulo)[("Fondo", None)]
    assert (fondo.medida_1, fondo.medida_2) == (D("79.7"), D("59.7"))


def test_frentes_laqueados_nacen_sin_filo(taller):
    t = taller
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(t, id_color_laca=1, id_terminacion=1))
    puerta = _piezas(t, id_modulo)[("Puerta", None)]
    assert (puerta.id_color_laca, puerta.id_terminacion, puerta.id_tipo_filo) == (1, 1, SIN_FILO)
    assert _piezas(t, id_modulo)[("Lateral", None)].id_tipo_filo is None


def test_laca_sin_terminacion(taller):
    with pytest.raises(ErrorMuebles, match="terminación"):
        taller["servicio"].guardar_modulo(_modulo(taller, id_color_laca=1))


def test_cajonera_con_cajones_guarda_piezas_por_cajon(taller):
    t = taller
    caj = CajonGuardado(None, 1, t["placas"]["blanco55"], D(12), D(50))
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(
        t, armado="Cajonera con fajas de luz", alto=D(34), profundidad=D("51.8"), puertas=0, estantes=0,
        ancho=D(60), ancho_faja=D(10), id_placa_fondo=None, cajones=(caj, caj),
        luz_superior=D("0.6"), luz_inferior=D("0.6")))
    piezas = _piezas(t, id_modulo)
    assert piezas[("Piso de cajón", 1)].id_material == t["placas"]["blanco55"]
    assert (piezas[("Contrafrente de cajón", 2)].medida_1, piezas[("Contrafrente de cajón", 2)].medida_2) == \
        (D("50.1"), D(12))
    assert piezas[("Frente de cajón", 1)].id_cajon is not None and piezas[("Faja", None)].id_modulo == id_modulo


def test_recalculo_conserva_filos_y_respeta_lo_editado(taller):
    t = taller
    s = t["servicio"]
    id_modulo, _ = s.guardar_modulo(_modulo(t))
    piezas = _piezas(t, id_modulo)
    s.definir_filo([piezas[("Puerta", None)].id], FILO_2, Cantos(True, True, True, True))
    s.editar_pieza(piezas[("Estante", None)].id, 1, D("86.0"), D("38.0"))
    _, avisos = s.guardar_modulo(_modulo(t, id=id_modulo, alto=D(70)))
    piezas = _piezas(t, id_modulo)
    puerta = piezas[("Puerta", None)]
    assert (puerta.medida_1, puerta.id_tipo_filo, puerta.cantos.cantidad) == (D("69.2"), FILO_2, 4)
    assert (piezas[("Estante", None)].medida_1, piezas[("Estante", None)].editada) == (D("86.0"), True)
    assert len(avisos) == 1 and "Estante" in avisos[0] and "86.4 × 38.2" in avisos[0]
    assert len([p for p in t["repo"].piezas_de_modulo(id_modulo) if p.tipo == "Estante"]) == 1


def test_quitar_un_cajon_avisa_si_tenia_piezas_editadas(taller):
    t = taller
    s = t["servicio"]
    caj = CajonGuardado(None, 1, t["placas"]["blanco55"], D(12), D(50))
    base = dict(armado="Cajonera con fajas de luz", alto=D(80), profundidad=D("51.8"), puertas=0, estantes=0,
                ancho=D(60), ancho_faja=D(10), id_placa_fondo=None, luz_superior=D("0.6"), luz_inferior=D("0.6"))
    id_modulo, _ = s.guardar_modulo(_modulo(t, cajones=(caj, caj, caj), **base))
    s.editar_pieza(_piezas(t, id_modulo)[("Frente de cajón", 3)].id, 1, D("59.4"), D(25))
    _, avisos = s.guardar_modulo(_modulo(t, id=id_modulo, cajones=(caj, caj), **base))
    assert any("Se quitó el cajón 3" in a for a in avisos)
    assert not [p for p in t["repo"].piezas_de_modulo(id_modulo) if p.orden_cajon == 3]


# ---------- filos (RF-15) ----------
def test_definir_filo_a_varias_piezas(taller):
    t = taller
    s = t["servicio"]
    id_modulo, _ = s.guardar_modulo(_modulo(t))
    piezas = _piezas(t, id_modulo)
    ids = [piezas[("Piso", None)].id, piezas[("Techo", None)].id]
    s.definir_filo(ids, FILO_045, Cantos(superior=True))
    assert all(t["repo"].pieza(i).id_tipo_filo == FILO_045 for i in ids)
    with pytest.raises(ErrorMuebles, match="Marcá qué cantos"):
        s.definir_filo(ids, FILO_2, Cantos())
    with pytest.raises(ErrorMuebles, match="no lleva cantos"):
        s.definir_filo(ids, SIN_FILO, Cantos(superior=True))


def test_laqueada_no_lleva_filo(taller):
    t = taller
    s = t["servicio"]
    id_modulo, _ = s.guardar_modulo(_modulo(t))
    puerta = _piezas(t, id_modulo)[("Puerta", None)]
    s.laquear([puerta.id], 1, 2)
    assert t["repo"].pieza(puerta.id).id_tipo_filo == SIN_FILO
    with pytest.raises(ErrorMuebles, match="laqueada"):
        s.definir_filo([puerta.id], FILO_2, Cantos(True, True, True, True))
    s.laquear([puerta.id], None, None)                                   # quitar la laca
    assert t["repo"].pieza(puerta.id).id_tipo_filo is None


def test_rotar_pieza_intercambia_medidas_y_cantos(taller):
    t = taller
    s = t["servicio"]
    id_modulo, _ = s.guardar_modulo(_modulo(t))
    lateral = _piezas(t, id_modulo)[("Lateral", None)]
    s.definir_filo([lateral.id], FILO_2, Cantos(izquierdo=True))
    s.rotar_pieza(lateral.id)
    rotada = t["repo"].pieza(lateral.id)
    assert (rotada.medida_1, rotada.medida_2) == (D("38.2"), D("56.4"))
    assert rotada.cantos == Cantos(superior=True) and rotada.editada


def test_dividir_fila(taller):
    t = taller
    s = t["servicio"]
    id_modulo, _ = s.guardar_modulo(_modulo(t))
    lateral = _piezas(t, id_modulo)[("Lateral", None)]
    nueva = s.dividir_fila(lateral.id, 1)
    assert (t["repo"].pieza(lateral.id).cantidad, t["repo"].pieza(nueva).cantidad) == (1, 1)
    s.definir_filo([nueva], FILO_2, Cantos(superior=True, izquierdo=True))   # el lateral visto
    with pytest.raises(ErrorMuebles, match="entre 1 y"):
        s.dividir_fila(lateral.id, 1)


def test_piezas_sueltas(taller):
    t = taller
    s = t["servicio"]
    id_ = s.agregar_pieza_suelta(t["id_mueble"], "Ajuste", "Revestimiento heladera", t["placas"]["roble18"], 1,
                                 D("60.55"), D(30))
    assert t["repo"].pieza(id_).medida_1 == D("60.5")
    id_modulo, _ = s.guardar_modulo(_modulo(t))
    with pytest.raises(ErrorMuebles, match="cambiá el módulo"):
        s.eliminar_pieza(_piezas(t, id_modulo)[("Piso", None)].id)
    s.eliminar_pieza(id_)


# ---------- zócalo ----------
def test_zocalo_con_parte_oculta(taller):
    t = taller
    s = t["servicio"]
    assert s.proponer_zocalo(D(180), D(55)) == (D(180), D("53.5"))
    id_z, _ = s.guardar_zocalo(ZocaloGuardado(None, t["id_mueble"], t["placas"]["roble18"], D(177), D(10),
                                              D("53.5"), refuerzos=2, id_placa_oculta=t["placas"]["blanco18"]))
    piezas = {p.tipo: p for p in t["repo"].piezas_de_zocalo(id_z)}
    assert piezas["Frente de zócalo"].id_material == t["placas"]["roble18"]
    assert piezas["Refuerzo de zócalo"].id_material == t["placas"]["blanco18"]
    assert (piezas["Lateral de zócalo"].cantidad, piezas["Lateral de zócalo"].medida_1) == (2, D("49.9"))


# ---------- trabajo que ya no se modifica ----------
def test_trabajo_cancelado_no_cambia_sus_muebles(taller):
    t = taller
    s = t["servicio"]
    tr = t["trabajos"]
    tr.cambiar_estado(t["sesion"], t["id_trabajo"], tr.estado_por_nombre("Cancelado").id)
    with pytest.raises(ErrorMuebles, match="cancelado"):
        s.guardar_modulo(_modulo(t))
    with pytest.raises(ErrorMuebles, match="cancelado"):
        s.guardar_mueble(None, t["id_trabajo"], "Alacena")


def test_previsualizar_no_guarda(taller):
    t = taller
    d = t["servicio"].previsualizar(_modulo(t))
    assert len(d.piezas) > 0 and t["repo"].piezas_ == {}
    sin_veta = {p.tipo for p in d.piezas if not p.con_veta}
    assert {"Lateral", "Fondo"} <= sin_veta and "Puerta" not in sin_veta   # blanco liso; puertas de roble


def test_pinos_nacen_sin_filo(taller):
    t = taller
    id_liston = t["materiales"].guardar_liston(None, "Pino", "2", "1")
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(t, lleva_techo=False, id_liston=id_liston))
    assert _piezas(t, id_modulo)[("Pino", None)].id_tipo_filo == SIN_FILO


def test_profundidad_de_la_caja_usa_el_espesor_de_la_placa_de_frentes(taller):
    t = taller
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(t, profundidad=D(60), luz_derecha=D("0.15")))
    piezas = _piezas(t, id_modulo)
    assert piezas[("Lateral", None)].medida_2 == D("58.2")      # frentes de roble de 18 mm
    assert piezas[("Puerta", None)].medida_2 == D("44.6")       # (90 − 0,3 − 0,15 − 0,3) / 2
    assert t["repo"].modulo(id_modulo).luz_derecha == D("0.15")


def test_largo_de_guia_propuesto_por_la_caja(taller):
    # Profundidad 51,8 − 1,8 de frentes = caja de 50 → entra la guía de 50 (telescópica, +0,2 ≤ 50,5).
    guia = taller["catalogo"].guias_[1]
    taller["catalogo"].guias_[1] = replace(guia, largos=(D(40), D(45), D(50)))
    assert taller["servicio"].proponer_largo_guia(1, D("51.8")) == D(50)
    assert taller["servicio"].proponer_largo_guia(1, D(50)) == D(45)


def test_modulos_iguales_multiplican_las_piezas(taller):
    t = taller
    caj = CajonGuardado(None, 1, t["placas"]["blanco55"], D(12), D(50))
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(t, cantidad=3, profundidad=D("51.8"), puertas=0,
                                                        cajones=(caj,), luz_superior=D(0), luz_inferior=D(0)))
    piezas = _piezas(t, id_modulo)
    lateral = piezas[("Lateral", None)]
    assert (lateral.cantidad, lateral.veces, lateral.total) == (2, 3, 6)
    assert piezas[("Lateral de cajón", 1)].total == 6                 # las del cajón también
    assert t["repo"].modulo(id_modulo).cantidad == 3
    assert sum(p.total for p in t["servicio"].piezas_del_trabajo(t["id_trabajo"])) == \
        3 * sum(p.cantidad for p in t["repo"].piezas_de_modulo(id_modulo))


def test_cantidad_de_modulos_fuera_de_rango(taller):
    with pytest.raises(ErrorMuebles, match="de 1 a 50"):
        taller["servicio"].guardar_modulo(_modulo(taller, cantidad=0))


def test_listado_bloqueado_mientras_falten_filos(taller):
    t = taller
    t["servicio"].guardar_modulo(_modulo(t))
    with pytest.raises(ErrorMuebles, match="Faltan definir los filos"):
        t["servicio"].listado_de_corte(t["id_trabajo"])


def test_listado_de_corte_con_filos_definidos(taller):
    t = taller
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(t, cantidad=2))
    ids = [p.id for p in t["repo"].piezas_de_modulo(id_modulo) if p.id_tipo_filo is None]
    t["servicio"].definir_filo(ids, FILO_045, Cantos(superior=True))
    secciones = t["servicio"].listado_de_corte(t["id_trabajo"])
    assert sum(s.total for s in secciones) == 2 * sum(p.cantidad for p in t["repo"].piezas_de_modulo(id_modulo))
    assert {s.titulo for s in secciones} >= {"Faplac Blanco · 18 mm", "Faplac Roble · 18 mm"}


def test_listado_de_trabajo_sin_piezas(taller):
    with pytest.raises(ErrorMuebles, match="no tiene piezas"):
        taller["servicio"].listado_de_corte(taller["id_trabajo"])
    with pytest.raises(ErrorMuebles, match="laqueadas"):
        taller["servicio"].listado_laqueador(taller["id_trabajo"])


def test_largos_de_guia_que_entran_en_la_caja(taller):
    guia = taller["catalogo"].guias_[1]
    taller["catalogo"].guias_[1] = replace(guia, largos=(D(35), D(40), D(45), D(50)))
    assert taller["servicio"].largos_que_entran(1, D(50)) == [D(45), D(40), D(35)]   # caja de 48,2
    assert taller["servicio"].largos_que_entran(1, D(30)) == []


def test_filo_por_patron_calcula_los_cantos_en_cada_pieza(taller):
    t = taller
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(t))     # 90 × 60 × 40
    piezas = _piezas(t, id_modulo)
    lateral, estante = piezas[("Lateral", None)], piezas[("Estante", None)]   # 56,4 × 38,2 y 86,4 × 38,2
    puerta = piezas[("Puerta", None)]                                         # 59,2 × 44,5
    t["servicio"].definir_filo_por_patron([lateral.id, estante.id, puerta.id], FILO_2, "un_largo")
    assert t["repo"].pieza(lateral.id).cantos == Cantos(superior=True)
    assert t["repo"].pieza(puerta.id).cantos == Cantos(superior=True)
    t["servicio"].rotar_pieza(puerta.id)                                      # 44,5 × 59,2: largo vertical
    t["servicio"].definir_filo_por_patron([puerta.id], FILO_2, "dos_largos")
    assert t["repo"].pieza(puerta.id).cantos == Cantos(izquierdo=True, derecho=True)
    with pytest.raises(ErrorMuebles, match="Elegí qué cantos"):
        t["servicio"].definir_filo_por_patron([lateral.id], FILO_2, None)
    t["servicio"].definir_filo_por_patron([lateral.id], SIN_FILO, None)
    assert t["repo"].pieza(lateral.id).cantos == Cantos()


def test_separar_fila_con_nombre(taller):
    t = taller
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(t))
    lateral = _piezas(t, id_modulo)[("Lateral", None)]
    nueva = t["servicio"].dividir_fila(lateral.id, 1, "Lateral visto")
    assert t["repo"].pieza(nueva).descripcion == "Lateral visto"
    assert t["repo"].pieza(lateral.id).cantidad == 1 and t["repo"].pieza(lateral.id).descripcion is None


def test_los_fondos_nacen_sin_filo_y_no_se_les_puede_poner(taller):
    t = taller
    id_modulo, _ = t["servicio"].guardar_modulo(_modulo(t))
    fondo = _piezas(t, id_modulo)[("Fondo", None)]
    assert fondo.id_tipo_filo == SIN_FILO
    with pytest.raises(ErrorMuebles, match="no llevan filo"):
        t["servicio"].definir_filo_por_patron([fondo.id], FILO_2, "un_largo")
    with pytest.raises(ErrorMuebles, match="no llevan filo"):
        t["servicio"].definir_filo([fondo.id], FILO_045, Cantos(superior=True))
    assert fondo not in t["servicio"].piezas_sin_filo(t["id_trabajo"])


def test_piso_de_cajon_nunca_lleva_filo(taller):
    t = taller
    oculta = next(g for g in t["catalogo"].guias_.values() if not any(x.pieza == "Lateral de cajón" for x in g.piezas))
    from carpinteria.negocio.catalogo import ServicioCatalogo
    ServicioCatalogo(t["catalogo"]).guardar_alto_contrafrente(oculta.id, "8,6")
    caj_oculto = CajonGuardado(None, oculta.id, t["placas"]["blanco18"], D(12), D(45))
    caj_tele = CajonGuardado(None, 1, t["placas"]["blanco55"], D(12), D(45))
    base = dict(armado="Cajonera con fajas de luz", alto=D(34), profundidad=D("51.8"), puertas=0, estantes=0,
                ancho=D(60), ancho_faja=D(10), id_placa_fondo=None, luz_superior=D("0.6"), luz_inferior=D("0.6"))
    id_oculto, _ = t["servicio"].guardar_modulo(_modulo(t, cajones=(caj_oculto,), **base))
    id_tele, _ = t["servicio"].guardar_modulo(_modulo(t, cajones=(caj_tele,), **base))
    piso_oculto = next(p for p in t["servicio"].piezas_de_modulo(id_oculto) if p.tipo == "Piso de cajón")
    piso_tele = next(p for p in t["servicio"].piezas_de_modulo(id_tele) if p.tipo == "Piso de cajón")
    assert piso_oculto.sin_filo_fijo and piso_oculto.id_tipo_filo == SIN_FILO
    assert piso_tele.id_tipo_filo == SIN_FILO      # con telescópica también: el piso es un fondo de 5,5
    with pytest.raises(ErrorMuebles, match="pisos de cajón no llevan filo"):
        t["servicio"].definir_filo_por_patron([piso_oculto.id], FILO_2, "un_largo")
    assert piso_oculto.id not in {p.id for p in t["servicio"].piezas_sin_filo(t["id_trabajo"])}


def test_con_telescopica_el_piso_del_cajon_va_en_5_5(taller):
    t = taller
    caj = CajonGuardado(None, 1, t["placas"]["blanco18"], D(12), D(50))
    with pytest.raises(ErrorMuebles, match="5,5 mm"):
        t["servicio"].guardar_modulo(_modulo(
            t, armado="Cajonera con fajas de luz", alto=D(34), profundidad=D("51.8"), puertas=0, estantes=0,
            ancho=D(60), ancho_faja=D(10), id_placa_fondo=None, cajones=(caj,)))
