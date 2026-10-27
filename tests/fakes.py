"""Repositorios en memoria para probar la lógica de negocio sin base de datos."""
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from carpinteria.negocio.entidades import EventoAuditoria, TipoEvento, Usuario

AHORA = datetime(2026, 10, 26, 18, 0)

TIPOS = {
    "LOGIN_OK": ("Ingreso correcto", False),
    "LOGIN_FALLIDO": ("Contraseña o usuario incorrecto", False),
    "USUARIO_BLOQUEADO": ("Usuario bloqueado por intentos fallidos", True),
    "LOGOUT": ("Cierre de sesión", False),
    "CIERRE_INACTIVIDAD": ("Sesión cerrada por inactividad", False),
    "CAMBIO_CONTRASENA": ("Cambio de la propia contraseña", False),
    "BLANQUEO_CONTRASENA": ("Contraseña blanqueada por otro usuario", True),
    "ALTA_USUARIO": ("Alta de usuario", True),
    "BAJA_USUARIO": ("Baja de usuario", True),
    "REACTIVACION_USUARIO": ("Reactivación de usuario", True),
}


class UsuariosEnMemoria:
    def __init__(self, *usuarios: Usuario) -> None:
        self.por_id = {u.id: u for u in usuarios}

    def buscar_por_nombre(self, nombre):
        return next((u for u in self.por_id.values()
                     if u.nombre_usuario.casefold() == nombre.casefold()), None)

    def buscar_por_id(self, id_usuario):
        return self.por_id.get(id_usuario)

    def registrar_fallo(self, id_usuario, intentos, bloqueado_hasta):
        self._cambiar(id_usuario, intentos_fallidos=intentos, bloqueado_hasta=bloqueado_hasta)

    def registrar_ingreso_exitoso(self, id_usuario, fecha):
        self._cambiar(id_usuario, intentos_fallidos=0, bloqueado_hasta=None, ultimo_ingreso=fecha)

    def cambiar_contrasena(self, id_usuario, hash_contrasena, fecha):
        self._cambiar(id_usuario, hash_contrasena=hash_contrasena, debe_cambiar_contrasena=False)

    def listar(self):
        return list(self.por_id.values())

    def crear(self, nombre_usuario, nombre_completo, hash_contrasena):
        nuevo_id = max(self.por_id, default=0) + 1
        self.por_id[nuevo_id] = Usuario(nuevo_id, nombre_usuario, nombre_completo, hash_contrasena,
                                        True, True, 0, None, None)
        return nuevo_id

    def asignar_contrasena_provisoria(self, id_usuario, hash_contrasena):
        self._cambiar(id_usuario, hash_contrasena=hash_contrasena, debe_cambiar_contrasena=True,
                      intentos_fallidos=0, bloqueado_hasta=None)

    def cambiar_estado(self, id_usuario, activo):
        self._cambiar(id_usuario, es_activo=activo)

    def _cambiar(self, id_usuario, **cambios):
        self.por_id[id_usuario] = replace(self.por_id[id_usuario], **cambios)


class AuditoriaEnMemoria:
    def __init__(self, reloj=lambda: AHORA) -> None:
        self.eventos = []
        self._reloj = reloj

    def registrar(self, codigo_evento, **datos):
        self.eventos.append((self._reloj(), codigo_evento, datos))

    def contar_ingresos_fallidos(self, id_usuario, desde):
        return sum(1 for fecha, codigo, d in self.eventos
                   if codigo == "LOGIN_FALLIDO" and d.get("id_usuario") == id_usuario
                   and (desde is None or fecha > desde))

    def listar(self, *, desde=None, id_usuario=None, codigo_evento=None, solo_criticos=False,
               limite=500):
        resultado = []
        for fecha, codigo, d in reversed(self.eventos):
            descripcion, critico = TIPOS.get(codigo, (codigo, False))
            if ((desde is None or fecha >= desde)
                    and (id_usuario is None or d.get("id_usuario") == id_usuario)
                    and (codigo_evento is None or codigo == codigo_evento)
                    and (not solo_criticos or critico)):
                resultado.append(EventoAuditoria(fecha, codigo, descripcion, critico, None,
                                                 d.get("usuario_ingresado"), d.get("detalle"),
                                                 d.get("equipo")))
        return resultado[:limite]

    def tipos_de_evento(self):
        return [TipoEvento(c, d, k) for c, (d, k) in TIPOS.items()]

    def codigos(self):
        return [codigo for _, codigo, _ in self.eventos]


class ParametrosEnMemoria:
    valores = {"max_intentos_login": Decimal(5), "minutos_bloqueo": Decimal(15),
               "porcentaje_sena": Decimal("60.0"),
               "largo_minimo_contrasena": Decimal(10), "minutos_inactividad": Decimal(15)}

    def obtener(self, clave):
        return self.valores.get(clave)


class Reloj:
    def __init__(self, ahora: datetime = AHORA) -> None:
        self.ahora = ahora

    def __call__(self):
        return self.ahora


