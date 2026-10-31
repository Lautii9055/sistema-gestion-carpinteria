"""Listado de corte y del laqueador (RF-21 a RF-24.1): lógica pura."""
from decimal import Decimal as D

from carpinteria.negocio.entidades import (Cantos, ColorLaca, ColorPlaca, Liston, PiezaGuardada, Placa,
                                           TerminacionLaca, TipoFilo)
from carpinteria.negocio.listado import armar_laqueador, armar_listado, nombre_de_archivo

ROBLE = ColorPlaca(1, 1, "Roble Kendal", None, tiene_veta=True, marca="Faplac")
BLANCO = ColorPlaca(2, 1, "Blanco", None, tiene_veta=False, marca="Faplac")
NEGRO = ColorPlaca(3, 1, "Negro", None, tiene_veta=False, marca="Faplac")
PLACAS = {10: Placa(10, 1, D("1.8"), D(183), D(260), color=ROBLE),
          11: Placa(11, 2, D("1.8"), D(183), D(260), color=BLANCO),
          12: Placa(12, 2, D("0.55"), D(183), D(260), color=BLANCO)}
LISTONES = {20: Liston(20, "Pino 2 × 1", D(2), D(1))}
FILOS = {1: TipoFilo(1, "Sin filo", D(0), D(0)), 2: TipoFilo(2, "0,45 mm", D("0.45"), D(0)),
         3: TipoFilo(3, "2 mm", D(2), D("0.2"))}
COLORES = {1: ROBLE, 2: BLANCO, 3: NEGRO}
TODOS = Cantos(True, True, True, True)


def pieza(tipo, material, cantidad, m1, m2, filo=1, cantos=Cantos(), veces=1, **otros):
    return PiezaGuardada(None, tipo, material, cantidad, D(str(m1)), D(str(m2)) if m2 is not None else None,
                         id_tipo_filo=filo, cantos=cantos, veces=veces, **otros)


def test_medida_de_corte_y_secciones_por_placa():
    secciones = armar_listado([
        pieza("Puerta", 10, 2, "59.2", "44.5", filo=3, cantos=TODOS),
        pieza("Lateral", 11, 2, "56.4", "38.2", filo=2, cantos=Cantos(superior=True)),
        pieza("Fondo", 12, 1, "59.7", "89.7"),
    ], PLACAS, LISTONES, FILOS, COLORES)
    assert [s.titulo for s in secciones] == ["Faplac Blanco · 18 mm", "Faplac Roble Kendal · 18 mm",
                                             "Faplac Blanco · 5,5 mm"]
    puerta = secciones[1].filas[0]
    assert (puerta.cantidad, puerta.medida_1, puerta.medida_2, puerta.filo) == (2, D("58.8"), D("44.1"), "2 mm")
    assert not puerta.rotable                                   # roble: la veta manda
    lateral = secciones[0].filas[0]
    assert (lateral.medida_1, lateral.medida_2, lateral.filo) == (D("56.4"), D("38.2"), "0,45 mm")
    assert lateral.rotable
    assert secciones[2].detalle == "Placa de 183 × 260"


def test_piezas_iguales_se_juntan_y_multiplican_por_modulos_iguales():
    secciones = armar_listado([
        pieza("Lateral", 11, 2, "56.4", "38.2", veces=3),
        pieza("Estante", 11, 1, "56.4", "38.2"),
        pieza("Piso", 11, 1, "90", "38.2"),
    ], PLACAS, LISTONES, FILOS, COLORES)
    filas = secciones[0].filas
    assert [(f.cantidad, f.medida_1, f.piezas) for f in filas] == [(1, D(90), "Piso"),
                                                                   (7, D("56.4"), "Lateral, Estante")]
    assert secciones[0].total == 8


def test_liso_se_pone_con_la_medida_mayor_primero_para_juntarse():
    secciones = armar_listado([
        pieza("Estante", 11, 1, "30", "80", filo=3, cantos=Cantos(izquierdo=True)),
        pieza("Estante", 11, 1, "80", "30", filo=3, cantos=Cantos(superior=True)),
    ], PLACAS, LISTONES, FILOS, COLORES)
    (fila,) = secciones[0].filas
    assert (fila.cantidad, fila.medida_1, fila.medida_2, fila.cantos) == (2, D(80), D("29.8"), Cantos(superior=True))


