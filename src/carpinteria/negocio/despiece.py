"""Motor de despiece (M5, reglas de la sección 4 de los requerimientos).

Calcula las piezas de un módulo (estructura, puertas, frentes y cajas de los
cajones) y de un zócalo a partir de sus medidas y opciones. Es lógica pura: no
toca la base de datos ni la pantalla, así se prueba con los ejemplos de la
sección 4.6 tal como están escritos.

Convenciones:
- Medidas en centímetros. Cada resultado se redondea hacia abajo al milímetro
  (RN-03: 44,55 → 44,5).
- Las piezas salen con su medida FINAL (terminada, con el filo incluido). La
  medida de corte se calcula al armar el listado, restando el filo (RN-03.1).
- La primera medida es SIEMPRE el sentido de la veta (RN-02). Cada tipo de pieza
  propone uno (vertical en puertas, laterales y fondos; horizontal en el resto) y
  al cargar el módulo se puede rotar por tipo de pieza; después, pieza por pieza.
- Si el color de la placa es liso, la pieza queda marcada "con_veta = False": se
  puede rotar para el menor desperdicio (lo decide el optimizador / la maderera).
- Los filos no se asignan: toda pieza nace con el filo sin definir (RN-08).
"""
from dataclasses import dataclass, field, replace
from decimal import ROUND_FLOOR, Decimal
from enum import Enum

from carpinteria.negocio.autenticacion import ErrorAutenticacion
from carpinteria.negocio.entidades import TipoGuia

DECIMO = Decimal("0.1")


class ErrorDespiece(ErrorAutenticacion):
    """Datos del módulo que no permiten calcular; el mensaje se muestra tal cual."""


class Armado(Enum):
    MODULO = "Módulo"
    CAJONERA_FAJAS_DE_LUZ = "Cajonera con fajas de luz"
    CAJONERA_LATERALES_DE_LUZ = "Cajonera con laterales de luz"

    @property
    def es_cajonera(self) -> bool:
        return self is not Armado.MODULO


class Material(Enum):
    """De qué placa (o listón) del módulo sale cada pieza (RF-14)."""
    ESTRUCTURA = "estructura"
    FRENTES = "frentes"
    CAJONES = "cajones"          # caja del cajón: laterales, contrafrente y frente interno
    PISO_CAJON = "piso del cajón"
    FONDO = "fondo"
    LISTON = "listón"
    ZOCALO = "zócalo"            # partes visibles del zócalo
    ZOCALO_OCULTO = "zócalo (oculto)"


@dataclass(frozen=True)
class Reglas:
    """Valores fijos de la tabla Parametro (sección 5)."""
    luz_lateral: Decimal = Decimal("0.3")        # a cada costado de puertas y frentes de cajón
    luz_entre_puertas: Decimal = Decimal("0.3")
    tolerancia_guia: Decimal = Decimal("0.5")    # cuánto puede sobresalir la guía
    retiro_zocalo: Decimal = Decimal("1.5")
    descuento_fondo: Decimal = Decimal("0.3")    # el fondo mide 0,3 menos que el módulo en ancho y alto


@dataclass(frozen=True)
class Cajon:
    guia: TipoGuia
    largo_guia: Decimal
    alto_caja: Decimal                      # estimado al diseñar (ej.: 12)
    alto_frente: Decimal | None = None      # None = reparto en partes iguales


@dataclass(frozen=True)
class Modulo:
    armado: Armado
    ancho: Decimal
    alto: Decimal                           # sin zócalo
    profundidad: Decimal
    espesor: Decimal = Decimal("1.8")       # de la placa de la estructura
    lleva_techo: bool = True
    ancho_faja: Decimal | None = None       # solo cajoneras
    estantes: int = 0
    puertas: int = 0
    lleva_fondo: bool = False
    lleva_pinos: bool = False
    luz_superior: Decimal = Decimal(0)
    luz_inferior: Decimal = Decimal(0)
    luz_entre_frentes: Decimal = Decimal(0)
    cajones: tuple[Cajon, ...] = ()         # de arriba hacia abajo
    rotar: frozenset[str] = frozenset()     # tipos de pieza con la veta rotada (ej.: {"Fondo", "Puerta"})
    sin_veta: frozenset["Material"] = frozenset()   # materiales lisos: sus piezas se pueden rotar

    @property
    def ancho_interior(self) -> Decimal:
        return self.ancho - 2 * self.espesor


@dataclass(frozen=True)
class Pieza:
    tipo: str                               # nombre del Tipo_Pieza
    cantidad: int
    medida_1: Decimal                       # sentido de la veta
    medida_2: Decimal | None                # None solo en listones
    material: Material
    cajon: int | None = None                # 1 = el de arriba; None = pieza del módulo
    con_veta: bool = True                   # False = color liso: rotable por menor desperdicio

    @property
    def medidas(self) -> tuple[Decimal, Decimal | None]:
        return self.medida_1, self.medida_2


