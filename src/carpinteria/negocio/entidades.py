"""Entidades del negocio: datos puros, sin lógica de base de datos ni de interfaz."""
from dataclasses import dataclass
from datetime import datetime


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
    fecha_alta: datetime


@dataclass(frozen=True)
class ObraConTrabajos:
    obra: Obra
    trabajos: list[TrabajoResumen]


@dataclass(frozen=True)
class FichaCliente:
    cliente: Cliente
    obras: list[ObraConTrabajos]
