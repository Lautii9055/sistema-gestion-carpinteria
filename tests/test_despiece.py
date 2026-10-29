"""Motor de despiece: los ejemplos de la sección 4.6 de los requerimientos, tal cual.

Cada prueba dice en el nombre qué ejemplo verifica. Las medidas son finales
(con el filo incluido); las de corte se verifican aparte.
"""
from decimal import Decimal as D

import pytest

from carpinteria.negocio.despiece import (Armado, Cajon, ErrorDespiece, Material, Modulo, Reglas, calcular_modulo,
                                          calcular_zocalo, medida_de_corte, proponer_largo_guia, proponer_zocalo,
                                          redondear, rotar)
from carpinteria.negocio.entidades import PiezaGuia, TipoGuia

LARGOS = tuple(D(x) for x in ("30", "35", "40", "45", "50"))
TELESCOPICA = TipoGuia(1, "Telescópica cierre suave", None, D("0.2"), largos=LARGOS, piezas=(
    PiezaGuia(10, "Lateral de cajón", 2, None, D("0"), D("0")),
    PiezaGuia(11, "Contrafrente de cajón", 1, D("6.3"), None, D("0")),
    PiezaGuia(12, "Frente interno de cajón", 1, D("6.3"), None, D("3")),
    PiezaGuia(13, "Piso de cajón", 1, D("2.7"), D("0"), None),
))
OCULTA_SIN_ALTO = TipoGuia(2, "Lateral oculto Eurohard", "Eurohard", D("0.8"), largos=LARGOS, piezas=(
    PiezaGuia(13, "Piso de cajón", 1, D("7.5"), D("0.9"), None),
))
OCULTA = TipoGuia(3, "Lateral oculto Häfele", "Häfele", D("0.8"), largos=LARGOS, piezas=(
    PiezaGuia(13, "Piso de cajón", 1, D("7.5"), D("0.9"), None),
    PiezaGuia(11, "Contrafrente de cajón", 1, D("8.7"), None, None, D("8.6")),
))
RINCON = TipoGuia(4, "Lateral oculto Rincón del Herraje", None, D("1.1"), largos=LARGOS)

CON_TIRADOR = dict(luz_superior=D("0.4"), luz_inferior=D("0.4"), luz_entre_frentes=D("0.3"))
CAJONERA_CON_TIRADOR = dict(luz_superior=D("0.6"), luz_inferior=D("0.6"), luz_entre_frentes=D("0.3"))


def medidas(despiece, tipo, cajon=None):
    """(cantidad, medida 1, medida 2) de las piezas de ese tipo."""
    return [(p.cantidad, p.medida_1, p.medida_2) for p in despiece.piezas if p.tipo == tipo and p.cajon == cajon]


def tipos(despiece):
    return [p.tipo for p in despiece.piezas]


# ---------- 4.6 Ejemplos de validación ----------
def test_bajo_mesada_90x75x55_sin_techo_1_estante_2_pinos():
    d = calcular_modulo(Modulo(Armado.MODULO, D(90), D(75), D(55), lleva_techo=False, estantes=1, lleva_pinos=True))
    assert medidas(d, "Piso") == [(1, D(90), D(55))]
    assert medidas(d, "Lateral") == [(2, D("73.2"), D(55))]
    assert medidas(d, "Estante") == [(1, D("86.4"), D(55))]
    assert medidas(d, "Pino") == [(2, D("86.4"), None)]
    assert "Techo" not in tipos(d)
    assert [p.material for p in d.piezas if p.tipo == "Pino"] == [Material.LISTON]


def test_modulo_con_techo_90x60x40_estante_fondo_2_puertas():
    d = calcular_modulo(Modulo(Armado.MODULO, D(90), D(60), D(40), estantes=1, puertas=2, lleva_fondo=True,
                               **CON_TIRADOR))
    assert medidas(d, "Piso") == [(1, D(90), D(40))]
    assert medidas(d, "Techo") == [(1, D(90), D(40))]
    assert medidas(d, "Lateral") == [(2, D("56.4"), D(40))]
    assert medidas(d, "Estante") == [(1, D("86.4"), D(40))]
    # Fondo (90 − 0,3) × (60 − 0,3), con la veta vertical por defecto: el alto primero.
    assert medidas(d, "Fondo") == [(1, D("59.7"), D("89.7"))]
    # Puertas: alto primero (veta vertical). Ancho (90 − 0,6 − 0,3) / 2 = 44,55 → 44,5.
    assert medidas(d, "Puerta") == [(2, D("59.2"), D("44.5"))]
    puerta = next(p for p in d.piezas if p.tipo == "Puerta")
    assert puerta.material is Material.FRENTES
    assert medida_de_corte(puerta.medida_1, puerta.medida_2, D("0.2"), True, True, True, True) == \
        (D("58.8"), D("44.1"))


