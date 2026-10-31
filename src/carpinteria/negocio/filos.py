"""Cantos con filo elegidos por patrón (RF-15.5): en vez de marcar canto por canto,
se elige «1 largo», «2 cortos», «1 largo y 1 corto», etc.

Los cantos largos son los del lado más largo de la pieza. Con la medida 1 dibujada
en horizontal, los cantos superior e inferior miden la medida 1 y los izquierdo y
derecho, la medida 2. Por eso el mismo patrón da cantos distintos en piezas
apaisadas o paradas, y se calcula pieza por pieza al aplicarlo a varias.
"""
from __future__ import annotations

from decimal import Decimal

from carpinteria.negocio.entidades import Cantos

# (clave, nombre para mostrar, cantos largos, cantos cortos)
PATRONES: list[tuple[str, str, int, int]] = [
    ("un_largo", "1 largo", 1, 0),
    ("dos_largos", "2 largos", 2, 0),
    ("un_corto", "1 corto", 0, 1),
    ("dos_cortos", "2 cortos", 0, 2),
    ("largo_y_corto", "1 largo y 1 corto", 1, 1),
    ("cuatro", "Los 4 cantos", 2, 2),
]
NOMBRES = {clave: nombre for clave, nombre, _, _ in PATRONES}

# Piezas que nunca llevan filo (RN-08.3): nacen «Sin filo» y no se les puede poner.
TIPOS_SIN_FILO = ("Fondo", "Piso de cajón")   # el piso del cajón es un fondo, con cualquier guía
# Con guía de lateral oculto (cualquier marca), el piso del cajón es como un fondo (RN-08.4).
PISO_DE_CAJON = "Piso de cajón"


def _lados(medida_1: Decimal, medida_2: Decimal | None) -> tuple[tuple[str, str], tuple[str, str]]:
    """(cantos largos, cantos cortos), cada uno en el orden en que se marcan."""
    horizontales, verticales = ("superior", "inferior"), ("izquierdo", "derecho")
    if medida_2 is None or medida_1 >= medida_2:
        return horizontales, verticales
    return verticales, horizontales


def cantos_de_patron(patron: str, medida_1: Decimal, medida_2: Decimal | None) -> Cantos:
    datos = next((p for p in PATRONES if p[0] == patron), None)
    if datos is None:
        raise ValueError(f"Patrón de cantos desconocido: {patron}")
    _, _, largos, cortos = datos
    lados_largos, lados_cortos = _lados(medida_1, medida_2)
    marcados = set(lados_largos[:largos]) | set(lados_cortos[:cortos])
    return Cantos(**{lado: lado in marcados for lado in ("superior", "inferior", "izquierdo", "derecho")})


def patron_de_cantos(cantos: Cantos, medida_1: Decimal, medida_2: Decimal | None) -> str | None:
    """El patrón que corresponde a unos cantos, o None si no es uno de los habituales."""
    lados_largos, lados_cortos = _lados(medida_1, medida_2)
    largos = sum(getattr(cantos, lado) for lado in lados_largos)
    cortos = sum(getattr(cantos, lado) for lado in lados_cortos)
    return next((clave for clave, _, l_, c in PATRONES if (l_, c) == (largos, cortos)), None)


def nombre_de_cantos(cantos: Cantos, medida_1: Decimal, medida_2: Decimal | None) -> str:
    patron = patron_de_cantos(cantos, medida_1, medida_2)
    if patron:
        return NOMBRES[patron]
    n = cantos.cantidad
    return f"{n} canto{'s' if n != 1 else ''}"