@dataclass(frozen=True)
class Despiece:
    piezas: list[Pieza]
    altos_frentes_cajon: list[Decimal] = field(default_factory=list)
    alto_puertas: Decimal | None = None


def rotar(pieza: Pieza) -> Pieza:
    """Cambia el sentido de la veta: intercambia las medidas (RN-02.1). Un listón no se rota."""
    if pieza.medida_2 is None:
        return pieza
    return replace(pieza, medida_1=pieza.medida_2, medida_2=pieza.medida_1)


def redondear(valor: Decimal) -> Decimal:
    """Hacia abajo al milímetro (RN-03). Una pieza que sobra se corta; una que falta, no."""
    return valor.quantize(DECIMO, rounding=ROUND_FLOOR)


def _positiva(valor: Decimal, que: str) -> Decimal:
    valor = redondear(valor)
    if valor <= 0:
        raise ErrorDespiece(f"Con esas medidas, {que} queda en {valor} cm. Revisá las medidas y las luces.")
    return valor


# ---------- largo de la guía (4.4 d) ----------
def proponer_largo_guia(guia: TipoGuia, profundidad: Decimal, reglas: Reglas = Reglas()) -> Decimal | None:
    """La guía más larga que entra: largo + espacio adicional ≤ profundidad + tolerancia."""
    limite = profundidad + reglas.tolerancia_guia
    posibles = [largo for largo in guia.largos if largo + guia.espacio_adicional <= limite]
    return max(posibles) if posibles else None


# ---------- validación ----------
def validar(m: Modulo, reglas: Reglas = Reglas()) -> None:
    if min(m.ancho, m.alto, m.profundidad) <= 0:
        raise ErrorDespiece("Completá ancho, alto y profundidad del módulo.")
    if m.espesor <= 0 or 2 * m.espesor >= m.ancho:
        raise ErrorDespiece("Revisá el espesor de la placa de la estructura.")
    if m.estantes < 0 or m.puertas < 0:
        raise ErrorDespiece("La cantidad de estantes y de puertas no puede ser negativa.")
    if m.armado.es_cajonera:
        if not m.ancho_faja or m.ancho_faja <= 0:
            raise ErrorDespiece("Indicá el ancho de las fajas de la cajonera (habitualmente 10 o 12 cm).")
        if m.puertas or m.estantes or m.lleva_pinos:
            raise ErrorDespiece("Una cajonera no lleva puertas, estantes ni pinos.")
        if not m.cajones:
            raise ErrorDespiece("Una cajonera necesita al menos un cajón.")
    else:
        if m.ancho_faja is not None:
            raise ErrorDespiece("El ancho de faja es solo para cajoneras.")
        if m.lleva_pinos and m.lleva_techo:
            raise ErrorDespiece("Los pinos de apoyo son para bajo mesadas (módulos sin techo).")
    if m.luz_entre_frentes < 0:
        raise ErrorDespiece("La luz entre frentes no puede ser negativa.")
    if m.cajones and m.puertas and any(c.alto_frente is None for c in m.cajones):
        raise ErrorDespiece("Si el módulo tiene puertas, indicá el alto del frente de cada cajón: "
                            "las puertas ocupan el alto que queda.")
    for i, c in enumerate(m.cajones, 1):
        if c.alto_caja <= 0 or c.largo_guia <= 0:
            raise ErrorDespiece(f"Cajón {i}: completá el alto de la caja y el largo de la guía.")
        if c.alto_frente is not None and c.alto_frente <= 0:
            raise ErrorDespiece(f"Cajón {i}: el alto del frente tiene que ser mayor que cero.")
        if c.largo_guia + c.guia.espacio_adicional > m.profundidad + reglas.tolerancia_guia:
            raise ErrorDespiece(f"Cajón {i}: la guía de {c.largo_guia} cm no entra en un módulo de "
                                f"{m.profundidad} cm de profundidad.")


# ---------- cálculo ----------
def calcular_modulo(m: Modulo, reglas: Reglas = Reglas()) -> Despiece:
    validar(m, reglas)
    piezas = _estructura(m, reglas)
    altos_frentes, alto_puertas = _altos_de_frentes(m)
    for numero, (cajon, alto_frente) in enumerate(zip(m.cajones, altos_frentes), 1):
        if cajon.alto_caja > alto_frente:
            raise ErrorDespiece(f"Cajón {numero}: la caja ({cajon.alto_caja} cm) es más alta que su frente "
                                f"({alto_frente} cm). Bajá el alto de la caja.")
    piezas += _frentes(m, reglas, altos_frentes, alto_puertas)
    for numero, cajon in enumerate(m.cajones, 1):
        piezas += _caja_del_cajon(m, cajon, numero)
    # Sentido de la veta elegido al cargar el módulo y si el material es liso.
    piezas = [rotar(p) if p.tipo in m.rotar else p for p in piezas]
    piezas = [replace(p, con_veta=p.material not in m.sin_veta) for p in piezas]
    return Despiece(piezas, altos_frentes, alto_puertas)


