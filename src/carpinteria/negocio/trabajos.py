"""Trabajos: alta, estados, montos y fechas (RF-12 y RF-25 a RF-28).

- Un trabajo pertenece a una obra (y por ella, a un cliente). Nace
  "Presupuestado" y avanza por los estados del taller; también se puede cancelar.
- El saldo no se guarda: es total − seña. La seña se sugiere como un porcentaje
  del total (parámetro porcentaje_sena, 60% por defecto).
- Los estados avanzan de a uno, en orden. Para corregir un error se vuelve un
  paso atrás (y se borra la fecha de ese paso). Se puede cancelar en cualquier
  momento antes de cobrado y retomar después.
- Cobrar no es un paso de la fabricación: la seña y el saldo se pueden
  registrar cuando ocurren (por ejemplo, el cliente paga todo al confirmar) y el
  trabajo sigue su curso. Cobrar la seña de un trabajo presupuestado lo confirma.
- Al cambiar de estado se sugiere la fecha que corresponde (RF-26.3) y las
  fechas se validan para que sean coherentes (RF-26.2).
- Los cambios de monto, de estado y las eliminaciones quedan en la auditoría.
"""
import re
import socket
from collections.abc import Callable
from dataclasses import replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from carpinteria.negocio.autenticacion import ErrorAutenticacion
from carpinteria.negocio.clientes import LIMITE_RESULTADOS, terminos_de_busqueda
from carpinteria.negocio.entidades import DetalleTrabajo, EstadoTrabajo, Sesion, Trabajo
from carpinteria.negocio.puertos import (RepositorioAuditoria, RepositorioClientes, RepositorioObras,
                                         RepositorioParametros, RepositorioTrabajos)

from carpinteria.negocio.estados import (CANCELADO, COBRADO, CONFIRMADO, EN_PRODUCCION,  # noqa: F401
                                         INSTALADO, PRESUPUESTADO, TERMINADO)

ESTADOS_SIN_COBRO = (PRESUPUESTADO, CANCELADO)   # todavía no (o ya no) se debe nada
ESTADOS_QUE_SE_PUEDEN_ELIMINAR = (PRESUPUESTADO, CANCELADO)

# Qué fecha se sugiere completar al pasar a cada estado (RF-26.3).
FECHA_DEL_ESTADO = {
    CONFIRMADO: "fecha_cobro_sena",
    EN_PRODUCCION: "fecha_comienzo",
    TERMINADO: "fecha_finalizacion",
    INSTALADO: "fecha_entrega",
    COBRADO: "fecha_cobro_saldo",
}
NOMBRE_DE_FECHA = {
    "fecha_cobro_sena": "Cobro de la seña",
    "fecha_comienzo": "Comienzo",
    "fecha_finalizacion": "Finalización",
    "fecha_entrega": "Entrega",
    "fecha_cobro_saldo": "Cobro del saldo",
}
CAMPOS_DE_FECHA = tuple(NOMBRE_DE_FECHA)
# Fechas de fabricación: se borran al volver un paso atrás. Las de cobro no,
# porque registran pagos reales.
FECHAS_DE_FABRICACION = ("fecha_comienzo", "fecha_finalizacion", "fecha_entrega")
# La fecha de presupuesto se puede cargar en el pasado (trabajos anotados tarde),
# nunca en el futuro ni antes de este límite (evita errores de tipeo como 2002).
FECHA_PRESUPUESTO = "fecha_presupuesto"
PRESUPUESTO_MAS_ANTIGUO = date(2010, 1, 1)

PERIODOS = {"Todos": None, "Últimos 30 días": 30, "Últimos 3 meses": 90, "Último año": 365}
PORCENTAJE_SENA_POR_DEFECTO = Decimal(60)
MONTO_MAXIMO = Decimal("9999999999.99")   # DECIMAL(12,2) en la base
_MILES = re.compile(r"\d{1,3}(\.\d{3})+")
_FECHA = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2}|\d{4})")


class ErrorTrabajos(ErrorAutenticacion):
    """Error de validación de trabajos; se muestra tal cual."""


