"""Entidades del negocio: datos puros, sin lógica de base de datos ni de interfaz."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Usuario:
    id: int
    nombre_usuario: str
    nombre_completo: str
    hash_contrasena: str
    debe_cambiar_contrasena: bool
    es_activo: bool
    intentos_fallidos: int
    bloqueado_hasta: datetime | None
    ultimo_ingreso: datetime | None

    def esta_bloqueado(self, ahora: datetime) -> bool:
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > ahora


@dataclass(frozen=True)
class Sesion:
    """Resultado de un ingreso correcto."""
    usuario: Usuario
    ultimo_ingreso_anterior: datetime | None   # para el aviso RF-03.7
    intentos_fallidos_desde_entonces: int
    debe_cambiar_contrasena: bool


@dataclass(frozen=True)
class EventoAuditoria:
    fecha_hora: datetime
    codigo: str
    descripcion: str
    es_critico: bool
    usuario: str | None          # nombre completo de quien lo hizo (si se sabe)
    usuario_ingresado: str | None
    detalle: str | None
    equipo: str | None


@dataclass(frozen=True)
class TipoEvento:
    codigo: str
    descripcion: str
    es_critico: bool


# ---------- Clientes y obras ----------
@dataclass(frozen=True)
class Cliente:
    id: int | None
    nombre: str
    apellido: str
    telefono: str
    email: str | None = None
    observaciones: str | None = None
    es_activo: bool = True

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"


@dataclass(frozen=True)
class Obra:
    id: int | None
    id_cliente: int | None
    direccion: str
    localidad: str
    alias: str | None = None
    observaciones: str | None = None

    @property
    def titulo(self) -> str:
        """Cómo se muestra la obra: el alias si tiene, si no la dirección."""
        return self.alias or self.direccion


@dataclass(frozen=True)
class ClienteResumen:
    """Fila del listado de clientes."""
    cliente: Cliente
    cantidad_obras: int
    primera_direccion: str | None


@dataclass(frozen=True)
class TrabajoResumen:
    id: int
    descripcion: str
    estado: str
    fecha_presupuesto: date


@dataclass(frozen=True)
class ObraConTrabajos:
    obra: Obra
    trabajos: list[TrabajoResumen]


@dataclass(frozen=True)
class FichaCliente:
    cliente: Cliente
    obras: list[ObraConTrabajos]


# ---------- trabajos (RF-12 y RF-25 a RF-28) ----------
@dataclass(frozen=True)
class EstadoTrabajo:
    id: int
    nombre: str
    orden: int


@dataclass(frozen=True)
class Trabajo:
    id: int | None
    id_obra: int
    id_estado: int
    descripcion: str
    monto_total: Decimal | None = None
    monto_sena: Decimal | None = None
    fecha_alta: datetime | None = None
    fecha_cobro_sena: date | None = None
    fecha_comienzo: date | None = None
    fecha_finalizacion: date | None = None
    fecha_entrega: date | None = None
    fecha_cobro_saldo: date | None = None
    observaciones: str | None = None
    fecha_presupuesto: date | None = None   # editable; fecha_alta es cuándo se cargó
    entrega_aproximada: bool = False         # True: de la entrega pactada solo se sabe la semana

    @property
    def saldo(self) -> Decimal | None:
        """El saldo no se guarda: se calcula como total − seña (RF-26)."""
        if self.monto_total is None:
            return None
        return self.monto_total - (self.monto_sena or Decimal(0))

    @property
    def cobrado(self) -> Decimal:
        total = Decimal(0)
        if self.fecha_cobro_sena and self.monto_sena:
            total += self.monto_sena
        if self.fecha_cobro_saldo and self.saldo:
            total += self.saldo
        return total

    @property
    def pendiente_de_cobro(self) -> Decimal:
        if self.monto_total is None:
            return Decimal(0)
        return self.monto_total - self.cobrado


@dataclass(frozen=True)
class DetalleTrabajo:
    """Un trabajo con su estado, su obra y su cliente (para listados y detalle)."""
    trabajo: Trabajo
    estado: EstadoTrabajo
    obra: Obra
    cliente: Cliente


# ---------- inicio ----------
@dataclass(frozen=True)
class Alerta:
    """Algo para resolver que se muestra en el inicio."""
    titulo: str
    detalle: str
    id_trabajo: int | None = None
    urgente: bool = False


@dataclass(frozen=True)
class ResumenInicio:
    en_produccion: int
    entregas_proximas: list[DetalleTrabajo]
    por_cobrar: Decimal
    trabajos_por_cobrar: int
    presupuestos_sin_confirmar: int
    dias_presupuesto_mas_antiguo: int | None
    en_curso: list[DetalleTrabajo]
    alertas: list[Alerta]


# ---------- catálogo de materiales (M3) ----------
@dataclass(frozen=True)
class MarcaPlaca:
    id: int | None
    nombre: str
    es_activo: bool = True


@dataclass(frozen=True)
class ColorPlaca:
    id: int | None
    id_marca: int
    nombre: str | None
    codigo: str | None
    tiene_veta: bool = False
    es_activo: bool = True
    marca: str = ""   # nombre de la marca (solo para mostrar)
    marca_activa: bool = True

    @property
    def descripcion(self) -> str:
        """"Blanco Nieve (BN-01)", o solo el que tenga."""
        if self.nombre and self.codigo:
            return f"{self.nombre} ({self.codigo})"
        return self.nombre or self.codigo or ""


@dataclass(frozen=True)
class Placa:
    id: int | None
    id_color: int
    espesor: Decimal          # cm (1,8 = 18 mm)
    largo: Decimal            # cm, en el sentido de la veta
    ancho: Decimal            # cm
    es_activo: bool = True
    color: ColorPlaca | None = None   # solo para mostrar
    en_uso: bool = False      # la usa algún trabajo o retazo: no se borra ni se cambian sus medidas

    @property
    def espesor_mm(self) -> Decimal:
        return (self.espesor * 10).normalize()


@dataclass(frozen=True)
class Liston:
    id: int | None
    nombre: str
    ancho_pulgadas: Decimal
    alto_pulgadas: Decimal
    es_activo: bool = True
    en_uso: bool = False


# ---------- catálogo, parte 2: filos, lacas, frentes y guías ----------
@dataclass(frozen=True)
class TipoFilo:
    id: int | None
    nombre: str
    espesor_mm: Decimal
    descuento_cm: Decimal      # se resta por cada canto con filo en la medida de corte
    en_uso: bool = False


@dataclass(frozen=True)
class MarcaPintura:
    id: int | None
    nombre: str
    es_activo: bool = True


@dataclass(frozen=True)
class ColorLaca:
    id: int | None
    id_marca: int
    nombre: str | None
    codigo: str | None
    es_activo: bool = True
    marca: str = ""
    marca_activa: bool = True
    en_uso: bool = False

    @property
    def descripcion(self) -> str:
        if self.nombre and self.codigo:
            return f"{self.nombre} ({self.codigo})"
        return self.nombre or self.codigo or ""


@dataclass(frozen=True)
class TerminacionLaca:
    id: int | None
    nombre: str
    es_activo: bool = True
    en_uso: bool = False


@dataclass(frozen=True)
class EstiloFrente:
    id: int | None
    nombre: str
    luz_superior: Decimal      # cm; negativa = el frente sobresale
    luz_inferior: Decimal
    luz_entre_frentes: Decimal
    descripcion: str | None = None
    es_activo: bool = True
    en_uso: bool = False


@dataclass(frozen=True)
class PiezaGuia:
    """Una pieza que lleva el cajón con esa guía: medida = referencia − descuento."""
    id_tipo_pieza: int
    pieza: str
    cantidad: int
    descuento_ancho: Decimal | None = None   # respecto del ancho interior del módulo
    descuento_largo: Decimal | None = None   # respecto del largo de la guía
    descuento_alto: Decimal | None = None    # respecto del alto del cajón
    alto_fijo: Decimal | None = None         # alto definido por la marca (contrafrente de guía oculta)


@dataclass(frozen=True)
class TipoGuia:
    id: int | None
    nombre: str
    marca: str | None = None
    espacio_adicional: Decimal = Decimal(0)
    es_activo: bool = True
    en_uso: bool = False
    largos: tuple[Decimal, ...] = ()
    piezas: tuple[PiezaGuia, ...] = ()


# ---------- muebles, módulos y piezas guardados (M4) ----------
@dataclass(frozen=True)
class Mueble:
    id: int | None
    id_trabajo: int
    nombre: str
    observaciones: str | None = None


@dataclass(frozen=True)
class CajonGuardado:
    id: int | None
    id_guia: int
    id_placa_piso: int
    alto_caja: Decimal
    largo_guia: Decimal
    alto_frente: Decimal | None = None


@dataclass(frozen=True)
class ModuloGuardado:
    """Un módulo tal como se guarda: medidas, opciones y materiales (ids del catálogo)."""
    id: int | None
    id_mueble: int
    armado: str                       # nombre del Tipo_Armado (ver despiece.Armado)
    id_placa: int                     # estructura
    ancho: Decimal
    alto: Decimal
    profundidad: Decimal
    nombre: str | None = None
    id_estilo: int | None = None
    id_placa_frentes: int | None = None
    id_placa_cajones: int | None = None
    id_placa_fondo: int | None = None      # None = sin fondo
    id_liston: int | None = None           # None = sin pinos
    id_color_laca: int | None = None       # frentes laqueados
    id_terminacion: int | None = None
    lleva_techo: bool = True
    ancho_faja: Decimal | None = None
    estantes: int = 0
    puertas: int = 0
    luz_superior: Decimal = Decimal(0)
    luz_inferior: Decimal = Decimal(0)
    luz_entre_frentes: Decimal = Decimal(0)
    cajones: tuple[CajonGuardado, ...] = ()
    rotar: frozenset[str] = frozenset()    # tipos de pieza con la veta rotada
    luz_izquierda: Decimal = Decimal("0.3")   # costados de puertas y frentes; 0,15 junto a otro módulo
    luz_derecha: Decimal = Decimal("0.3")
    cantidad: int = 1                      # módulos iguales: se cargan una vez y se multiplican las piezas


@dataclass(frozen=True)
class ZocaloGuardado:
    id: int | None
    id_mueble: int
    id_placa: int
    largo: Decimal
    alto: Decimal
    profundidad: Decimal
    refuerzos: int = 0
    id_placa_oculta: int | None = None
    descripcion: str | None = None


@dataclass(frozen=True)
class Cantos:
    """Cantos con filo. La pieza se dibuja con la medida 1 en horizontal: superior e
    inferior son paralelos a la veta; izquierdo y derecho, los de la medida 2."""
    superior: bool = False
    inferior: bool = False
    izquierdo: bool = False
    derecho: bool = False

    @property
    def cantidad(self) -> int:
        return sum((self.superior, self.inferior, self.izquierdo, self.derecho))

    def rotados(self) -> "Cantos":
        return Cantos(self.izquierdo, self.derecho, self.superior, self.inferior)


@dataclass(frozen=True)
class PiezaGuardada:
    id: int | None
    tipo: str                         # nombre del Tipo_Pieza
    id_material: int
    cantidad: int
    medida_1: Decimal                 # final, sentido de la veta
    medida_2: Decimal | None
    id_mueble: int | None = None      # dueño: exactamente uno de los cuatro
    id_modulo: int | None = None
    id_cajon: int | None = None
    id_zocalo: int | None = None
    orden_cajon: int | None = None    # al generar, a qué cajón del módulo pertenece (antes de tener id)
    id_tipo_filo: int | None = None   # None = filo SIN DEFINIR
    cantos: Cantos = Cantos()
    id_color_filo: int | None = None  # None = mismo color que la pieza
    id_color_laca: int | None = None
    id_terminacion: int | None = None
    descripcion: str | None = None
    editada: bool = False
    veces: int = 1                    # cantidad de módulos iguales del dueño (solo lectura)

    @property
    def total(self) -> int:
        """Piezas a cortar: la cantidad de la fila por la cantidad de módulos iguales."""
        return self.cantidad * self.veces
