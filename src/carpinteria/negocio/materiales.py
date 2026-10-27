"""Catálogo de materiales, primera parte: marcas, colores, placas y listones
(RF-08, RF-08.1, RF-10, RF-11 y RF-11.1).

- Un color pertenece a una marca y se identifica por nombre, código o ambos
  (el mismo color puede tener otro código en otra marca). La veta es del color.
- Una placa es un color en un espesor y una medida de placa entera. Se carga en
  milímetros (18, 15, 9, 5,5) y centímetros (183 × 260), como se habla en el
  taller; en la base el espesor queda en centímetros (1,8).
- Nada en uso se borra: se da de baja y deja de ofrecerse para cargas nuevas,
  pero los trabajos anteriores lo siguen mostrando. Lo que nunca se usó (por
  ejemplo, algo cargado por error) sí se puede eliminar.
- Una placa en uso tampoco cambia de color, espesor ni medidas: si cambió, se
  da de baja y se carga la nueva (así el historial no se altera).
"""
import unicodedata
from dataclasses import replace
from decimal import Decimal, InvalidOperation

from carpinteria.negocio.autenticacion import ErrorAutenticacion
from carpinteria.negocio.clientes import terminos_de_busqueda
from carpinteria.negocio.entidades import ColorPlaca, Liston, MarcaPlaca, Placa
from carpinteria.negocio.puertos import RepositorioMateriales

ESPESORES_HABITUALES_MM = (Decimal(18), Decimal(15), Decimal(9), Decimal("5.5"))
ESPESOR_MAXIMO_MM = Decimal(60)
MEDIDA_MAXIMA_CM = Decimal(400)
SECCION_MAXIMA_PULGADAS = Decimal(12)


class ErrorMateriales(ErrorAutenticacion):
    """Error de validación del catálogo; se muestra tal cual."""


def _sin_tildes(texto: str | None) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "")
                   if unicodedata.category(c) != "Mn").casefold()


def _texto(valor: str | None) -> str | None:
    return " ".join((valor or "").split()) or None


def _largo(valor: str | None, campo: str, maximo: int) -> str | None:
    if valor and len(valor) > maximo:
        raise ErrorMateriales(f"{campo} puede tener hasta {maximo} caracteres.")
    return valor


def leer_numero(texto: str | None, campo: str, decimales: int = 1) -> Decimal:
    """Número escrito como en el taller: "183", "5,5" o "5.5"."""
    limpio = (texto or "").strip().replace(",", ".")
    if not limpio:
        raise ErrorMateriales(f"Completá {campo}.")
    try:
        numero = Decimal(limpio)
    except InvalidOperation:
        raise ErrorMateriales(f"Revisá {campo}: escribí solo el número (por ejemplo: 183 o 5,5).") from None
    if not numero.is_finite() or numero <= 0:
        raise ErrorMateriales(f"Revisá {campo}: tiene que ser mayor que cero.")
    paso = Decimal(1).scaleb(-decimales)
    if numero != numero.quantize(paso):
        raise ErrorMateriales(f"Revisá {campo}: como máximo {decimales} decimal"
                              f"{'es' if decimales > 1 else ''}.")
    return numero.quantize(paso)


def formato_numero(numero: Decimal | None) -> str:
    """1.80 → "1,8"; 260.0 → "260"."""
    if numero is None:
        return ""
    texto = f"{numero.normalize():f}"
    return texto.replace(".", ",")


def coincide(textos: list[str | None], busqueda: str) -> bool:
    """Todas las palabras buscadas aparecen en alguno de los textos (sin tildes ni mayúsculas)."""
    juntos = " ".join(_sin_tildes(t) for t in textos if t)
    return all(_sin_tildes(p) in juntos for p in terminos_de_busqueda(busqueda))