# ---------- montos y fechas escritos por el usuario ----------
def leer_monto(texto: str | None, campo: str = "el monto") -> Decimal | None:
    """Interpreta montos como se escriben acá: "2.800.000", "2800000", "1.250,50", "$ 900"."""
    limpio = (texto or "").replace("$", "").replace(" ", "").strip()
    if not limpio:
        return None
    if "," in limpio:                       # coma decimal: los puntos son de miles
        limpio = limpio.replace(".", "").replace(",", ".")
    elif _MILES.fullmatch(limpio):          # "2.800.000"
        limpio = limpio.replace(".", "")
    try:
        monto = Decimal(limpio)
    except InvalidOperation:
        raise ErrorTrabajos(f"Revisá {campo}: escribí solo números (por ejemplo: 2.800.000).") from None
    if not monto.is_finite() or monto < 0:
        raise ErrorTrabajos(f"Revisá {campo}: no puede ser negativo.")
    if monto != monto.quantize(Decimal("0.01")):
        raise ErrorTrabajos(f"Revisá {campo}: como máximo dos decimales.")
    if monto > MONTO_MAXIMO:
        raise ErrorTrabajos(f"Revisá {campo}: es demasiado grande.")
    return monto.quantize(Decimal("0.01"))


def formatear_al_escribir(texto: str | None) -> str:
    """Pone los puntos de miles mientras se escribe: "12000000" → "12.000.000".

    Los decimales van con coma ("1.250,5"); un punto escrito se toma como de miles.
    """
    limpio = "".join(c for c in (texto or "") if c.isdigit() or c in ",.")
    entero, coma, decimales = limpio.partition(",")
    digitos = "".join(c for c in entero if c.isdigit()).lstrip("0") or ("0" if entero or coma else "")
    agrupado = f"{int(digitos):,}".replace(",", ".") if digitos else ""
    return agrupado + (("," + "".join(c for c in decimales if c.isdigit())[:2]) if coma else "")


def formato_pesos(monto: Decimal | None) -> str:
    if monto is None:
        return "—"
    entero, _, decimales = f"{monto:,.2f}".partition(".")
    entero = entero.replace(",", ".")
    return f"$ {entero}" + ("" if decimales == "00" else f",{decimales}")


def formatear_fecha_al_escribir(texto: str | None) -> str:
    """Agrega las barras mientras se escribe: "18112026" → "18/11/2026".

    Si la persona escribe sus propias barras con otro formato (ej.: "5/11/26"),
    se respeta lo que escribió.
    """
    texto = texto or ""
    digitos = "".join(c for c in texto if c.isdigit())[:8]
    barras_propias = [i for i, c in enumerate(texto) if not c.isdigit()]
    if any(i not in (2, 5) or texto[i] != "/" for i in barras_propias):
        return texto
    if len(digitos) > 4:
        return f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"
    if len(digitos) > 2:
        return f"{digitos[:2]}/{digitos[2:]}"
    return digitos


def leer_fecha(texto: str | None, campo: str = "la fecha") -> date | None:
    """Acepta dd/mm/aaaa, dd/mm/aa, con barras, guiones o puntos, o solo los números (ddmmaaaa)."""
    limpio = (texto or "").strip()
    if not limpio:
        return None
    if limpio.isdigit() and len(limpio) in (6, 8):
        limpio = f"{limpio[:2]}/{limpio[2:4]}/{limpio[4:]}"
    coincidencia = _FECHA.fullmatch(limpio)
    if coincidencia:
        dia, mes, anio = (int(x) for x in coincidencia.groups())
        if anio < 100:
            anio += 2000
        try:
            return date(anio, mes, dia)
        except ValueError:
            pass
    raise ErrorTrabajos(f"Revisá {campo}: usá el formato dd/mm/aaaa (por ejemplo: 05/11/2026).")


def formato_fecha(fecha: date | None) -> str:
    return f"{fecha:%d/%m/%Y}" if fecha else ""


# ---------- entrega pactada ----------
_DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def inicio_de_semana(fecha: date) -> date:
    return fecha - timedelta(days=fecha.weekday())


