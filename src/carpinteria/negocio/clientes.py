"""Clientes y obras (RF-04 a RF-07).

- Alta, modificación, baja lógica y consulta de clientes.
- Cada cliente tiene una o más obras (casas o inmuebles). La primera obra se
  puede cargar junto con el cliente, en una sola operación.
- Búsqueda flexible: varias palabras, fragmentos, sin distinguir mayúsculas ni
  tildes; por nombre, apellido, teléfono, email o dirección de sus obras.
- Ficha del cliente: sus obras con el historial de trabajos de cada una.
"""
import re
from dataclasses import replace

from carpinteria.negocio.autenticacion import ErrorAutenticacion
from carpinteria.negocio.entidades import Cliente, ClienteResumen, FichaCliente, Obra, ObraConTrabajos
from carpinteria.negocio.puertos import RepositorioClientes, RepositorioObras

MAXIMO_TERMINOS = 5
LARGO_MAXIMO_TERMINO = 50
LIMITE_RESULTADOS = 100
_PATRON_TELEFONO = re.compile(r"[0-9+()\- ]{6,25}")
_PATRON_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class ErrorClientes(ErrorAutenticacion):
    """Error de validación de clientes u obras; se muestra tal cual."""


def _limpiar(texto: str | None) -> str:
    return " ".join((texto or "").split())


def _opcional(texto: str | None) -> str | None:
    return _limpiar(texto) or None


def solo_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def terminos_de_busqueda(texto: str) -> list[str]:
    """Divide lo escrito en palabras (máximo 5, de hasta 50 letras) para buscar cada una.

    El tope evita consultas desmedidas si alguien pega un texto enorme.
    """
    limpio = _limpiar(texto)
    return [t[:LARGO_MAXIMO_TERMINO] for t in limpio.split(" ")[:MAXIMO_TERMINOS]] if limpio else []


def _requerido(valor: str, campo: str, maximo: int) -> str:
    if not valor:
        raise ErrorClientes(f"Completá {campo}.")
    if len(valor) > maximo:
        raise ErrorClientes(f"{campo[0].upper() + campo[1:]} puede tener hasta {maximo} caracteres.")
    return valor


def _maximo(valor: str | None, campo: str, maximo: int) -> str | None:
    if valor and len(valor) > maximo:
        raise ErrorClientes(f"{campo[0].upper() + campo[1:]} puede tener hasta {maximo} caracteres.")
    return valor


def validar_cliente(cliente: Cliente) -> Cliente:
    nombre = _requerido(_limpiar(cliente.nombre), "el nombre", 50)
    apellido = _requerido(_limpiar(cliente.apellido), "el apellido", 50)
    telefono = _limpiar(cliente.telefono)
    if not _PATRON_TELEFONO.fullmatch(telefono) or len(solo_digitos(telefono)) < 6:
        raise ErrorClientes("Revisá el teléfono: solo números, espacios, guiones, + o paréntesis "
                            "(al menos 6 números).")
    email = _opcional(cliente.email)
    if email and (len(email) > 100 or not _PATRON_EMAIL.fullmatch(email)):
        raise ErrorClientes("Revisá el email (por ejemplo: nombre@gmail.com).")
    observaciones = _maximo(_opcional(cliente.observaciones), "las observaciones", 500)
    return replace(cliente, nombre=nombre, apellido=apellido, telefono=telefono,
                   email=email.lower() if email else None, observaciones=observaciones)


def validar_obra(obra: Obra) -> Obra:
    return replace(
        obra,
        direccion=_requerido(_limpiar(obra.direccion), "la dirección", 150),
        localidad=_requerido(_limpiar(obra.localidad), "la localidad", 80),
        alias=_maximo(_opcional(obra.alias), "el alias", 100),
        observaciones=_maximo(_opcional(obra.observaciones), "las observaciones", 500),
    )


class ServicioClientes:
    def __init__(self, clientes: RepositorioClientes, obras: RepositorioObras) -> None:
        self._clientes = clientes
        self._obras = obras

    # ---------- consulta ----------
    def buscar(self, texto: str = "", incluir_inactivos: bool = False) -> list[ClienteResumen]:
        return self._clientes.buscar(terminos_de_busqueda(texto), incluir_inactivos, LIMITE_RESULTADOS)

    def ficha(self, id_cliente: int) -> FichaCliente:
        cliente = self._clientes.obtener(id_cliente)
        if cliente is None:
            raise ErrorClientes("El cliente ya no existe.")
        obras = [ObraConTrabajos(o, self._obras.trabajos_de_la_obra(o.id))
                 for o in self._obras.listar_por_cliente(id_cliente)]
        return FichaCliente(cliente, obras)

    # ---------- clientes ----------
    def crear(self, cliente: Cliente, obra_inicial: Obra | None = None) -> int:
        cliente = validar_cliente(cliente)
        self._controlar_telefono_repetido(cliente)
        if obra_inicial is not None:
            obra_inicial = validar_obra(obra_inicial)
        return self._clientes.crear(cliente, obra_inicial)

    def actualizar(self, cliente: Cliente) -> None:
        if cliente.id is None:
            raise ErrorClientes("Falta indicar qué cliente se modifica.")
        cliente = validar_cliente(cliente)
        self._controlar_telefono_repetido(cliente)
        self._clientes.actualizar(cliente)

    def dar_de_baja(self, id_cliente: int) -> None:
        self._clientes.cambiar_estado(id_cliente, False)

    def reactivar(self, id_cliente: int) -> None:
        self._clientes.cambiar_estado(id_cliente, True)

    def _controlar_telefono_repetido(self, cliente: Cliente) -> None:
        """Evita cargar dos veces al mismo cliente (el teléfono lo identifica en la práctica)."""
        for otro in self._clientes.buscar_por_telefono(solo_digitos(cliente.telefono)):
            if otro.id != cliente.id:
                raise ErrorClientes(f"Ya existe un cliente con ese teléfono: {otro.nombre_completo}"
                                    + ("" if otro.es_activo else " (dado de baja)") + ".")

    # ---------- obras ----------
    def agregar_obra(self, obra: Obra) -> int:
        if obra.id_cliente is None:
            raise ErrorClientes("Falta indicar el cliente de la obra.")
        obra = validar_obra(obra)
        self._controlar_obra_repetida(obra)
        return self._obras.crear(obra)

    def actualizar_obra(self, obra: Obra) -> None:
        if obra.id is None:
            raise ErrorClientes("Falta indicar qué obra se modifica.")
        obra = validar_obra(obra)
        self._controlar_obra_repetida(obra)
        self._obras.actualizar(obra)

    def _controlar_obra_repetida(self, obra: Obra) -> None:
        if self._obras.existe(obra.id_cliente, obra.direccion, obra.localidad, obra.id):
            raise ErrorClientes("Este cliente ya tiene una obra en esa dirección y localidad.")