class ServicioMateriales:
    def __init__(self, repositorio: RepositorioMateriales) -> None:
        self._repo = repositorio

    # ---------- marcas ----------
    def marcas(self, incluir_bajas: bool = False) -> list[MarcaPlaca]:
        return sorted((m for m in self._repo.marcas() if incluir_bajas or m.es_activo),
                      key=lambda m: (not m.es_activo, _sin_tildes(m.nombre)))

    def guardar_marca(self, marca: MarcaPlaca) -> int:
        nombre = _largo(_texto(marca.nombre), "El nombre de la marca", 50)
        if not nombre:
            raise ErrorMateriales("Completá el nombre de la marca.")
        if any(_sin_tildes(m.nombre) == _sin_tildes(nombre) and m.id != marca.id for m in self._repo.marcas()):
            raise ErrorMateriales(f"Ya existe la marca «{nombre}».")
        marca = replace(marca, nombre=nombre)
        if marca.id is None:
            return self._repo.crear_marca(marca)
        self._repo.actualizar_marca(marca)
        return marca.id

    def cambiar_estado_marca(self, id_marca: int, activa: bool) -> None:
        marca = self._marca(id_marca)
        self._repo.actualizar_marca(replace(marca, es_activo=activa))

    def eliminar_marca(self, id_marca: int) -> None:
        if self._repo.marca_en_uso(id_marca):
            raise ErrorMateriales("La marca tiene colores cargados: no se puede eliminar. Podés darla de baja.")
        self._repo.eliminar_marca(id_marca)

    def _marca(self, id_marca: int) -> MarcaPlaca:
        marca = next((m for m in self._repo.marcas() if m.id == id_marca), None)
        if marca is None:
            raise ErrorMateriales("La marca ya no existe.")
        return marca

    # ---------- colores ----------
    def colores(self, busqueda: str = "", id_marca: int | None = None,
                incluir_bajas: bool = False) -> list[ColorPlaca]:
        """Búsqueda por nombre o código (RF-08.1) y por marca."""
        return sorted(
            (c for c in self._repo.colores()
             if (incluir_bajas or (c.es_activo and c.marca_activa)) and (id_marca is None or c.id_marca == id_marca)
             and coincide([c.nombre, c.codigo, c.marca], busqueda)),
            key=lambda c: (not c.es_activo, _sin_tildes(c.marca), _sin_tildes(c.descripcion)))

    def guardar_color(self, color: ColorPlaca) -> int:
        nombre = _largo(_texto(color.nombre), "El nombre del color", 60)
        codigo = _largo(_texto(color.codigo), "El código", 30)
        if not nombre and not codigo:
            raise ErrorMateriales("Completá el nombre del color, su código o los dos.")
        marca = self._marca(color.id_marca)
        if not marca.es_activo and color.id is None:
            raise ErrorMateriales(f"La marca «{marca.nombre}» está dada de baja.")
        for otro in self._repo.colores():
            if otro.id == color.id or otro.id_marca != color.id_marca:
                continue
            if codigo and otro.codigo and _sin_tildes(otro.codigo) == _sin_tildes(codigo):
                raise ErrorMateriales(f"En {marca.nombre} ya existe un color con el código «{codigo}» "
                                      f"({otro.descripcion}).")
            if nombre and otro.nombre and _sin_tildes(otro.nombre) == _sin_tildes(nombre):
                raise ErrorMateriales(f"En {marca.nombre} ya existe el color «{nombre}».")
        if color.id is not None:
            actual = self._color(color.id)
            if actual.tiene_veta != color.tiene_veta and self._repo.color_en_uso(color.id):
                raise ErrorMateriales("El color ya se usa en trabajos: no se puede cambiar si tiene veta. "
                                      "Dalo de baja y cargalo de nuevo.")
        color = replace(color, nombre=nombre, codigo=codigo)
        if color.id is None:
            return self._repo.crear_color(color)
        self._repo.actualizar_color(color)
        return color.id

    def cambiar_estado_color(self, id_color: int, activo: bool) -> None:
        self._repo.actualizar_color(replace(self._color(id_color), es_activo=activo))

    def eliminar_color(self, id_color: int) -> None:
        if self._repo.color_en_uso(id_color):
            raise ErrorMateriales("El color tiene placas o piezas que lo usan: no se puede eliminar. "
                                  "Podés darlo de baja.")
        self._repo.eliminar_color(id_color)

    def _color(self, id_color: int) -> ColorPlaca:
        color = next((c for c in self._repo.colores() if c.id == id_color), None)
        if color is None:
            raise ErrorMateriales("El color ya no existe.")
        return color

    # ---------- placas ----------
    def placas(self, busqueda: str = "", incluir_bajas: bool = False) -> list[Placa]:
        def textos(p: Placa) -> list[str | None]:
            c = p.color
            return [c.nombre, c.codigo, c.marca, f"{formato_numero(p.espesor_mm)}mm",
                    formato_numero(p.espesor_mm)] if c else []
        def disponible(p: Placa) -> bool:   # una placa se ofrece si ella, su color y su marca están activos
            return p.es_activo and (p.color is None or (p.color.es_activo and p.color.marca_activa))
        return sorted(
            (p for p in self._repo.placas() if (incluir_bajas or disponible(p)) and coincide(textos(p), busqueda)),
            key=lambda p: (not p.es_activo, _sin_tildes(p.color.marca if p.color else ""),
                           _sin_tildes(p.color.descripcion if p.color else ""), -p.espesor))

    def medidas_habituales(self, id_marca: int) -> tuple[Decimal, Decimal] | None:
        """Medida de placa entera más usada en esa marca, para proponerla (RF-11)."""
        conteo: dict[tuple[Decimal, Decimal], int] = {}
        for p in self._repo.placas():
            if p.color and p.color.id_marca == id_marca:
                conteo[(p.largo, p.ancho)] = conteo.get((p.largo, p.ancho), 0) + 1
        return max(conteo, key=conteo.get) if conteo else None

    def guardar_placa(self, id_placa: int | None, id_color: int | None, espesor_mm: str,
                      largo_cm: str, ancho_cm: str) -> int:
        if id_color is None:
            raise ErrorMateriales("Elegí el color de la placa.")
        color = self._color(id_color)
        espesor = leer_numero(espesor_mm, "el espesor (en mm)")
        largo = leer_numero(largo_cm, "el largo (en cm)")
        ancho = leer_numero(ancho_cm, "el ancho (en cm)")
        if espesor > ESPESOR_MAXIMO_MM:
            raise ErrorMateriales("Revisá el espesor: va en milímetros (por ejemplo: 18).")
        if largo > MEDIDA_MAXIMA_CM or ancho > MEDIDA_MAXIMA_CM:
            raise ErrorMateriales("Revisá las medidas: van en centímetros (por ejemplo: 183 × 260).")
        placa = Placa(id_placa, id_color, (espesor / 10).quantize(Decimal("0.01")), largo, ancho)
        for otra in self._repo.placas():
            if otra.id != id_placa and (otra.id_color, otra.espesor, otra.largo, otra.ancho) == \
                    (placa.id_color, placa.espesor, placa.largo, placa.ancho):
                raise ErrorMateriales(f"Esa placa ya existe ({color.marca} {color.descripcion} "
                                      f"{formato_numero(espesor)} mm)" + ("" if otra.es_activo else
                                                                          ", dada de baja: reactivala") + ".")
        if id_placa is None:
            if not color.es_activo:
                raise ErrorMateriales("El color está dado de baja.")
            return self._repo.crear_placa(placa)
        actual = self._placa(id_placa)
        if actual.en_uso and (actual.id_color, actual.espesor, actual.largo, actual.ancho) != \
                (placa.id_color, placa.espesor, placa.largo, placa.ancho):
            raise ErrorMateriales("La placa ya se usa en trabajos: no se le puede cambiar el color, el espesor "
                                  "ni las medidas. Dala de baja y cargá la nueva.")
        self._repo.actualizar_placa(replace(placa, es_activo=actual.es_activo))
        return id_placa

    def cambiar_estado_placa(self, id_placa: int, activa: bool) -> None:
        placa = self._placa(id_placa)
        if activa and placa.color and not placa.color.es_activo:
            raise ErrorMateriales("Su color está dado de baja: reactivá primero el color.")
        self._repo.actualizar_placa(replace(placa, es_activo=activa))

    def eliminar_placa(self, id_placa: int) -> None:
        if self._placa(id_placa).en_uso:
            raise ErrorMateriales("La placa se usa en trabajos o retazos: no se puede eliminar. Podés darla de baja.")
        self._repo.eliminar_placa(id_placa)

    def _placa(self, id_placa: int) -> Placa:
        placa = next((p for p in self._repo.placas() if p.id == id_placa), None)
        if placa is None:
            raise ErrorMateriales("La placa ya no existe.")
        return placa

    # ---------- listones ----------
    def listones(self, incluir_bajas: bool = False) -> list[Liston]:
        return sorted((x for x in self._repo.listones() if incluir_bajas or x.es_activo),
                      key=lambda x: (not x.es_activo, _sin_tildes(x.nombre), x.ancho_pulgadas, x.alto_pulgadas))

    def guardar_liston(self, id_liston: int | None, nombre: str, ancho_pulgadas: str, alto_pulgadas: str) -> int:
        nombre = _largo(_texto(nombre), "El nombre", 50)
        if not nombre:
            raise ErrorMateriales("Completá el nombre (por ejemplo: Pino).")
        ancho = leer_numero(ancho_pulgadas, "el ancho de la sección (en pulgadas)", 2)
        alto = leer_numero(alto_pulgadas, "el alto de la sección (en pulgadas)", 2)
        if ancho > SECCION_MAXIMA_PULGADAS or alto > SECCION_MAXIMA_PULGADAS:
            raise ErrorMateriales("Revisá la sección: va en pulgadas (por ejemplo: 2 × 1).")
        liston = Liston(id_liston, nombre, ancho, alto)
        for otro in self._repo.listones():
            if otro.id != id_liston and _sin_tildes(otro.nombre) == _sin_tildes(nombre) and \
                    (otro.ancho_pulgadas, otro.alto_pulgadas) == (ancho, alto):
                raise ErrorMateriales("Ese listón ya existe.")
        if id_liston is None:
            return self._repo.crear_liston(liston)
        actual = self._liston(id_liston)
        if actual.en_uso and (actual.ancho_pulgadas, actual.alto_pulgadas) != (ancho, alto):
            raise ErrorMateriales("El listón ya se usa en trabajos: no se le puede cambiar la sección. "
                                  "Dalo de baja y cargá el nuevo.")
        self._repo.actualizar_liston(replace(liston, es_activo=actual.es_activo))
        return id_liston

    def cambiar_estado_liston(self, id_liston: int, activo: bool) -> None:
        self._repo.actualizar_liston(replace(self._liston(id_liston), es_activo=activo))

    def eliminar_liston(self, id_liston: int) -> None:
        if self._liston(id_liston).en_uso:
            raise ErrorMateriales("El listón se usa en trabajos: no se puede eliminar. Podés darlo de baja.")
        self._repo.eliminar_liston(id_liston)

    def _liston(self, id_liston: int) -> Liston:
        liston = next((x for x in self._repo.listones() if x.id == id_liston), None)
        if liston is None:
            raise ErrorMateriales("El listón ya no existe.")
        return liston


def texto_placa(p: Placa) -> str:
    """"Faplac Blanco Nieve · 18 mm · 183 × 260"."""
    color = f"{p.color.marca} {p.color.descripcion}" if p.color else "Placa"
    return f"{color} · {formato_numero(p.espesor_mm)} mm · {formato_numero(p.largo)} × {formato_numero(p.ancho)}"


def texto_seccion(x: Liston) -> str:
    return f'{formato_numero(x.ancho_pulgadas)} × {formato_numero(x.alto_pulgadas)}"'