def test_con_veta_no_se_gira():
    secciones = armar_listado([pieza("Puerta", 10, 1, "30", "80")], PLACAS, LISTONES, FILOS, COLORES)
    assert (secciones[0].filas[0].medida_1, secciones[0].filas[0].medida_2) == (D(30), D(80))


def test_distinto_filo_o_cantos_no_se_juntan():
    secciones = armar_listado([
        pieza("Lateral", 11, 1, "70", "55", filo=3, cantos=Cantos(superior=True, derecho=True)),
        pieza("Lateral", 11, 1, "70", "55"),
    ], PLACAS, LISTONES, FILOS, COLORES)
    assert len(secciones[0].filas) == 2


def test_color_de_filo_distinto_al_de_la_pieza():
    secciones = armar_listado([
        pieza("Puerta", 11, 1, "70", "40", filo=3, cantos=TODOS, id_color_filo=3),
        pieza("Puerta", 11, 1, "60", "40", filo=3, cantos=TODOS, id_color_filo=2),   # mismo color: no se aclara
    ], PLACAS, LISTONES, FILOS, COLORES)
    assert [f.color_filo for f in secciones[0].filas] == ["Faplac Negro", None]


def test_listones_en_seccion_aparte_al_final():
    secciones = armar_listado([pieza("Pino", 20, 2, "87.4", None, veces=2), pieza("Piso", 11, 1, "90", "58.2")],
                              PLACAS, LISTONES, FILOS, COLORES)
    assert secciones[-1].es_liston and secciones[-1].titulo == "Pino 2 × 1"
    assert (secciones[-1].filas[0].cantidad, secciones[-1].filas[0].medida_1) == (4, D("87.4"))


def test_laqueador_agrupa_por_color_y_terminacion_con_medida_final():
    lacas = {1: ColorLaca(1, 1, "Gris Topo", "SW 7062", marca="Sherwin Williams")}
    terminaciones = {1: TerminacionLaca(1, "Satinado"), 2: TerminacionLaca(2, "Mate")}
    secciones = armar_laqueador([
        pieza("Puerta", 11, 2, "59.2", "44.5", id_color_laca=1, id_terminacion=1, veces=2),
        pieza("Frente de cajón", 11, 1, "59.4", "16.2", id_color_laca=1, id_terminacion=2),
        pieza("Lateral", 11, 2, "56.4", "38.2"),
    ], lacas, terminaciones, PLACAS)
    assert [(s.titulo, s.terminacion, s.total) for s in secciones] == [
        ("Sherwin Williams Gris Topo (SW 7062)", "Mate", 1), ("Sherwin Williams Gris Topo (SW 7062)", "Satinado", 4)]
    assert secciones[1].filas[0].medida_1 == D("59.2")


def test_nombre_de_archivo_sin_caracteres_invalidos():
    assert nombre_de_archivo(12, 'Cocina "Ferreyra" / PB', "Listado de corte") == \
        "Trabajo 12 - Cocina Ferreyra  PB - Listado de corte.pdf"


def test_cada_fila_lleva_la_medida_final_para_el_control_del_taller():
    secciones = armar_listado([
        pieza("Puerta", 10, 2, "77.2", "45.1", filo=3, cantos=TODOS),
        pieza("Estante", 11, 1, "30", "80", filo=3, cantos=Cantos(izquierdo=True)),   # liso: se gira
        pieza("Pino", 20, 2, "87.4", None),
    ], PLACAS, LISTONES, FILOS, COLORES)
    estante = secciones[0].filas[0]
    puerta = secciones[1].filas[0]
    assert (puerta.final_1, puerta.final_2, puerta.medida_1, puerta.medida_2) == (D("77.2"), D("45.1"), D("76.8"),
                                                                                D("44.7"))
    assert (estante.final_1, estante.final_2, estante.medida_1, estante.medida_2) == (D(80), D(30), D(80),
                                                                                    D("29.8"))
    assert secciones[-1].filas[0].final_1 == D("87.4")


def test_un_fondo_nunca_sale_con_filo_en_el_listado():
    secciones = armar_listado([pieza("Fondo", 12, 1, "59.7", "89.7", filo=3, cantos=TODOS)],
                              PLACAS, LISTONES, FILOS, COLORES)
    fila = secciones[0].filas[0]
    assert (fila.filo, fila.medida_1, fila.medida_2) == (None, D("89.7"), D("59.7"))
