"""Pruebas del catálogo de placas y listones (RF-08 a RF-11.1)."""
from decimal import Decimal as D

import pytest

from carpinteria.negocio.entidades import ColorPlaca, MarcaPlaca
from carpinteria.negocio.materiales import (ErrorMateriales, ServicioMateriales, formato_numero, leer_numero,
                                            texto_placa, texto_seccion)

from fakes import MaterialesEnMemoria


@pytest.fixture
def catalogo():
    repo = MaterialesEnMemoria()
    servicio = ServicioMateriales(repo)
    faplac = servicio.guardar_marca(MarcaPlaca(None, "Faplac"))
    egger = servicio.guardar_marca(MarcaPlaca(None, "Egger"))
    blanco = servicio.guardar_color(ColorPlaca(None, faplac, "Blanco Nieve", "BN"))
    roble = servicio.guardar_color(ColorPlaca(None, faplac, "Roble Kendal", None, tiene_veta=True))
    return servicio, repo, {"faplac": faplac, "egger": egger, "blanco": blanco, "roble": roble}


# ---------- números ----------
@pytest.mark.parametrize("texto, esperado", [("183", D("183.0")), ("5,5", D("5.5")), ("260.5", D("260.5"))])
def test_leer_numero(texto, esperado):
    assert leer_numero(texto, "x") == esperado


@pytest.mark.parametrize("texto", ["", "0", "-3", "abc", "1,25", "Infinity"])
def test_leer_numero_rechaza(texto):
    with pytest.raises(ErrorMateriales):
        leer_numero(texto, "x")


def test_formato_numero():
    assert (formato_numero(D("1.80")), formato_numero(D("260.0")), formato_numero(D("5.5"))) == ("1,8", "260", "5,5")


# ---------- marcas y colores ----------
def test_marca_repetida_sin_importar_mayusculas(catalogo):
    servicio, _, _ = catalogo
    with pytest.raises(ErrorMateriales, match="Ya existe"):
        servicio.guardar_marca(MarcaPlaca(None, "  FAPLAC "))


def test_color_necesita_nombre_o_codigo(catalogo):
    servicio, _, ids = catalogo
    with pytest.raises(ErrorMateriales, match="nombre del color, su código"):
        servicio.guardar_color(ColorPlaca(None, ids["faplac"], " ", None))
    assert servicio.guardar_color(ColorPlaca(None, ids["faplac"], None, "A-207"))   # solo código: válido


def test_codigo_unico_por_marca_pero_repetible_en_otra(catalogo):
    servicio, _, ids = catalogo
    with pytest.raises(ErrorMateriales, match="código «bn»"):
        servicio.guardar_color(ColorPlaca(None, ids["faplac"], "Otro", "bn"))
    # El mismo código en otra marca es otro color: se permite (RF-08.1).
    assert servicio.guardar_color(ColorPlaca(None, ids["egger"], "Blanco", "BN"))


def test_busqueda_de_colores_por_nombre_o_codigo(catalogo):
    servicio, _, ids = catalogo
    assert [c.id for c in servicio.colores("blanco")] == [ids["blanco"]]
    assert [c.id for c in servicio.colores("bn")] == [ids["blanco"]]
    assert [c.id for c in servicio.colores("faplac roble")] == [ids["roble"]]
    assert {c.id for c in servicio.colores(id_marca=ids["faplac"])} == {ids["blanco"], ids["roble"]}


def test_colores_de_una_marca_dada_de_baja_no_se_ofrecen(catalogo):
    servicio, _, ids = catalogo
    servicio.cambiar_estado_marca(ids["faplac"], False)
    assert servicio.colores() == []
    assert len(servicio.colores(incluir_bajas=True)) == 2
    with pytest.raises(ErrorMateriales, match="dada de baja"):
        servicio.guardar_color(ColorPlaca(None, ids["faplac"], "Gris", None))


def test_eliminar_marca_o_color_en_uso(catalogo):
    servicio, _, ids = catalogo
    with pytest.raises(ErrorMateriales, match="tiene colores"):
        servicio.eliminar_marca(ids["faplac"])
    servicio.eliminar_marca(ids["egger"])
    servicio.guardar_placa(None, ids["blanco"], "18", "183", "260")
    with pytest.raises(ErrorMateriales, match="no se puede eliminar"):
        servicio.eliminar_color(ids["blanco"])
    servicio.eliminar_color(ids["roble"])


def test_no_cambia_la_veta_de_un_color_en_uso(catalogo):
    servicio, repo, ids = catalogo
    repo.colores_en_uso.add(ids["roble"])
    with pytest.raises(ErrorMateriales, match="veta"):
        servicio.guardar_color(ColorPlaca(ids["roble"], ids["faplac"], "Roble Kendal", None, tiene_veta=False))
    servicio.guardar_color(ColorPlaca(ids["roble"], ids["faplac"], "Roble Kendal Natural", "RK", tiene_veta=True))