def test_cajonera_60x34x50_fajas_de_luz_2_cajones_telescopicos():
    cajon = Cajon(TELESCOPICA, largo_guia=D(50), alto_caja=D(12))
    d = calcular_modulo(Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(34), D(50), ancho_faja=D(10),
                               cajones=(cajon, cajon), **CAJONERA_CON_TIRADOR))
    assert medidas(d, "Lateral") == [(2, D(34), D(50))]
    assert medidas(d, "Faja") == [(4, D("56.4"), D(10))]
    # (34 − 0,6 − 0,6 − 0,3) / 2 = 16,25 → 16,2
    for numero in (1, 2):
        assert medidas(d, "Frente de cajón", numero) == [(1, D("59.4"), D("16.2"))]
        assert medidas(d, "Lateral de cajón", numero) == [(2, D(50), D(12))]
        assert medidas(d, "Contrafrente de cajón", numero) == [(1, D("50.1"), D(12))]
        assert medidas(d, "Frente interno de cajón", numero) == [(1, D("50.1"), D(9))]
        assert medidas(d, "Piso de cajón", numero) == [(1, D("53.7"), D(50))]
    assert medida_de_corte(D("59.4"), D("16.2"), D("0.2"), True, True, True, True) == (D("59.0"), D("15.8"))
    piso = next(p for p in d.piezas if p.tipo == "Piso de cajón")
    lateral = next(p for p in d.piezas if p.tipo == "Lateral de cajón")
    assert (piso.material, lateral.material) == (Material.PISO_CAJON, Material.CAJONES)
    assert "Puerta" not in tipos(d) and "Piso" not in tipos(d)


def test_cajonera_80_de_alto_3_cajones_reparto_en_partes_iguales():
    cajon = Cajon(TELESCOPICA, D(45), D(12))
    d = calcular_modulo(Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(80), D(50), ancho_faja=D(10),
                               cajones=(cajon,) * 3, **CAJONERA_CON_TIRADOR))
    assert d.altos_frentes_cajon == [D("26.0")] * 3      # 78,2 / 3 = 26,07 → 26,0


def test_cajonera_80_de_alto_primer_frente_de_15():
    libre = Cajon(TELESCOPICA, D(45), D(12))
    d = calcular_modulo(Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(80), D(50), ancho_faja=D(10),
                               cajones=(Cajon(TELESCOPICA, D(45), D(12), D(15)), libre, libre), **CAJONERA_CON_TIRADOR))
    assert d.altos_frentes_cajon == [D(15), D("31.6"), D("31.6")]


def test_modulo_mixto_90x75_cajon_arriba_de_15_y_2_puertas():
    d = calcular_modulo(Modulo(Armado.MODULO, D(90), D(75), D(55), puertas=2, luz_superior=D("0.4"),
                               luz_inferior=D(0), luz_entre_frentes=D("0.3"),
                               cajones=(Cajon(TELESCOPICA, D(50), D(12), D(15)),)))
    assert medidas(d, "Frente de cajón", 1) == [(1, D("89.4"), D(15))]
    # 75 − 0,4 − 0 − 15 − 0,3 = 59,3
    assert medidas(d, "Puerta") == [(2, D("59.3"), D("44.5"))]


def test_bajo_mesada_con_gola_90x75_2_puertas():
    d = calcular_modulo(Modulo(Armado.MODULO, D(90), D(75), D(55), lleva_techo=False, puertas=2,
                               luz_superior=D(3), luz_inferior=D(0), luz_entre_frentes=D(3)))
    assert medidas(d, "Puerta") == [(2, D(72), D("44.5"))]


def test_alacena_90x60_2_puertas_sobresale_abajo():
    d = calcular_modulo(Modulo(Armado.MODULO, D(90), D(60), D(30), puertas=2, luz_superior=D(0),
                               luz_inferior=D("-1.3"), luz_entre_frentes=D("0.3")))
    assert medidas(d, "Puerta") == [(2, D("61.3"), D("44.5"))]


