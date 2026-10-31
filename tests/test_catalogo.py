"""Pruebas del catálogo, parte 2: filos, lacas, estilos de frente y guías."""
from decimal import Decimal as D

import pytest

from carpinteria.negocio.catalogo import ErrorCatalogo, ServicioCatalogo, leer_decimal, texto_regla

from fakes import CatalogoEnMemoria


@pytest.fixture
def catalogo():
    repo = CatalogoEnMemoria()
    return ServicioCatalogo(repo), repo


def test_leer_decimal_con_rango_y_negativos():
    assert leer_decimal("-1,3", "x", D(-10), D(10)) == D("-1.30")
    with pytest.raises(ErrorCatalogo, match="entre 0 y 10"):
        leer_decimal("-1", "x", D(0), D(10))
    with pytest.raises(ErrorCatalogo, match="decimales"):
        leer_decimal("0,125", "x", D(0), D(1))


# ---------- filos ----------
def test_alta_y_orden_de_filos(catalogo):
    servicio, _ = catalogo
    servicio.guardar_filo(None, "1 mm", "1", "0,1")
    assert [f.nombre for f in servicio.filos()] == ["Sin filo", "0,45 mm", "1 mm", "2 mm"]


def test_sin_filo_no_se_toca(catalogo):
    servicio, _ = catalogo
    with pytest.raises(ErrorCatalogo, match="Sin filo"):
        servicio.eliminar_filo(1)
    with pytest.raises(ErrorCatalogo, match="Sin filo"):
        servicio.guardar_filo(1, "Sin filo", "0", "0,1")


def test_filo_en_uso_no_cambia_el_descuento(catalogo):
    servicio, repo = catalogo
    repo.en_uso.add(("filo", 3))
    with pytest.raises(ErrorCatalogo, match="listados de trabajos anteriores"):
        servicio.guardar_filo(3, "2 mm", "2", "0,25")
    servicio.guardar_filo(3, "2 mm PVC", "2", "0,2")            # el nombre sí
    with pytest.raises(ErrorCatalogo, match="no se puede eliminar"):
        servicio.eliminar_filo(3)
    servicio.eliminar_filo(2)


def test_filo_repetido_y_rangos(catalogo):
    servicio, _ = catalogo
    with pytest.raises(ErrorCatalogo, match="Ya existe"):
        servicio.guardar_filo(None, "2 MM", "2", "0,2")
    with pytest.raises(ErrorCatalogo, match="descuento"):
        servicio.guardar_filo(None, "Grueso", "3", "2")


# ---------- lacas ----------
def test_colores_de_laca(catalogo):
    servicio, repo = catalogo
    gris = servicio.guardar_color_laca(None, 2, "Gris Topo", "SW 7062")
    with pytest.raises(ErrorCatalogo, match="código"):
        servicio.guardar_color_laca(None, 2, "Otro", "sw 7062")
    servicio.guardar_color_laca(None, 1, None, "SW 7062")           # otro fabricante: válido
    assert [c.id for c in servicio.colores_laca("topo")] == [gris]
    servicio.cambiar_estado_marca_pintura(2, False)
    assert [c.marca for c in servicio.colores_laca()] == ["Alba"]  # los de una marca dada de baja no se ofrecen
    repo.en_uso.add(("color", gris))
    with pytest.raises(ErrorCatalogo, match="no se puede eliminar"):
        servicio.eliminar_color_laca(gris)
    with pytest.raises(ErrorCatalogo, match="tiene colores"):
        servicio.eliminar_marca_pintura(1)


def test_terminaciones(catalogo):
    servicio, repo = catalogo
    servicio.guardar_terminacion(None, "Satinado")
    with pytest.raises(ErrorCatalogo, match="Ya existe"):
        servicio.guardar_terminacion(None, "mate")
    servicio.cambiar_estado_terminacion(3, False)
    assert [t.nombre for t in servicio.terminaciones()] == ["Mate", "Semimate", "Satinado"]


# ---------- estilos de frente ----------
def test_estilo_con_luz_negativa(catalogo):
    servicio, repo = catalogo
    id_ = servicio.guardar_estilo(None, "Alacena", "0", "-1,3", "0,3", "Sobresale abajo")
    assert repo.estilos_[id_].luz_inferior == D("-1.30")
    with pytest.raises(ErrorCatalogo, match="luz entre frentes"):
        servicio.guardar_estilo(None, "Otro", "0", "0", "-0,3", None)
    repo.en_uso.add(("estilo", 1))
    with pytest.raises(ErrorCatalogo, match="no se puede eliminar"):
        servicio.eliminar_estilo(1)


# ---------- guías ----------
def test_guia_nueva_basada_en_otra(catalogo):
    servicio, repo = catalogo
    with pytest.raises(ErrorCatalogo, match="en qué guía se basa"):
        servicio.guardar_guia(None, "Lateral oculto Häfele", "Häfele", "0,8")
    id_ = servicio.guardar_guia(None, "Lateral oculto Häfele", "Häfele", "0,8", basada_en=2)
    assert [p.pieza for p in repo.guias_[id_].piezas] == ["Piso de cajón"]


def test_largos_de_guia(catalogo):
    servicio, repo = catalogo
    for largo in ("45", "30", "27"):
        servicio.agregar_largo(1, largo)
    assert repo.guias_[1].largos == (D("27.0"), D("30.0"), D("45.0"))
    with pytest.raises(ErrorCatalogo, match="ya tiene"):
        servicio.agregar_largo(1, "30,0")
    with pytest.raises(ErrorCatalogo, match="entre 10 y 120"):
        servicio.agregar_largo(1, "450")
    servicio.quitar_largo(1, D("30.0"))
    assert repo.guias_[1].largos == (D("27.0"), D("45.0"))


def test_alto_del_contrafrente_de_guia_oculta(catalogo):
    servicio, repo = catalogo
    tele, oculta = repo.guias_[1], repo.guias_[2]
    assert not servicio.usa_contrafrente_fijo(tele) and servicio.usa_contrafrente_fijo(oculta)
    assert servicio.alto_contrafrente(oculta) is None                 # dato pendiente
    servicio.guardar_alto_contrafrente(2, "8,6")
    contrafrente = next(p for p in repo.guias_[2].piezas if p.pieza == "Contrafrente de cajón")
    assert (contrafrente.descuento_ancho, contrafrente.alto_fijo) == (D("8.7"), D("8.6"))
    assert texto_regla(contrafrente) == "1 × (ancho interior − 8,7) × 8,6 (fijo)"
    servicio.guardar_alto_contrafrente(2, "9")                        # se corrige, no se duplica
    assert len([p for p in repo.guias_[2].piezas if p.pieza == "Contrafrente de cajón"]) == 1
    with pytest.raises(ErrorCatalogo, match="alto del cajón"):
        servicio.guardar_alto_contrafrente(1, "9")


def test_texto_de_reglas_de_la_telescopica(catalogo):
    _, repo = catalogo
    reglas = [texto_regla(p) for p in repo.guias_[1].piezas]
    assert reglas == ["2 × largo guía × alto cajón", "1 × (ancho interior − 6,3) × alto cajón",
                      "1 × (ancho interior − 6,3) × (alto cajón − 3)", "1 × (ancho interior − 3) × (largo guía − 0,3)"]


def test_guia_en_uso_no_se_elimina(catalogo):
    servicio, repo = catalogo
    repo.en_uso.add(("guia", 1))
    with pytest.raises(ErrorCatalogo, match="no se puede eliminar"):
        servicio.eliminar_guia(1)
    servicio.cambiar_estado_guia(1, False)
    assert [g.id for g in servicio.guias()] == [2]