# ---------- placas ----------
def test_alta_de_placa_en_mm_y_cm(catalogo):
    servicio, repo, ids = catalogo
    id_ = servicio.guardar_placa(None, ids["blanco"], "5,5", "183", "260")
    placa = servicio.placas()[0]
    assert repo.p[id_].espesor == D("0.55")               # en la base, en cm
    assert placa.espesor_mm == D("5.5")
    assert texto_placa(placa) == "Faplac Blanco Nieve (BN) · 5,5 mm · 183 × 260"


@pytest.mark.parametrize("espesor, largo, mensaje", [("180", "183", "milímetros"), ("18", "1830", "centímetros"),
                                                     ("", "183", "espesor")])
def test_placa_con_unidades_equivocadas(catalogo, espesor, largo, mensaje):
    servicio, _, ids = catalogo
    with pytest.raises(ErrorMateriales, match=mensaje):
        servicio.guardar_placa(None, ids["blanco"], espesor, largo, "260")


def test_placa_repetida(catalogo):
    servicio, _, ids = catalogo
    servicio.guardar_placa(None, ids["blanco"], "18", "183", "260")
    with pytest.raises(ErrorMateriales, match="ya existe"):
        servicio.guardar_placa(None, ids["blanco"], "18,0", "183", "260")
    servicio.guardar_placa(None, ids["blanco"], "18", "183", "275")   # otra medida: otra placa (RF-11)


def test_medidas_habituales_de_la_marca(catalogo):
    servicio, _, ids = catalogo
    assert servicio.medidas_habituales(ids["faplac"]) is None
    servicio.guardar_placa(None, ids["blanco"], "18", "183", "260")
    servicio.guardar_placa(None, ids["roble"], "18", "183", "260")
    servicio.guardar_placa(None, ids["blanco"], "15", "183", "275")
    assert servicio.medidas_habituales(ids["faplac"]) == (D("183.0"), D("260.0"))


def test_placa_en_uso_no_cambia_medidas_ni_se_elimina(catalogo):
    servicio, repo, ids = catalogo
    id_ = servicio.guardar_placa(None, ids["blanco"], "18", "183", "260")
    repo.placas_en_uso.add(id_)
    with pytest.raises(ErrorMateriales, match="no se le puede cambiar"):
        servicio.guardar_placa(id_, ids["blanco"], "15", "183", "260")
    with pytest.raises(ErrorMateriales, match="no se puede eliminar"):
        servicio.eliminar_placa(id_)
    servicio.cambiar_estado_placa(id_, False)                    # baja lógica (RF-11.1)
    assert servicio.placas() == [] and len(servicio.placas(incluir_bajas=True)) == 1


def test_busqueda_de_placas(catalogo):
    servicio, _, ids = catalogo
    servicio.guardar_placa(None, ids["blanco"], "18", "183", "260")
    servicio.guardar_placa(None, ids["blanco"], "5,5", "183", "260")
    assert len(servicio.placas("blanco")) == 2
    assert [formato_numero(p.espesor_mm) for p in servicio.placas("blanco 18mm")] == ["18"]
    assert servicio.placas("roble") == []


def test_reactivar_placa_de_color_dado_de_baja(catalogo):
    servicio, _, ids = catalogo
    id_ = servicio.guardar_placa(None, ids["blanco"], "18", "183", "260")
    servicio.cambiar_estado_placa(id_, False)
    servicio.cambiar_estado_color(ids["blanco"], False)
    with pytest.raises(ErrorMateriales, match="reactivá primero el color"):
        servicio.cambiar_estado_placa(id_, True)


# ---------- listones ----------
def test_listones(catalogo):
    servicio, repo, _ = catalogo
    id_ = servicio.guardar_liston(None, "Pino", "2", "1")
    assert texto_seccion(servicio.listones()[0]) == '2 × 1"'
    with pytest.raises(ErrorMateriales, match="ya existe"):
        servicio.guardar_liston(None, "pino", "2,0", "1")
    with pytest.raises(ErrorMateriales, match="pulgadas"):
        servicio.guardar_liston(None, "Pino", "50", "1")
    repo.listones_en_uso.add(id_)
    with pytest.raises(ErrorMateriales, match="sección"):
        servicio.guardar_liston(id_, "Pino", "3", "1")
    servicio.guardar_liston(id_, "Pino cepillado", "2", "1")        # el nombre sí se puede corregir
    with pytest.raises(ErrorMateriales, match="no se puede eliminar"):
        servicio.eliminar_liston(id_)