# ---------- 4.1 y 4.4: otras reglas ----------
def test_cajonera_laterales_de_luz():
    d = calcular_modulo(Modulo(Armado.CAJONERA_LATERALES_DE_LUZ, D(60), D(34), D(50), ancho_faja=D(12),
                               cajones=(Cajon(TELESCOPICA, D(50), D(12)),), **CAJONERA_CON_TIRADOR))
    assert medidas(d, "Lateral") == [(2, D("30.4"), D(50))]
    assert medidas(d, "Faja") == [(4, D(60), D(12))]


def test_cajon_con_guia_oculta_ejemplo_de_la_seccion_4_4():
    # Módulo de 60 (interior 56,4) con guía de 45 → piso 48,9 × 44,1; contrafrente 47,7 × alto de la marca.
    d = calcular_modulo(Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(34), D(50), ancho_faja=D(10),
                               cajones=(Cajon(OCULTA, D(45), D(12)),), **CAJONERA_CON_TIRADOR))
    assert medidas(d, "Piso de cajón", 1) == [(1, D("48.9"), D("44.1"))]
    assert medidas(d, "Contrafrente de cajón", 1) == [(1, D("47.7"), D("8.6"))]
    assert "Lateral de cajón" not in tipos(d) and "Frente interno de cajón" not in tipos(d)


def test_guia_oculta_sin_alto_de_contrafrente_avisa():
    with pytest.raises(ErrorDespiece, match="Falta el alto del contrafrente"):
        calcular_modulo(Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(34), D(50), ancho_faja=D(10),
                               cajones=(Cajon(OCULTA_SIN_ALTO, D(45), D(12)),)))


@pytest.mark.parametrize("profundidad, telescopica, oculta, rincon", [
    ("50", "50", "45", "45"), ("48", "45", "45", "45"), ("40.5", "40", "40", "35"),
    ("40", "40", "35", "35"), ("37", "35", "35", "35"),
])
def test_tabla_de_largos_de_guia_seccion_4_4_d(profundidad, telescopica, oculta, rincon):
    assert proponer_largo_guia(TELESCOPICA, D(profundidad)) == D(telescopica)
    assert proponer_largo_guia(OCULTA, D(profundidad)) == D(oculta)
    assert proponer_largo_guia(RINCON, D(profundidad)) == D(rincon)


def test_sin_largos_cargados_no_hay_propuesta():
    assert proponer_largo_guia(TipoGuia(9, "Sin datos"), D(50)) is None
    assert proponer_largo_guia(TELESCOPICA, D(20)) is None


def test_guia_que_no_entra():
    with pytest.raises(ErrorDespiece, match="no entra"):
        calcular_modulo(Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(34), D(40), ancho_faja=D(10),
                               cajones=(Cajon(TELESCOPICA, D(45), D(12)),)))


def test_redondeo_hacia_abajo_al_milimetro():
    assert (redondear(D("44.55")), redondear(D("16.25")), redondear(D("26.0666"))) == (D("44.5"), D("16.2"), D("26.0"))


# ---------- 4.4 bis Zócalo ----------
def test_zocalo_propuesto_180x55():
    assert proponer_zocalo(D(180), D(55)) == (D(180), D("53.5"))


def test_piezas_del_zocalo():
    piezas = calcular_zocalo(D(177), D(10), D("53.5"), refuerzos=2)
    resumen = [(p.tipo, p.cantidad, p.medida_1, p.medida_2, p.material) for p in piezas]
    assert resumen == [
        ("Frente de zócalo", 1, D(177), D(10), Material.ZOCALO),
        ("Trasera de zócalo", 1, D(177), D(10), Material.ZOCALO_OCULTO),
        ("Lateral de zócalo", 2, D("49.9"), D(10), Material.ZOCALO),
        ("Refuerzo de zócalo", 2, D("49.9"), D(10), Material.ZOCALO_OCULTO),
    ]
    assert len(calcular_zocalo(D(90), D(8), D(50))) == 3          # sin refuerzos


# ---------- 4.5 Filos: medida de corte ----------
def test_lateral_visto_con_filo_en_un_canto_corto():
    assert medida_de_corte(D("73.2"), D(55), D("0.2"), izquierdo=True) == (D("73.0"), D(55))


