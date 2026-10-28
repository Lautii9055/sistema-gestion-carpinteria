"""Catálogo, segunda parte: tipos de filo (RF-09), lacas (RF-15.2), estilos de
frente (RF-11.0) y guías de cajón (sección 4.4 de los requerimientos).

Reglas:
- Lo que nunca se usó se puede eliminar; lo que está en uso se da de baja
  (RF-11.1). Los tipos de filo no tienen baja: son pocos y fijos.
- Un filo en uso no cambia su espesor ni su descuento: el listado de corte se
  calcula con ese descuento y los trabajos ya hechos cambiarían. "Sin filo" no
  se elimina ni se renombra: el sistema lo asigna a las piezas laqueadas.
- Las piezas que lleva cada guía son datos (no código): una guía nueva se crea
  "basada en" otra y copia sus reglas. En las guías laterales ocultas solo
  cambia, según la marca, el alto del contrafrente.
"""
import unicodedata
from dataclasses import replace
from decimal import Decimal, InvalidOperation

from carpinteria.negocio.autenticacion import ErrorAutenticacion
from carpinteria.negocio.entidades import (ColorLaca, EstiloFrente, MarcaPintura, PiezaGuia, TerminacionLaca,
                                          TipoFilo, TipoGuia)
from carpinteria.negocio.materiales import coincide
from carpinteria.negocio.puertos import RepositorioCatalogo

SIN_FILO = "Sin filo"
CONTRAFRENTE = "Contrafrente de cajón"
DESCUENTO_ANCHO_CONTRAFRENTE_OCULTA = Decimal("8.7")   # igual en las tres marcas (requerimientos 4.4)


class ErrorCatalogo(ErrorAutenticacion):
    """Error de validación del catálogo; se muestra tal cual."""


def _clave(texto: str | None) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "")
                   if unicodedata.category(c) != "Mn").casefold().strip()


def _texto(valor: str | None, campo: str, maximo: int, obligatorio: bool = True) -> str | None:
    limpio = " ".join((valor or "").split()) or None
    if obligatorio and not limpio:
        raise ErrorCatalogo(f"Completá {campo}.")
    if limpio and len(limpio) > maximo:
        raise ErrorCatalogo(f"{campo[0].upper()}{campo[1:]} puede tener hasta {maximo} caracteres.")
    return limpio


def leer_decimal(texto: str | Decimal | None, campo: str, minimo: Decimal, maximo: Decimal,
                 decimales: int = 2, obligatorio: bool = True) -> Decimal | None:
    """Número con coma o punto, dentro de un rango. Acepta negativos si el mínimo lo permite."""
    if isinstance(texto, Decimal):
        numero = texto
    else:
        limpio = (texto or "").strip().replace(",", ".")
        if not limpio:
            if obligatorio:
                raise ErrorCatalogo(f"Completá {campo}.")
            return None
        try:
            numero = Decimal(limpio)
        except InvalidOperation:
            raise ErrorCatalogo(f"Revisá {campo}: escribí solo el número.") from None
    if not numero.is_finite() or not minimo <= numero <= maximo:
        raise ErrorCatalogo(f"Revisá {campo}: tiene que estar entre {_fmt(minimo)} y {_fmt(maximo)}.")
    paso = Decimal(1).scaleb(-decimales)
    if numero != numero.quantize(paso):
        raise ErrorCatalogo(f"Revisá {campo}: como máximo {decimales} decimales.")
    return numero.quantize(paso)


def _fmt(numero: Decimal) -> str:
    return f"{numero.normalize():f}".replace(".", ",")


def _repetido(nombre: str, otros, propio_id: int | None, que: str) -> None:
    if any(_clave(o.nombre) == _clave(nombre) and o.id != propio_id for o in otros):
        raise ErrorCatalogo(f"Ya existe {que} «{nombre}».")


def _buscar(lista, id_, que: str):
    elemento = next((x for x in lista if x.id == id_), None)
    if elemento is None:
        raise ErrorCatalogo(f"{que} ya no existe.")
    return elemento