def _estructura(m: Modulo, reglas: Reglas) -> list[Pieza]:
    A, H, P, e = m.ancho, m.alto, m.profundidad, m.espesor
    piezas: list[Pieza] = []
    if m.armado is Armado.MODULO:
        # Piso y techo enteros; laterales entre ellos (RN-04, 4.2).
        piezas.append(Pieza("Piso", 1, _positiva(A, "el piso"), _positiva(P, "el piso"), Material.ESTRUCTURA))
        if m.lleva_techo:
            piezas.append(Pieza("Techo", 1, redondear(A), redondear(P), Material.ESTRUCTURA))
        alto_lateral = H - 2 * e if m.lleva_techo else H - e
        piezas.append(Pieza("Lateral", 2, _positiva(alto_lateral, "el lateral"), redondear(P), Material.ESTRUCTURA))
        if m.estantes:
            piezas.append(Pieza("Estante", m.estantes, redondear(A - 2 * e), redondear(P), Material.ESTRUCTURA))
        if m.lleva_pinos:
            piezas.append(Pieza("Pino", 2, redondear(A - 2 * e), None, Material.LISTON))
    elif m.armado is Armado.CAJONERA_FAJAS_DE_LUZ:
        # Laterales enteros; las 4 fajas entre ellos.
        piezas.append(Pieza("Lateral", 2, redondear(H), redondear(P), Material.ESTRUCTURA))
        piezas.append(Pieza("Faja", 4, redondear(A - 2 * e), redondear(m.ancho_faja), Material.ESTRUCTURA))
    else:
        # Fajas enteras; los laterales entre ellas.
        piezas.append(Pieza("Lateral", 2, _positiva(H - 2 * e, "el lateral"), redondear(P), Material.ESTRUCTURA))
        piezas.append(Pieza("Faja", 4, redondear(A), redondear(m.ancho_faja), Material.ESTRUCTURA))
    if m.lleva_fondo:
        # 0,3 menos que el módulo en ancho y alto (30 × 30 → 29,7 × 29,7); veta vertical por defecto.
        d = reglas.descuento_fondo
        piezas.append(Pieza("Fondo", 1, _positiva(H - d, "el fondo"), _positiva(A - d, "el fondo"), Material.FONDO))
    return piezas


def _altos_de_frentes(m: Modulo) -> tuple[list[Decimal], Decimal | None]:
    """Altos de los frentes de cajón y de las puertas (4.3 y 4.4 c).

    Espacio para frentes = alto − luz superior − luz inferior. Con puertas, cada cajón
    tiene su alto de frente y las puertas ocupan lo que queda. Sin puertas, los
    cajones sin alto definido se reparten en partes iguales lo que dejan los demás.
    """
    disponible = m.alto - m.luz_superior - m.luz_inferior
    cantidad = len(m.cajones)
    if not cantidad:
        return [], (_positiva(disponible, "la puerta") if m.puertas else None)
    if m.puertas:
        fijos = [c.alto_frente for c in m.cajones]
        alto_puertas = disponible - sum(fijos) - cantidad * m.luz_entre_frentes
        return [redondear(a) for a in fijos], _positiva(alto_puertas, "el alto de las puertas")
    espacio = disponible - (cantidad - 1) * m.luz_entre_frentes
    fijos = [c.alto_frente for c in m.cajones if c.alto_frente is not None]
    libres = cantidad - len(fijos)
    resto = espacio - sum(fijos)
    if libres == 0:
        if abs(resto) >= DECIMO:
            raise ErrorDespiece(f"Los altos de los frentes no completan el espacio: sobran o faltan "
                                f"{redondear(resto)} cm. Dejá algún cajón sin alto para que se reparta.")
        return [redondear(a) for a in fijos], None
    parte = _positiva(resto / libres, "el frente de cajón")
    return [redondear(c.alto_frente) if c.alto_frente is not None else parte for c in m.cajones], None


