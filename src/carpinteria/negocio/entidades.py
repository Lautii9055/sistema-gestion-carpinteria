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