class ServicioCatalogo:
    def __init__(self, repositorio: RepositorioCatalogo) -> None:
        self._repo = repositorio

    # ---------- filos ----------
    def filos(self) -> list[TipoFilo]:
        return sorted(self._repo.filos(), key=lambda f: (f.espesor_mm, _clave(f.nombre)))

    def guardar_filo(self, id_filo: int | None, nombre: str, espesor_mm: str, descuento_cm: str) -> int:
        nombre = _texto(nombre, "el nombre del filo", 30)
        espesor = leer_decimal(espesor_mm, "el espesor (mm)", Decimal(0), Decimal(5))
        descuento = leer_decimal(descuento_cm, "el descuento por canto (cm)", Decimal(0), Decimal(1))
        filos = self._repo.filos()
        _repetido(nombre, filos, id_filo, "el filo")
        filo = TipoFilo(id_filo, nombre, espesor, descuento)
        if id_filo is not None:
            actual = _buscar(filos, id_filo, "El filo")
            if actual.nombre == SIN_FILO and (nombre != SIN_FILO or espesor or descuento):
                raise ErrorCatalogo("«Sin filo» no se modifica: el sistema lo usa para las piezas laqueadas.")
            if actual.en_uso and (actual.espesor_mm, actual.descuento_cm) != (espesor, descuento):
                raise ErrorCatalogo("El filo ya se usa en piezas: no se le puede cambiar el espesor ni el descuento "
                                    "(cambiarían los listados de trabajos anteriores). Cargá uno nuevo.")
        return self._repo.guardar_filo(filo)

    def eliminar_filo(self, id_filo: int) -> None:
        filo = _buscar(self._repo.filos(), id_filo, "El filo")
        if filo.nombre == SIN_FILO:
            raise ErrorCatalogo("«Sin filo» no se elimina: el sistema lo usa para las piezas laqueadas.")
        if filo.en_uso:
            raise ErrorCatalogo("El filo se usa en piezas: no se puede eliminar.")
        self._repo.eliminar_filo(id_filo)

    # ---------- lacas: marcas ----------
    def marcas_pintura(self, incluir_bajas: bool = False) -> list[MarcaPintura]:
        return sorted((m for m in self._repo.marcas_pintura() if incluir_bajas or m.es_activo),
                      key=lambda m: (not m.es_activo, _clave(m.nombre)))

    def guardar_marca_pintura(self, id_marca: int | None, nombre: str) -> int:
        nombre = _texto(nombre, "el nombre de la marca", 50)
        marcas = self._repo.marcas_pintura()
        _repetido(nombre, marcas, id_marca, "la marca")
        activa = _buscar(marcas, id_marca, "La marca").es_activo if id_marca else True
        return self._repo.guardar_marca_pintura(MarcaPintura(id_marca, nombre, activa))

    def cambiar_estado_marca_pintura(self, id_marca: int, activa: bool) -> None:
        marca = _buscar(self._repo.marcas_pintura(), id_marca, "La marca")
        self._repo.guardar_marca_pintura(replace(marca, es_activo=activa))

    def eliminar_marca_pintura(self, id_marca: int) -> None:
        if any(c.id_marca == id_marca for c in self._repo.colores_laca()):
            raise ErrorCatalogo("La marca tiene colores cargados: no se puede eliminar. Podés darla de baja.")
        self._repo.eliminar_marca_pintura(id_marca)

    # ---------- lacas: colores ----------
    def colores_laca(self, busqueda: str = "", incluir_bajas: bool = False) -> list[ColorLaca]:
        return sorted(
            (c for c in self._repo.colores_laca()
             if (incluir_bajas or (c.es_activo and c.marca_activa)) and coincide([c.nombre, c.codigo, c.marca], busqueda)),
            key=lambda c: (not c.es_activo, _clave(c.marca), _clave(c.descripcion)))

    def guardar_color_laca(self, id_color: int | None, id_marca: int | None, nombre: str | None,
                           codigo: str | None) -> int:
        if id_marca is None:
            raise ErrorCatalogo("Elegí la marca de la laca.")
        nombre = _texto(nombre, "el nombre del color", 60, obligatorio=False)
        codigo = _texto(codigo, "el código", 30, obligatorio=False)
        if not nombre and not codigo:
            raise ErrorCatalogo("Completá el nombre del color, su código o los dos.")
        marca = _buscar(self._repo.marcas_pintura(), id_marca, "La marca")
        if not marca.es_activo and id_color is None:
            raise ErrorCatalogo(f"La marca «{marca.nombre}» está dada de baja.")
        colores = self._repo.colores_laca()
        for otro in colores:
            if otro.id == id_color or otro.id_marca != id_marca:
                continue
            if codigo and otro.codigo and _clave(otro.codigo) == _clave(codigo):
                raise ErrorCatalogo(f"En {marca.nombre} ya existe un color con el código «{codigo}».")
            if nombre and otro.nombre and _clave(otro.nombre) == _clave(nombre):
                raise ErrorCatalogo(f"En {marca.nombre} ya existe el color «{nombre}».")
        activo = _buscar(colores, id_color, "El color").es_activo if id_color else True
        return self._repo.guardar_color_laca(ColorLaca(id_color, id_marca, nombre, codigo, activo))

    def cambiar_estado_color_laca(self, id_color: int, activo: bool) -> None:
        color = _buscar(self._repo.colores_laca(), id_color, "El color")
        self._repo.guardar_color_laca(replace(color, es_activo=activo))

    def eliminar_color_laca(self, id_color: int) -> None:
        if _buscar(self._repo.colores_laca(), id_color, "El color").en_uso:
            raise ErrorCatalogo("El color se usa en trabajos: no se puede eliminar. Podés darlo de baja.")
        self._repo.eliminar_color_laca(id_color)

    # ---------- lacas: terminaciones ----------
    def terminaciones(self, incluir_bajas: bool = False) -> list[TerminacionLaca]:
        return [t for t in self._repo.terminaciones() if incluir_bajas or t.es_activo]

    def guardar_terminacion(self, id_terminacion: int | None, nombre: str) -> int:
        nombre = _texto(nombre, "el nombre de la terminación", 30)
        lista = self._repo.terminaciones()
        _repetido(nombre, lista, id_terminacion, "la terminación")
        activa = _buscar(lista, id_terminacion, "La terminación").es_activo if id_terminacion else True
        return self._repo.guardar_terminacion(TerminacionLaca(id_terminacion, nombre, activa))

    def cambiar_estado_terminacion(self, id_terminacion: int, activa: bool) -> None:
        t = _buscar(self._repo.terminaciones(), id_terminacion, "La terminación")
        self._repo.guardar_terminacion(replace(t, es_activo=activa))

    def eliminar_terminacion(self, id_terminacion: int) -> None:
        if _buscar(self._repo.terminaciones(), id_terminacion, "La terminación").en_uso:
            raise ErrorCatalogo("La terminación se usa en trabajos: no se puede eliminar. Podés darla de baja.")
        self._repo.eliminar_terminacion(id_terminacion)

    # ---------- estilos de frente ----------
    def estilos(self, incluir_bajas: bool = False) -> list[EstiloFrente]:
        return sorted((e for e in self._repo.estilos() if incluir_bajas or e.es_activo),
                      key=lambda e: (not e.es_activo, _clave(e.nombre)))

    def guardar_estilo(self, id_estilo: int | None, nombre: str, luz_superior: str, luz_inferior: str,
                       luz_entre: str, descripcion: str | None) -> int:
        nombre = _texto(nombre, "el nombre del estilo", 50)
        superior = leer_decimal(luz_superior, "la luz superior (cm)", Decimal(-10), Decimal(10))
        inferior = leer_decimal(luz_inferior, "la luz inferior (cm)", Decimal(-10), Decimal(10))
        entre = leer_decimal(luz_entre, "la luz entre frentes (cm)", Decimal(0), Decimal(10))
        descripcion = _texto(descripcion, "la descripción", 200, obligatorio=False)
        lista = self._repo.estilos()
        _repetido(nombre, lista, id_estilo, "el estilo")
        activo = _buscar(lista, id_estilo, "El estilo").es_activo if id_estilo else True
        return self._repo.guardar_estilo(EstiloFrente(id_estilo, nombre, superior, inferior, entre, descripcion, activo))

    def cambiar_estado_estilo(self, id_estilo: int, activo: bool) -> None:
        e = _buscar(self._repo.estilos(), id_estilo, "El estilo")
        self._repo.guardar_estilo(replace(e, es_activo=activo))

    def eliminar_estilo(self, id_estilo: int) -> None:
        if _buscar(self._repo.estilos(), id_estilo, "El estilo").en_uso:
            raise ErrorCatalogo("El estilo se usa en módulos: no se puede eliminar. Podés darlo de baja.")
        self._repo.eliminar_estilo(id_estilo)

    # ---------- guías ----------
    def guias(self, incluir_bajas: bool = False) -> list[TipoGuia]:
        return sorted((g for g in self._repo.guias() if incluir_bajas or g.es_activo),
                      key=lambda g: (not g.es_activo, _clave(g.nombre)))

    def guardar_guia(self, id_guia: int | None, nombre: str, marca: str | None, espacio_adicional: str,
                     basada_en: int | None = None) -> int:
        """Alta (copiando las piezas de la guía en la que se basa) o modificación."""
        nombre = _texto(nombre, "el nombre de la guía", 50)
        marca = _texto(marca, "la marca", 50, obligatorio=False)
        espacio = leer_decimal(espacio_adicional, "el espacio adicional (cm)", Decimal(0), Decimal(5))
        guias = self._repo.guias()
        _repetido(nombre, guias, id_guia, "la guía")
        if id_guia is None:
            if basada_en is None:
                raise ErrorCatalogo("Elegí en qué guía se basa: de ahí toma las piezas que lleva el cajón.")
            _buscar(guias, basada_en, "La guía de base")
            nuevo = self._repo.guardar_guia(TipoGuia(None, nombre, marca, espacio))
            self._repo.copiar_piezas_guia(basada_en, nuevo)
            return nuevo
        actual = _buscar(guias, id_guia, "La guía")
        return self._repo.guardar_guia(replace(actual, nombre=nombre, marca=marca, espacio_adicional=espacio))

    def cambiar_estado_guia(self, id_guia: int, activa: bool) -> None:
        g = _buscar(self._repo.guias(), id_guia, "La guía")
        self._repo.guardar_guia(replace(g, es_activo=activa))

    def eliminar_guia(self, id_guia: int) -> None:
        if _buscar(self._repo.guias(), id_guia, "La guía").en_uso:
            raise ErrorCatalogo("La guía se usa en cajones: no se puede eliminar. Podés darla de baja.")
        self._repo.eliminar_guia(id_guia)

    def agregar_largo(self, id_guia: int, largo: str) -> None:
        valor = leer_decimal(largo, "el largo (cm)", Decimal(10), Decimal(120), decimales=1)
        guia = _buscar(self._repo.guias(), id_guia, "La guía")
        if valor in guia.largos:
            raise ErrorCatalogo(f"La guía ya tiene el largo {_fmt(valor)} cm.")
        self._repo.agregar_largo_guia(id_guia, valor)

    def quitar_largo(self, id_guia: int, largo: Decimal) -> None:
        self._repo.quitar_largo_guia(id_guia, largo)

    @staticmethod
    def usa_contrafrente_fijo(guia: TipoGuia) -> bool:
        """Guías laterales ocultas: el contrafrente tiene un alto fijo según la marca
        (o todavía no se cargó). Las telescópicas lo calculan del alto del cajón."""
        contrafrente = next((p for p in guia.piezas if p.pieza == CONTRAFRENTE), None)
        return contrafrente is None or contrafrente.alto_fijo is not None

    @staticmethod
    def alto_contrafrente(guia: TipoGuia) -> Decimal | None:
        contrafrente = next((p for p in guia.piezas if p.pieza == CONTRAFRENTE), None)
        return contrafrente.alto_fijo if contrafrente else None

    def guardar_alto_contrafrente(self, id_guia: int, alto: str) -> None:
        """Contrafrente de guía oculta: (ancho interior − 8,7) × alto fijo de la marca."""
        guia = _buscar(self._repo.guias(), id_guia, "La guía")
        if not self.usa_contrafrente_fijo(guia):
            raise ErrorCatalogo("En esta guía el contrafrente se calcula con el alto del cajón.")
        valor = leer_decimal(alto, "el alto del contrafrente (cm)", Decimal(1), Decimal(40), decimales=1)
        id_pieza = self._repo.id_tipo_pieza(CONTRAFRENTE)
        if id_pieza is None:
            raise ErrorCatalogo("Falta el tipo de pieza «Contrafrente de cajón» en la base.")
        self._repo.guardar_pieza_guia(id_guia, PiezaGuia(id_pieza, CONTRAFRENTE, 1,
                                                         descuento_ancho=DESCUENTO_ANCHO_CONTRAFRENTE_OCULTA,
                                                         alto_fijo=valor))


def texto_regla(pieza: PiezaGuia) -> str:
    """"2 × (largo de la guía) × (alto del cajón)", como lo escribiría el carpintero."""
    def medida(referencia: str, descuento: Decimal | None) -> str:
        return referencia if not descuento else f"({referencia} − {_fmt(descuento)})"

    partes = []
    if pieza.descuento_ancho is not None:
        partes.append(medida("ancho interior", pieza.descuento_ancho))
    if pieza.descuento_largo is not None:
        partes.append(medida("largo guía", pieza.descuento_largo))
    if pieza.alto_fijo is not None:
        partes.append(f"{_fmt(pieza.alto_fijo)} (fijo)")
    elif pieza.descuento_alto is not None:
        partes.append(medida("alto cajón", pieza.descuento_alto))
    return f"{pieza.cantidad} × " + " × ".join(partes)


def formato(numero: Decimal | None) -> str:
    return _fmt(numero) if numero is not None else ""