def test_filo_045_no_descuenta():
    assert medida_de_corte(D("86.4"), D(55), D(0), superior=True) == (D("86.4"), D(55))


# ---------- validaciones ----------
@pytest.mark.parametrize("modulo, mensaje", [
    (Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(34), D(50), cajones=(Cajon(TELESCOPICA, D(45), D(12)),)),
     "ancho de las fajas"),
    (Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(34), D(50), ancho_faja=D(10), puertas=2,
            cajones=(Cajon(TELESCOPICA, D(45), D(12)),)), "no lleva puertas"),
    (Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(34), D(50), ancho_faja=D(10)), "al menos un cajón"),
    (Modulo(Armado.MODULO, D(90), D(60), D(40), lleva_pinos=True), "bajo mesadas"),
    (Modulo(Armado.MODULO, D(90), D(75), D(55), puertas=2, cajones=(Cajon(TELESCOPICA, D(50), D(12)),)),
     "alto del frente de cada cajón"),
    (Modulo(Armado.MODULO, D(0), D(75), D(55)), "Completá"),
    (Modulo(Armado.MODULO, D(90), D(10), D(55), puertas=1, luz_superior=D(6), luz_inferior=D(6)), "Revisá"),
])
def test_validaciones(modulo, mensaje):
    with pytest.raises(ErrorDespiece, match=mensaje):
        calcular_modulo(modulo)


def test_frentes_fijos_que_no_completan_el_espacio():
    fijo = Cajon(TELESCOPICA, D(45), D(12), D(20))
    with pytest.raises(ErrorDespiece, match="no completan"):
        calcular_modulo(Modulo(Armado.CAJONERA_FAJAS_DE_LUZ, D(60), D(80), D(50), ancho_faja=D(10),
                               cajones=(fijo, fijo), **CAJONERA_CON_TIRADOR))


# ---------- veta y fondo (RN-02, RN-02.1) ----------
def test_fondo_de_un_mueble_de_30x30():
    d = calcular_modulo(Modulo(Armado.MODULO, D(30), D(30), D(30), lleva_fondo=True))
    assert medidas(d, "Fondo") == [(1, D("29.7"), D("29.7"))]


def test_sin_fondo_no_hay_pieza_de_fondo():
    assert "Fondo" not in tipos(calcular_modulo(Modulo(Armado.MODULO, D(90), D(60), D(40))))


def test_descuento_del_fondo_configurable():
    d = calcular_modulo(Modulo(Armado.MODULO, D(90), D(60), D(40), lleva_fondo=True),
                        Reglas(descuento_fondo=D("0.5")))
    assert medidas(d, "Fondo") == [(1, D("59.5"), D("89.5"))]


def test_rotar_la_veta_por_tipo_de_pieza_al_cargar_el_modulo():
    d = calcular_modulo(Modulo(Armado.MODULO, D(90), D(60), D(40), puertas=2, lleva_fondo=True,
                               rotar=frozenset({"Fondo", "Puerta"}), **CON_TIRADOR))
    assert medidas(d, "Fondo") == [(1, D("89.7"), D("59.7"))]
    assert medidas(d, "Puerta") == [(2, D("44.5"), D("59.2"))]
    assert medidas(d, "Lateral") == [(2, D("56.4"), D(40))]          # el resto, sin cambios


def test_rotar_una_pieza_y_los_listones_no_se_rotan():
    d = calcular_modulo(Modulo(Armado.MODULO, D(90), D(75), D(55), lleva_techo=False, lleva_pinos=True))
    lateral = next(p for p in d.piezas if p.tipo == "Lateral")
    pino = next(p for p in d.piezas if p.tipo == "Pino")
    assert rotar(lateral).medidas == (D(55), D("73.2"))
    assert rotar(rotar(lateral)) == lateral
    assert rotar(pino) == pino


def test_piezas_de_material_liso_quedan_rotables():
    d = calcular_modulo(Modulo(Armado.MODULO, D(90), D(60), D(40), puertas=2, lleva_fondo=True,
                               sin_veta=frozenset({Material.ESTRUCTURA, Material.FONDO}), **CON_TIRADOR))
    con_veta = {p.tipo: p.con_veta for p in d.piezas}
    assert con_veta == {"Piso": False, "Techo": False, "Lateral": False, "Fondo": False, "Puerta": True}