def limite_de_entrega(t: Trabajo) -> date | None:
    """Último día aceptable: el pactado o, si se pactó la semana, su domingo."""
    if not t.fecha_entrega:
        return None
    return inicio_de_semana(t.fecha_entrega) + timedelta(days=6) if t.entrega_aproximada else t.fecha_entrega


def texto_entrega(t: Trabajo) -> str:
    if not t.fecha_entrega:
        return ""
    if t.entrega_aproximada:
        return f"Semana del {inicio_de_semana(t.fecha_entrega):%d/%m}"
    return f"{_DIAS_CORTOS[t.fecha_entrega.weekday()]} {t.fecha_entrega:%d/%m}"


# ---------- validación ----------
def _texto(valor: str | None) -> str | None:
    return " ".join((valor or "").split()) or None


def validar_trabajo(trabajo: Trabajo, hoy: date, estado: EstadoTrabajo | None = None,
                    alcanzados: tuple[str, ...] = ()) -> Trabajo:
    """Valida datos, montos y fechas. alcanzados: estados por los que ya pasó."""
    descripcion = _texto(trabajo.descripcion)
    if not descripcion:
        raise ErrorTrabajos("Completá la descripción del trabajo (por ejemplo: Cocina completa).")
    if len(descripcion) > 200:
        raise ErrorTrabajos("La descripción puede tener hasta 200 caracteres.")
    observaciones = (trabajo.observaciones or "").strip() or None
    if observaciones and len(observaciones) > 500:
        raise ErrorTrabajos("Las observaciones pueden tener hasta 500 caracteres.")

    total, sena = trabajo.monto_total, trabajo.monto_sena
    for monto in (total, sena):
        if monto is not None and (monto < 0 or monto > MONTO_MAXIMO):
            raise ErrorTrabajos("Revisá los montos.")
    if sena is not None and total is None:
        raise ErrorTrabajos("Para cargar la seña, cargá primero el monto total.")
    if sena is not None and sena > total:
        raise ErrorTrabajos("La seña no puede ser mayor que el monto total.")

    t = trabajo
    if t.entrega_aproximada and not t.fecha_entrega:
        t = trabajo = replace(t, entrega_aproximada=False)
    presupuesto = t.fecha_presupuesto or (t.fecha_alta.date() if t.fecha_alta else None)
    if presupuesto and presupuesto > hoy:
        raise ErrorTrabajos("La fecha de presupuesto no puede ser futura.")
    if presupuesto and presupuesto < PRESUPUESTO_MAS_ANTIGUO:
        raise ErrorTrabajos(f"Revisá la fecha de presupuesto: no puede ser anterior al "
                            f"{PRESUPUESTO_MAS_ANTIGUO:%d/%m/%Y}.")
    for campo in CAMPOS_DE_FECHA:
        fecha = getattr(t, campo)
        if presupuesto and fecha and fecha < presupuesto:
            raise ErrorTrabajos(f"{NOMBRE_DE_FECHA[campo]}: no puede ser anterior al presupuesto "
                                f"({presupuesto:%d/%m/%Y}).")
    # Una fecha real (de un paso ya hecho, o un cobro) seguida de una prevista que
    # quedó atrás (ej.: entrega pactada para antes de terminar) no es un error:
    # el trabajo viene demorado. Entre dos reales o dos previstas, sí se exige el orden.
    def real(campo: str) -> bool:
        if estado is None or campo in ("fecha_cobro_sena", "fecha_cobro_saldo"):
            return True
        return next(e for e, c in FECHA_DEL_ESTADO.items() if c == campo) in alcanzados

    def orden(antes: str, despues: str, mensaje: str) -> None:
        if real(antes) and not real(despues):
            return
        _orden(getattr(t, antes), getattr(t, despues), mensaje)

    orden("fecha_cobro_sena", "fecha_comienzo", "El comienzo no puede ser anterior a la confirmación "
                                                "(cobro de la seña).")
    orden("fecha_comienzo", "fecha_finalizacion", "La finalización no puede ser anterior al comienzo.")
    orden("fecha_finalizacion", "fecha_entrega", "La entrega no puede ser anterior a la finalización.")
    orden("fecha_comienzo", "fecha_entrega", "La entrega no puede ser anterior al comienzo.")
    _orden(t.fecha_cobro_sena, t.fecha_cobro_saldo, "El cobro del saldo no puede ser anterior al de la seña.")
    for campo in ("fecha_cobro_sena", "fecha_cobro_saldo"):
        fecha = getattr(t, campo)
        if fecha and fecha > hoy:
            raise ErrorTrabajos(f"{NOMBRE_DE_FECHA[campo]}: no puede ser una fecha futura.")
    if t.fecha_cobro_sena and not sena:
        raise ErrorTrabajos("Hay fecha de cobro de la seña pero no hay monto de seña.")
    # Lo que ya pasó no puede tener fecha futura; lo que falta, sí (fecha prevista).
    for nombre in alcanzados:
        campo = FECHA_DEL_ESTADO.get(nombre)
        fecha = getattr(t, campo) if campo else None
        if fecha and fecha > hoy:
            raise ErrorTrabajos(f"{NOMBRE_DE_FECHA[campo]}: el trabajo ya está «{nombre.lower()}», "
                                "así que la fecha no puede ser futura.")
    return replace(trabajo, descripcion=descripcion, observaciones=observaciones)


