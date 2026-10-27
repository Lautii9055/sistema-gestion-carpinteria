"""Resumen del inicio (diseño 2): qué hay en el taller y qué hay que resolver.

Todo se calcula a partir de los trabajos activos (los que no están cobrados ni
cancelados), así el inicio no necesita datos propios.
"""
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal

from carpinteria.negocio.entidades import Alerta, DetalleTrabajo, ResumenInicio
from carpinteria.negocio.puertos import RepositorioTrabajos
from carpinteria.negocio.trabajos import (CANCELADO, COBRADO, EN_PRODUCCION, INSTALADO, PRESUPUESTADO,
                                          formato_pesos, inicio_de_semana, limite_de_entrega, texto_entrega)

DIAS_ENTREGAS_PROXIMAS = 7
DIAS_PRESUPUESTO_SIN_RESPUESTA = 15   # después de esto, se sugiere llamar al cliente
MAXIMO_ACTIVOS = 500
MAXIMO_EN_CURSO = 8


def _orden_en_curso(d: DetalleTrabajo):
    """Primero lo que tiene entrega más cercana; después, lo más avanzado."""
    entrega = limite_de_entrega(d.trabajo) if d.estado.nombre != INSTALADO else None
    return (entrega is None, entrega or date.max, -d.estado.orden, d.trabajo.id)


def _cuando(fecha: date, hoy: date) -> str:
    dias = (fecha - hoy).days
    if dias == 0:
        return "hoy"
    if dias == 1:
        return "mañana"
    return f"el {fecha:%d/%m}"


class ServicioInicio:
    def __init__(self, trabajos: RepositorioTrabajos, hoy: Callable[[], date] = date.today) -> None:
        self._trabajos = trabajos
        self._hoy = hoy

    def resumen(self) -> ResumenInicio:
        hoy = self._hoy()
        activos = self._trabajos.activos((COBRADO, CANCELADO), MAXIMO_ACTIVOS)
        sin_instalar = [d for d in activos if d.estado.nombre not in (PRESUPUESTADO, INSTALADO)]
        hasta = hoy + timedelta(days=DIAS_ENTREGAS_PROXIMAS - 1)

        def proxima(d: DetalleTrabajo) -> bool:
            t = d.trabajo
            if not t.fecha_entrega:
                return False
            desde = inicio_de_semana(t.fecha_entrega) if t.entrega_aproximada else t.fecha_entrega
            return desde <= hasta and limite_de_entrega(t) >= hoy

        entregas = sorted((d for d in sin_instalar if proxima(d)), key=lambda d: limite_de_entrega(d.trabajo))

        con_deuda = [d for d in activos if d.estado.nombre != PRESUPUESTADO and d.trabajo.pendiente_de_cobro > 0]
        presupuestos = [d for d in activos if d.estado.nombre == PRESUPUESTADO]
        mas_antiguo = min((d.trabajo.fecha_presupuesto for d in presupuestos if d.trabajo.fecha_presupuesto),
                          default=None)

        return ResumenInicio(
            en_produccion=sum(1 for d in activos if d.estado.nombre == EN_PRODUCCION),
            entregas_proximas=entregas,
            por_cobrar=sum((d.trabajo.pendiente_de_cobro for d in con_deuda), Decimal(0)),
            trabajos_por_cobrar=len(con_deuda),
            presupuestos_sin_confirmar=len(presupuestos),
            dias_presupuesto_mas_antiguo=(hoy - mas_antiguo).days if mas_antiguo else None,
            en_curso=sorted(activos, key=_orden_en_curso)[:MAXIMO_EN_CURSO],
            alertas=self._alertas(activos, hoy),
        )

    @staticmethod
    def _alertas(activos: list[DetalleTrabajo], hoy: date) -> list[Alerta]:
        alertas: list[Alerta] = []
        for d in activos:
            t, estado, nombre = d.trabajo, d.estado.nombre, f"{d.trabajo.descripcion} ({d.cliente.apellido})"
            limite = limite_de_entrega(t)
            if estado not in (PRESUPUESTADO, INSTALADO) and limite and limite < hoy:
                pactada = (f"la entrega era la {texto_entrega(t).lower()}" if t.entrega_aproximada
                           else f"la entrega era el {t.fecha_entrega:%d/%m}")
                alertas.append(Alerta("Entrega atrasada", f"{nombre}: {pactada} y está «{estado.lower()}».",
                                      t.id, urgente=True))
            if estado == INSTALADO and t.saldo and not t.fecha_cobro_saldo:
                alertas.append(Alerta("Saldo por cobrar",
                                      f"{nombre}: instalado, falta cobrar {formato_pesos(t.pendiente_de_cobro)}.",
                                      t.id, urgente=True))
            if estado != PRESUPUESTADO and t.monto_sena and not t.fecha_cobro_sena:
                alertas.append(Alerta("Seña pendiente",
                                      f"{nombre}: «{estado.lower()}» sin seña cobrada.", t.id))
            if estado != PRESUPUESTADO and t.monto_total is None:
                alertas.append(Alerta("Sin monto", f"{nombre}: «{estado.lower()}» y todavía sin monto total.",
                                      t.id))
            if estado == PRESUPUESTADO and t.fecha_presupuesto and \
                    (hoy - t.fecha_presupuesto).days > DIAS_PRESUPUESTO_SIN_RESPUESTA:
                alertas.append(Alerta("Presupuesto sin respuesta",
                                      f"{nombre}: presupuestado hace {(hoy - t.fecha_presupuesto).days} días. "
                                      "¿Llamar al cliente?", t.id))
        alertas.sort(key=lambda a: not a.urgente)   # lo urgente primero, sin perder el orden
        return alertas


def texto_entregas(entregas: list[DetalleTrabajo], hoy: date) -> str:
    if not entregas:
        return "sin entregas pactadas"
    dias = []
    for d in entregas:
        t = d.trabajo
        texto = (f"sem. {inicio_de_semana(t.fecha_entrega):%d/%m}" if t.entrega_aproximada
                 else _cuando(t.fecha_entrega, hoy))
        if texto not in dias:
            dias.append(texto)
    return ", ".join(dias[:3]) + ("…" if len(dias) > 3 else "")