def _frentes(m: Modulo, reglas: Reglas, altos_cajones: list[Decimal], alto_puertas: Decimal | None) -> list[Pieza]:
    piezas = []
    ancho_frente = _positiva(m.ancho - 2 * reglas.luz_lateral, "el frente")
    for numero, alto in enumerate(altos_cajones, 1):
        # Frente de cajón: veta horizontal → ancho primero (59,4 × 16,2).
        piezas.append(Pieza("Frente de cajón", 1, ancho_frente, alto, Material.FRENTES, numero))
    if m.puertas:
        n = m.puertas
        ancho = _positiva((m.ancho - 2 * reglas.luz_lateral - (n - 1) * reglas.luz_entre_puertas) / n, "la puerta")
        # Puerta: veta vertical → alto primero (59,2 × 44,5).
        piezas.append(Pieza("Puerta", n, alto_puertas, ancho, Material.FRENTES))
    return piezas


def _caja_del_cajon(m: Modulo, cajon: Cajon, numero: int) -> list[Pieza]:
    """Piezas de la caja según las reglas de la guía (Pieza_Guia): referencia − descuento."""
    guia = cajon.guia
    if not guia.piezas:
        raise ErrorDespiece(f"La guía «{guia.nombre}» no tiene piezas cargadas.")
    # Guía lateral oculta (sin laterales propios) a la que todavía no se le cargó el contrafrente.
    nombres = {p.pieza for p in guia.piezas}
    if "Contrafrente de cajón" not in nombres and "Lateral de cajón" not in nombres:
        raise ErrorDespiece(f"Falta el alto del contrafrente de la guía «{guia.nombre}» (dato de la marca). "
                            "Cargalo en Materiales › Guías.")
    piezas = []
    for regla in guia.piezas:
        medidas = []
        if regla.descuento_ancho is not None:
            medidas.append(m.ancho_interior - regla.descuento_ancho)
        if regla.descuento_largo is not None:
            medidas.append(cajon.largo_guia - regla.descuento_largo)
        if regla.alto_fijo is not None:
            medidas.append(regla.alto_fijo)
        elif regla.descuento_alto is not None:
            medidas.append(cajon.alto_caja - regla.descuento_alto)
        if len(medidas) != 2:
            raise ErrorDespiece(f"La regla de «{regla.pieza}» en la guía «{guia.nombre}» está incompleta.")
        material = Material.PISO_CAJON if regla.pieza == "Piso de cajón" else Material.CAJONES
        piezas.append(Pieza(regla.pieza, regla.cantidad, _positiva(medidas[0], regla.pieza.lower()),
                            _positiva(medidas[1], regla.pieza.lower()), material, numero))
    return piezas


# ---------- zócalo (4.4 bis) ----------
def proponer_zocalo(largo_tramo: Decimal, profundidad_tramo: Decimal,
                    reglas: Reglas = Reglas()) -> tuple[Decimal, Decimal]:
    """Largo completo del tramo (si un costado queda libre, lo descuenta el usuario) y
    profundidad con el retiro del frente: 180 × 55 → 180 × 53,5."""
    return redondear(largo_tramo), redondear(profundidad_tramo - reglas.retiro_zocalo)


def calcular_zocalo(largo: Decimal, alto: Decimal, profundidad: Decimal, refuerzos: int = 0,
                    espesor: Decimal = Decimal("1.8")) -> list[Pieza]:
    """Marco: frente y trasera enteros; laterales y refuerzos entre ellos."""
    if min(largo, alto, profundidad) <= 0:
        raise ErrorDespiece("Completá largo, alto y profundidad del zócalo.")
    if refuerzos < 0:
        raise ErrorDespiece("La cantidad de refuerzos no puede ser negativa.")
    interior = _positiva(profundidad - 2 * espesor, "el lateral del zócalo")
    piezas = [
        Pieza("Frente de zócalo", 1, redondear(largo), redondear(alto), Material.ZOCALO),
        Pieza("Trasera de zócalo", 1, redondear(largo), redondear(alto), Material.ZOCALO_OCULTO),
        Pieza("Lateral de zócalo", 2, interior, redondear(alto), Material.ZOCALO),
    ]
    if refuerzos:
        piezas.append(Pieza("Refuerzo de zócalo", refuerzos, interior, redondear(alto), Material.ZOCALO_OCULTO))
    return piezas


# ---------- medida de corte (RN-03.1, 4.5) ----------
def medida_de_corte(medida_1: Decimal, medida_2: Decimal | None, descuento: Decimal, superior: bool = False,
                    inferior: bool = False, izquierdo: bool = False,
                    derecho: bool = False) -> tuple[Decimal, Decimal | None]:
    """Resta el filo de cada canto que lo lleva. La pieza se dibuja con la medida 1 en
    horizontal: izquierdo y derecho acortan la medida 1; superior e inferior, la 2."""
    corte_1 = medida_1 - descuento * (int(izquierdo) + int(derecho))
    corte_2 = None if medida_2 is None else medida_2 - descuento * (int(superior) + int(inferior))
    return corte_1, corte_2
