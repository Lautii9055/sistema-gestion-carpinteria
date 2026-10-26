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
