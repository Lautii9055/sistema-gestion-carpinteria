"""Cantos por patrón (RF-15.5)."""
from decimal import Decimal as D

import pytest

from carpinteria.negocio.entidades import Cantos
from carpinteria.negocio.filos import cantos_de_patron, nombre_de_cantos, patron_de_cantos

APAISADA = (D(80), D(30))     # medida 1 (veta) más larga: los largos son superior e inferior
PARADA = (D("71.4"), D(90))   # medida 2 más larga: los largos son izquierdo y derecho


@pytest.mark.parametrize("patron, apaisada, parada", [
    ("un_largo", Cantos(superior=True), Cantos(izquierdo=True)),
    ("dos_largos", Cantos(superior=True, inferior=True), Cantos(izquierdo=True, derecho=True)),
    ("un_corto", Cantos(izquierdo=True), Cantos(superior=True)),
    ("dos_cortos", Cantos(izquierdo=True, derecho=True), Cantos(superior=True, inferior=True)),
    ("largo_y_corto", Cantos(superior=True, izquierdo=True), Cantos(izquierdo=True, superior=True)),
    ("cuatro", Cantos(True, True, True, True), Cantos(True, True, True, True)),
])
def test_patron_segun_el_lado_largo_de_cada_pieza(patron, apaisada, parada):
    assert cantos_de_patron(patron, *APAISADA) == apaisada
    assert cantos_de_patron(patron, *PARADA) == parada
    assert patron_de_cantos(apaisada, *APAISADA) == patron


def test_nombre_de_cantos():
    assert nombre_de_cantos(Cantos(superior=True, inferior=True), *APAISADA) == "2 largos"
    assert nombre_de_cantos(Cantos(superior=True, inferior=True), *PARADA) == "2 cortos"
    assert nombre_de_cantos(Cantos(superior=True, inferior=True, izquierdo=True), *APAISADA) == "3 cantos"


def test_patron_desconocido():
    with pytest.raises(ValueError):
        cantos_de_patron("tres", *APAISADA)