def _sin_tildes(texto: str) -> str:
    """Imita la collation de la base (Modern_Spanish_CI_AI): sin mayúsculas ni tildes."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", texto or "")
                   if unicodedata.category(c) != "Mn").casefold()


class ObrasEnMemoria:
    def __init__(self) -> None:
        self.por_id = {}
        self.trabajos = {}  # id_obra -> lista de TrabajoResumen

    def listar_por_cliente(self, id_cliente):
        return [o for o in self.por_id.values() if o.id_cliente == id_cliente]

    def obtener(self, id_obra):
        return self.por_id.get(id_obra)

    def existe(self, id_cliente, direccion, localidad, excluir_id):
        return any(o.id_cliente == id_cliente and _sin_tildes(o.direccion) == _sin_tildes(direccion)
                   and _sin_tildes(o.localidad) == _sin_tildes(localidad) and o.id != excluir_id
                   for o in self.por_id.values())

    def crear(self, obra):
        nuevo = max(self.por_id, default=0) + 1
        self.por_id[nuevo] = replace(obra, id=nuevo)
        return nuevo

    def actualizar(self, obra):
        self.por_id[obra.id] = obra

    def trabajos_de_la_obra(self, id_obra):
        return self.trabajos.get(id_obra, [])


class ClientesEnMemoria:
    def __init__(self, obras: ObrasEnMemoria) -> None:
        self.por_id = {}
        self.obras = obras
        self.ultimo_limite = None

    def _coincide(self, cliente, termino):
        t = _sin_tildes(termino)
        textos = [cliente.nombre, cliente.apellido, cliente.email or ""]
        for o in self.obras.listar_por_cliente(cliente.id):
            textos += [o.direccion, o.localidad, o.alias or ""]
        digitos = "".join(c for c in termino if c.isdigit())
        tel = "".join(c for c in cliente.telefono if c.isdigit())
        return (any(t in _sin_tildes(x) for x in textos)
                or (len(digitos) >= 3 and digitos in tel) or termino == str(cliente.id))

    def buscar(self, terminos, incluir_inactivos, limite):
        from carpinteria.negocio.entidades import ClienteResumen
        self.ultimo_limite = limite
        encontrados = [c for c in self.por_id.values()
                       if (incluir_inactivos or c.es_activo) and all(self._coincide(c, t) for t in terminos)]
        encontrados.sort(key=lambda c: (not c.es_activo, c.apellido, c.nombre))
        resultado = []
        for c in encontrados[:limite]:
            obras = self.obras.listar_por_cliente(c.id)
            resultado.append(ClienteResumen(c, len(obras),
                                            f"{obras[0].direccion}, {obras[0].localidad}" if obras else None))
        return resultado

    def obtener(self, id_cliente):
        return self.por_id.get(id_cliente)

    def buscar_por_telefono(self, digitos):
        return [c for c in self.por_id.values()
                if "".join(ch for ch in c.telefono if ch.isdigit()) == digitos]

    def crear(self, cliente, obra_inicial):
        nuevo = max(self.por_id, default=0) + 1
        self.por_id[nuevo] = replace(cliente, id=nuevo)
        if obra_inicial is not None:
            self.obras.crear(replace(obra_inicial, id_cliente=nuevo))
        return nuevo

    def actualizar(self, cliente):
        self.por_id[cliente.id] = cliente

    def cambiar_estado(self, id_cliente, activo):
        self.por_id[id_cliente] = replace(self.por_id[id_cliente], es_activo=activo)


ESTADOS = ["Presupuestado", "Confirmado", "En producción", "Terminado", "Instalado", "Cobrado",
           "Cancelado"]


class TrabajosEnMemoria:
    def __init__(self, clientes: "ClientesEnMemoria", obras: ObrasEnMemoria, reloj=lambda: AHORA) -> None:
        from carpinteria.negocio.entidades import EstadoTrabajo
        self.por_id = {}
        self.clientes = clientes
        self.obras = obras
        self._reloj = reloj
        self._estados = [EstadoTrabajo(i + 1, n, i + 1) for i, n in enumerate(ESTADOS)]
        self.ultimos_filtros = None

    def estados(self):
        return list(self._estados)

    def _detalle(self, t):
        from carpinteria.negocio.entidades import DetalleTrabajo
        obra = self.obras.por_id[t.id_obra]
        return DetalleTrabajo(t, next(e for e in self._estados if e.id == t.id_estado), obra,
                              self.clientes.por_id[obra.id_cliente])

    def buscar(self, terminos, id_estado, solo_por_cobrar, desde, limite):
        self.ultimos_filtros = (terminos, id_estado, solo_por_cobrar, desde, limite)
        resultado = []
        for t in sorted(self.por_id.values(), key=lambda t: (t.fecha_presupuesto, t.id), reverse=True):
            d = self._detalle(t)
            textos = [t.descripcion, d.cliente.nombre, d.cliente.apellido, d.obra.direccion,
                      d.obra.localidad, d.obra.alias or "", d.estado.nombre]
            if id_estado is not None and t.id_estado != id_estado:
                continue
            if desde is not None and t.fecha_presupuesto < desde:
                continue
            if solo_por_cobrar and (d.estado.nombre in ("Presupuestado", "Cancelado")
                                    or t.pendiente_de_cobro <= 0):
                continue
            if all(any(_sin_tildes(x) in _sin_tildes(c) for c in textos) or x == str(t.id)
                   for x in terminos):
                resultado.append(d)
        return resultado[:limite]

    def obtener(self, id_trabajo):
        t = self.por_id.get(id_trabajo)
        return self._detalle(t) if t else None

    def crear(self, trabajo):
        nuevo = max(self.por_id, default=0) + 1
        ahora = self._reloj()
        self.por_id[nuevo] = replace(trabajo, id=nuevo, fecha_alta=ahora,
                                     fecha_presupuesto=trabajo.fecha_presupuesto or ahora.date())
        return nuevo

    def actualizar(self, trabajo):
        self.por_id[trabajo.id] = trabajo

    def eliminar(self, id_trabajo):
        del self.por_id[id_trabajo]
