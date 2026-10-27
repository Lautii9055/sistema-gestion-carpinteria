"""Consulta del registro de auditoría (RF-03.6). Solo lectura."""
from collections.abc import Callable
from datetime import datetime, timedelta

from carpinteria.negocio.entidades import EventoAuditoria, TipoEvento
from carpinteria.negocio.puertos import RepositorioAuditoria

# Períodos que ofrece la pantalla: nombre visible -> días hacia atrás (None = todo).
PERIODOS: dict[str, int | None] = {
    "Hoy": 0,
    "Últimos 7 días": 7,
    "Últimos 30 días": 30,
    "Todo": None,
}


class ServicioAuditoria:
    def __init__(self, auditoria: RepositorioAuditoria,
                 reloj: Callable[[], datetime] = datetime.now) -> None:
        self._auditoria = auditoria
        self._reloj = reloj

    def tipos_de_evento(self) -> list[TipoEvento]:
        return self._auditoria.tipos_de_evento()

    def consultar(self, periodo: str = "Últimos 7 días", id_usuario: int | None = None,
                  codigo_evento: str | None = None, solo_criticos: bool = False) -> list[EventoAuditoria]:
        dias = PERIODOS.get(periodo)
        desde = None
        if dias is not None:
            hoy = self._reloj().replace(hour=0, minute=0, second=0, microsecond=0)
            desde = hoy - timedelta(days=dias)
        return self._auditoria.listar(desde=desde, id_usuario=id_usuario,
                                      codigo_evento=codigo_evento, solo_criticos=solo_criticos)