def _orden(antes: date | None, despues: date | None, mensaje: str) -> None:
    if antes and despues and despues < antes:
        raise ErrorTrabajos(mensaje)


# ---------- servicio ----------
class ServicioTrabajos:
    def __init__(self, trabajos: RepositorioTrabajos, clientes: RepositorioClientes,
                 obras: RepositorioObras, auditoria: RepositorioAuditoria,
                 parametros: RepositorioParametros, hoy: Callable[[], date] = date.today,
                 equipo: str | None = None) -> None:
        self._trabajos = trabajos
        self._clientes = clientes
        self._obras = obras
        self._auditoria = auditoria
        self._parametros = parametros
        self._hoy = hoy
        self._equipo = equipo or socket.gethostname()
        self._estados: list[EstadoTrabajo] | None = None

    # ---------- estados ----------
    def estados(self) -> list[EstadoTrabajo]:
        if self._estados is None:  # no cambian mientras el sistema está abierto
            self._estados = sorted(self._trabajos.estados(), key=lambda e: e.orden)
        return self._estados

    def estado_por_nombre(self, nombre: str) -> EstadoTrabajo:
        return next(e for e in self.estados() if e.nombre == nombre)

    def recorrido(self) -> list[EstadoTrabajo]:
        """Los estados del camino normal, sin Cancelado (para dibujar el avance)."""
        return [e for e in self.estados() if e.nombre != CANCELADO]

    def _vecino(self, actual: EstadoTrabajo, paso: int) -> EstadoTrabajo | None:
        if actual.nombre == CANCELADO:
            return None
        camino = self.recorrido()
        posicion = next(i for i, e in enumerate(camino) if e.id == actual.id) + paso
        return camino[posicion] if 0 <= posicion < len(camino) else None

    def estado_siguiente(self, actual: EstadoTrabajo) -> EstadoTrabajo | None:
        return self._vecino(actual, +1)

    def estado_anterior(self, actual: EstadoTrabajo) -> EstadoTrabajo | None:
        return self._vecino(actual, -1)

    def puede_cancelarse(self, actual: EstadoTrabajo) -> bool:
        return actual.nombre not in (CANCELADO, COBRADO)

    def alcanzados(self, actual: EstadoTrabajo) -> tuple[str, ...]:
        """Estados por los que ya pasó el trabajo (incluido el actual)."""
        if actual.nombre == CANCELADO:
            return ()
        return tuple(e.nombre for e in self.recorrido() if e.orden <= actual.orden)

    def estado_para_retomar(self, trabajo: Trabajo) -> EstadoTrabajo:
        """Al retomar un trabajo cancelado: el último estado que muestran sus fechas."""
        candidato = self.estado_por_nombre(PRESUPUESTADO)
        for e in self.recorrido():
            campo = FECHA_DEL_ESTADO.get(e.nombre)
            if e.nombre != COBRADO and campo and getattr(trabajo, campo):
                candidato = e
        return candidato

    @staticmethod
    def fecha_sugerida(estado: EstadoTrabajo) -> str | None:
        """Campo de fecha a completar al pasar a ese estado (o None)."""
        return FECHA_DEL_ESTADO.get(estado.nombre)

    # ---------- seña ----------
    def porcentaje_sena(self) -> Decimal:
        valor = self._parametros.obtener("porcentaje_sena")
        return Decimal(valor) if valor is not None else PORCENTAJE_SENA_POR_DEFECTO

    def sena_sugerida(self, total: Decimal) -> Decimal:
        """Seña sugerida, redondeada a pesos enteros (RF-27)."""
        return (total * self.porcentaje_sena() / 100).quantize(Decimal(1), ROUND_HALF_UP)

    # ---------- consulta ----------
    def buscar(self, texto: str = "", id_estado: int | None = None, solo_por_cobrar: bool = False,
               periodo: str = "Todos") -> list[DetalleTrabajo]:
        dias = PERIODOS.get(periodo)
        desde = self._hoy() - timedelta(days=dias) if dias else None
        terminos = terminos_de_busqueda(texto)
        # Los trabajos de clientes dados de baja no aparecen en el listado general,
        # pero sí cuando se los busca (ej.: por el nombre del cliente).
        return self._trabajos.buscar(terminos, id_estado, solo_por_cobrar, desde, LIMITE_RESULTADOS,
                                     incluir_clientes_inactivos=bool(terminos))

    def detalle(self, id_trabajo: int) -> DetalleTrabajo:
        detalle = self._trabajos.obtener(id_trabajo)
        if detalle is None:
            raise ErrorTrabajos("El trabajo ya no existe.")
        return detalle

    # ---------- alta y modificación ----------
    def crear(self, sesion: Sesion, id_obra: int | None, descripcion: str,
              monto_total: Decimal | None = None, monto_sena: Decimal | None = None,
              observaciones: str | None = None, fecha_presupuesto: date | None = None,
              entrega: date | None = None, entrega_aproximada: bool = False) -> int:
        """fecha_presupuesto: hoy si no se indica; puede ser pasada (trabajo anotado tarde).
        entrega: entrega pactada (opcional), un día o solo la semana."""
        if id_obra is None:
            raise ErrorTrabajos("Elegí la obra del trabajo.")
        obra = self._obras.obtener(id_obra)
        if obra is None:
            raise ErrorTrabajos("La obra ya no existe.")
        cliente = self._clientes.obtener(obra.id_cliente)
        if cliente is None or not cliente.es_activo:
            raise ErrorTrabajos("El cliente está dado de baja: reactivalo para cargarle trabajos.")
        hoy = self._hoy()
        fecha_presupuesto = fecha_presupuesto or hoy
        trabajo = validar_trabajo(Trabajo(None, id_obra, self.estado_por_nombre(PRESUPUESTADO).id,
                                          descripcion, monto_total, monto_sena,
                                          observaciones=observaciones, fecha_entrega=entrega,
                                          fecha_presupuesto=fecha_presupuesto,
                                          entrega_aproximada=bool(entrega and entrega_aproximada)), hoy)
        nuevo = self._trabajos.crear(trabajo)
        if fecha_presupuesto != hoy:
            self._auditar("CAMBIO_FECHA_PRESUPUESTO", sesion, nuevo,
                          f"Cargado el {hoy:%d/%m/%Y} con fecha de presupuesto {fecha_presupuesto:%d/%m/%Y}")
        if monto_total is not None:
            self._auditar("CAMBIO_MONTO", sesion, nuevo,
                          f"Alta con total {formato_pesos(monto_total)}, seña {formato_pesos(monto_sena)}")
        return nuevo

    def actualizar_datos(self, sesion: Sesion, id_trabajo: int, descripcion: str,
                         observaciones: str | None) -> None:
        actual = self._editable(id_trabajo).trabajo
        self._guardar(replace(actual, descripcion=descripcion, observaciones=observaciones))

    def actualizar_pagos(self, sesion: Sesion, id_trabajo: int, monto_total: Decimal | None,
                         monto_sena: Decimal | None, fechas: dict[str, date | None]) -> None:
        """Montos, las cinco fechas (RF-26 y RF-26.1) y la fecha de presupuesto."""
        desconocidas = set(fechas) - set(CAMPOS_DE_FECHA) - {FECHA_PRESUPUESTO}
        if desconocidas:
            raise ValueError(f"Campos de fecha desconocidos: {desconocidas}")
        if FECHA_PRESUPUESTO in fechas and fechas[FECHA_PRESUPUESTO] is None:
            raise ErrorTrabajos("Completá la fecha de presupuesto.")
        actual = self._editable(id_trabajo).trabajo
        nuevo = self._guardar(replace(actual, monto_total=monto_total, monto_sena=monto_sena, **fechas))
        cambios = []
        if actual.monto_total != nuevo.monto_total:
            cambios.append(f"Total: {formato_pesos(actual.monto_total)} → {formato_pesos(nuevo.monto_total)}")
        if actual.monto_sena != nuevo.monto_sena:
            cambios.append(f"Seña: {formato_pesos(actual.monto_sena)} → {formato_pesos(nuevo.monto_sena)}")
        if cambios:
            self._auditar("CAMBIO_MONTO", sesion, id_trabajo, "; ".join(cambios))
        if FECHA_PRESUPUESTO in fechas and nuevo.fecha_presupuesto != actual.fecha_presupuesto:
            self._auditar("CAMBIO_FECHA_PRESUPUESTO", sesion, id_trabajo,
                          f"Presupuesto: {formato_fecha(actual.fecha_presupuesto)} → "
                          f"{formato_fecha(nuevo.fecha_presupuesto)}")

    def registrar_cobro(self, sesion: Sesion, id_trabajo: int, campo: str, fecha: date) -> bool:
        """Registra el cobro de la seña o del saldo cuando ocurre.

        Cobrar la seña de un trabajo presupuestado lo confirma (devuelve True si
        cambió de estado). El saldo se puede cobrar por adelantado desde que el
        trabajo está confirmado; el trabajo sigue su curso normal.
        """
        if campo not in ("fecha_cobro_sena", "fecha_cobro_saldo"):
            raise ValueError(campo)
        detalle = self._editable(id_trabajo)
        estado = detalle.estado.nombre
        if estado == CANCELADO:
            raise ErrorTrabajos("El trabajo está cancelado: retomalo para registrar cobros.")
        if fecha is None:
            raise ErrorTrabajos("Indicá la fecha del cobro.")
        if campo == "fecha_cobro_saldo" and estado == PRESUPUESTADO:
            raise ErrorTrabajos("Primero confirmá el trabajo (registrando el cobro de la seña).")
        if campo == "fecha_cobro_sena" and estado == PRESUPUESTADO:
            self.cambiar_estado(sesion, id_trabajo, self.estado_por_nombre(CONFIRMADO).id, fecha)
            return True
        self._guardar(replace(detalle.trabajo, **{campo: fecha}))
        return False

    def cambiar_estado(self, sesion: Sesion, id_trabajo: int, id_estado: int,
                       fecha: date | None = None) -> None:
        """Avanza un paso (completando la fecha que corresponde), vuelve un paso
        atrás (borrando la fecha de fabricación de ese paso), cancela o retoma."""
        detalle = self._editable(id_trabajo)
        actual = detalle.estado
        nuevo = next((e for e in self.estados() if e.id == id_estado), None)
        if nuevo is None:
            raise ErrorTrabajos("El estado elegido no existe.")
        if nuevo.id == actual.id:
            return
        t = detalle.trabajo
        cambios: dict = {"id_estado": nuevo.id}

        if nuevo == self.estado_siguiente(actual):
            campo = self.fecha_sugerida(nuevo)
            if campo and fecha is not None:
                cambios[campo] = fecha
            if nuevo.nombre == INSTALADO:
                cambios["entrega_aproximada"] = False   # desde ahora es la fecha real
            if nuevo.nombre == COBRADO:
                self._controlar_cobro_total(replace(t, **cambios))
        elif nuevo == self.estado_anterior(actual):
            campo = self.fecha_sugerida(actual)
            if actual.nombre == CONFIRMADO and t.fecha_cobro_sena:
                raise ErrorTrabajos("La seña figura cobrada: para volver a presupuestado, primero quitá "
                                    "la fecha de cobro de la seña en «Editar montos y fechas».")
            if campo in FECHAS_DE_FABRICACION:
                cambios[campo] = None
        elif nuevo.nombre == CANCELADO:
            if not self.puede_cancelarse(actual):
                raise ErrorTrabajos("Un trabajo cobrado no se puede cancelar.")
        elif actual.nombre == CANCELADO:
            if nuevo.nombre == COBRADO:
                raise ErrorTrabajos("Al retomar, el trabajo vuelve al estado en que estaba.")
        else:
            raise ErrorTrabajos("Los estados avanzan de a uno. Para corregir, volvé un paso atrás.")

        self._guardar(replace(t, **cambios))
        self._auditar("CAMBIO_ESTADO_TRABAJO", sesion, id_trabajo, f"{actual.nombre} → {nuevo.nombre}")

    def pactar_entrega(self, sesion: Sesion, id_trabajo: int, fecha: date | None, aproximada: bool) -> None:
        """Entrega pactada con el cliente: un día, o solo la semana (aproximada=True).

        Se puede cambiar hasta que el trabajo se instala; ahí pasa a ser la fecha real.
        """
        detalle = self._editable(id_trabajo)
        if detalle.estado.nombre in (INSTALADO, COBRADO):
            raise ErrorTrabajos("El trabajo ya está instalado: la fecha de entrega es la real "
                                "(se corrige en «Editar montos y fechas»).")
        if detalle.estado.nombre == CANCELADO:
            raise ErrorTrabajos("El trabajo está cancelado.")
        self._guardar(replace(detalle.trabajo, fecha_entrega=fecha, entrega_aproximada=bool(fecha and aproximada)))

    @staticmethod
    def _controlar_cobro_total(t: Trabajo) -> None:
        if t.monto_sena and not t.fecha_cobro_sena:
            raise ErrorTrabajos("Falta registrar el cobro de la seña.")
        if t.saldo and not t.fecha_cobro_saldo:
            raise ErrorTrabajos("Indicá la fecha de cobro del saldo.")

    def eliminar(self, sesion: Sesion, id_trabajo: int) -> None:
        """Solo se eliminan trabajos presupuestados o cancelados: los demás tienen
        compromisos o cobros y se conservan (a lo sumo, se cancelan)."""
        detalle = self._editable(id_trabajo)
        if detalle.estado.nombre not in ESTADOS_QUE_SE_PUEDEN_ELIMINAR:
            raise ErrorTrabajos("Solo se pueden eliminar trabajos presupuestados o cancelados. "
                                "Si no se va a hacer, cancelalo.")
        self._trabajos.eliminar(id_trabajo)
        self._auditar("ELIMINACION_TRABAJO", sesion, id_trabajo,
                      f"#{id_trabajo} {detalle.trabajo.descripcion} ({detalle.cliente.nombre_completo}, "
                      f"{detalle.estado.nombre})")

    # ---------- auxiliares ----------
    def _editable(self, id_trabajo: int) -> DetalleTrabajo:
        """Los trabajos de un cliente dado de baja quedan como historial: no se modifican."""
        detalle = self.detalle(id_trabajo)
        if not detalle.cliente.es_activo:
            raise ErrorTrabajos("El cliente está dado de baja: el trabajo queda como historial. "
                                "Reactivá al cliente para modificarlo.")
        return detalle

    def _guardar(self, trabajo: Trabajo) -> Trabajo:
        estado = next(e for e in self.estados() if e.id == trabajo.id_estado)
        trabajo = validar_trabajo(trabajo, self._hoy(), estado, self.alcanzados(estado))
        self._trabajos.actualizar(trabajo)
        return trabajo

    def _auditar(self, codigo: str, sesion: Sesion, id_trabajo: int, detalle: str) -> None:
        self._auditoria.registrar(codigo, id_usuario=sesion.usuario.id, entidad="Trabajo",
                                  id_entidad=id_trabajo, detalle=detalle[:500], equipo=self._equipo)
