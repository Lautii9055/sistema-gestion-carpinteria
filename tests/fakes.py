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
        from carpinteria.negocio.entidades import TrabajoResumen
        reales = []
        repo = getattr(self, "repo_trabajos", None)
        if repo is not None:   # si hay trabajos en memoria, salen de ahí (como el JOIN de la base)
            reales = [TrabajoResumen(t.id, t.descripcion, repo._detalle(t).estado.nombre, t.fecha_presupuesto)
                      for t in repo.por_id.values() if t.id_obra == id_obra]
        return self.trabajos.get(id_obra, []) + reales


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
        obras.repo_trabajos = self

    def estados(self):
        return list(self._estados)

    def _detalle(self, t):
        from carpinteria.negocio.entidades import DetalleTrabajo
        obra = self.obras.por_id[t.id_obra]
        return DetalleTrabajo(t, next(e for e in self._estados if e.id == t.id_estado), obra,
                              self.clientes.por_id[obra.id_cliente])

    def buscar(self, terminos, id_estado, solo_por_cobrar, desde, limite, incluir_clientes_inactivos=False):
        self.ultimos_filtros = (terminos, id_estado, solo_por_cobrar, desde, limite)
        resultado = []
        for t in sorted(self.por_id.values(), key=lambda t: (t.fecha_presupuesto, t.id), reverse=True):
            d = self._detalle(t)
            textos = [t.descripcion, d.cliente.nombre, d.cliente.apellido, d.obra.direccion,
                      d.obra.localidad, d.obra.alias or "", d.estado.nombre]
            if id_estado is not None and t.id_estado != id_estado:
                continue
            if not incluir_clientes_inactivos and not d.cliente.es_activo:
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

    def activos(self, excluir_estados, limite):
        resultado = [self._detalle(t) for t in sorted(self.por_id.values(),
                                                      key=lambda t: (t.fecha_presupuesto, t.id))]
        return [d for d in resultado if d.estado.nombre not in excluir_estados][:limite]


class MaterialesEnMemoria:
    """Catálogo en memoria. en_uso_*: ids que "usa algún trabajo"."""
    def __init__(self) -> None:
        self.m, self.c, self.p, self.l = {}, {}, {}, {}
        self.placas_en_uso, self.colores_en_uso, self.listones_en_uso = set(), set(), set()
        self._siguiente_material = 100

    @staticmethod
    def _nuevo(d):
        return max(d, default=0) + 1

    def marcas(self):
        return list(self.m.values())

    def crear_marca(self, marca):
        i = self._nuevo(self.m); self.m[i] = replace(marca, id=i); return i

    def actualizar_marca(self, marca):
        self.m[marca.id] = marca

    def eliminar_marca(self, id_marca):
        del self.m[id_marca]

    def marca_en_uso(self, id_marca):
        return any(c.id_marca == id_marca for c in self.c.values())

    def colores(self):
        return [replace(c, marca=self.m[c.id_marca].nombre, marca_activa=self.m[c.id_marca].es_activo)
                for c in self.c.values()]

    def crear_color(self, color):
        i = self._nuevo(self.c); self.c[i] = replace(color, id=i); return i

    def actualizar_color(self, color):
        self.c[color.id] = color

    def eliminar_color(self, id_color):
        del self.c[id_color]

    def color_en_uso(self, id_color):
        return id_color in self.colores_en_uso or any(p.id_color == id_color for p in self.p.values())

    def placas(self):
        colores = {c.id: c for c in self.colores()}
        return [replace(p, color=colores[p.id_color], en_uso=p.id in self.placas_en_uso) for p in self.p.values()]

    def crear_placa(self, placa):
        self._siguiente_material += 1
        i = self._siguiente_material; self.p[i] = replace(placa, id=i); return i

    def actualizar_placa(self, placa):
        self.p[placa.id] = replace(placa, color=None, en_uso=False)

    def eliminar_placa(self, id_placa):
        del self.p[id_placa]

    def listones(self):
        return [replace(x, en_uso=x.id in self.listones_en_uso) for x in self.l.values()]

    def crear_liston(self, liston):
        self._siguiente_material += 1
        i = self._siguiente_material; self.l[i] = replace(liston, id=i); return i

    def actualizar_liston(self, liston):
        self.l[liston.id] = replace(liston, en_uso=False)

    def eliminar_liston(self, id_liston):
        del self.l[id_liston]


class CatalogoEnMemoria:
    """Filos, lacas, estilos y guías en memoria, con los datos iniciales de la base."""
    def __init__(self) -> None:
        from decimal import Decimal as D
        from carpinteria.negocio.entidades import (EstiloFrente, MarcaPintura, PiezaGuia, TerminacionLaca,
                                                  TipoFilo, TipoGuia)
        self.filos_ = {1: TipoFilo(1, "Sin filo", D("0.00"), D("0.00")), 2: TipoFilo(2, "0,45 mm", D("0.45"), D("0.00")),
                       3: TipoFilo(3, "2 mm", D("2.00"), D("0.20"))}
        self.marcas_ = {1: MarcaPintura(1, "Alba"), 2: MarcaPintura(2, "Sherwin Williams")}
        self.colores_ = {}
        self.terminaciones_ = {i: TerminacionLaca(i, n) for i, n in enumerate(["Mate", "Semimate", "Brillante"], 1)}
        self.estilos_ = {1: EstiloFrente(1, "Con tirador", D("0.4"), D("0.4"), D("0.3"))}
        self.tipos_pieza = {"Lateral de cajón": 10, "Contrafrente de cajón": 11, "Frente interno de cajón": 12,
                            "Piso de cajón": 13}
        tele = (PiezaGuia(10, "Lateral de cajón", 2, None, D("0.0"), D("0.0")),
                PiezaGuia(11, "Contrafrente de cajón", 1, D("6.3"), None, D("0.0")),
                PiezaGuia(12, "Frente interno de cajón", 1, D("6.3"), None, D("3.0")),
                PiezaGuia(13, "Piso de cajón", 1, D("3.0"), D("0.3"), None))
        oculta = (PiezaGuia(13, "Piso de cajón", 1, D("7.5"), D("0.9"), None),)
        self.guias_ = {1: TipoGuia(1, "Telescópica cierre suave", None, D("0.2"), piezas=tele),
                       2: TipoGuia(2, "Lateral oculto Eurohard", "Eurohard", D("0.8"), piezas=oculta)}
        self.en_uso = set()   # ("filo", id), ("color", id), ("guia", id), ...

    def _nuevo(self, d):
        return max(d, default=0) + 1

    def _uso(self, tipo, x):
        return replace(x, en_uso=(tipo, x.id) in self.en_uso)

    def _guardar(self, d, x):
        if x.id is None:
            x = replace(x, id=self._nuevo(d))
        d[x.id] = replace(x, en_uso=False) if hasattr(x, "en_uso") else x
        return x.id

    def filos(self): return [self._uso("filo", f) for f in self.filos_.values()]
    def guardar_filo(self, f): return self._guardar(self.filos_, f)
    def eliminar_filo(self, i): del self.filos_[i]
    def marcas_pintura(self): return list(self.marcas_.values())
    def guardar_marca_pintura(self, m): return self._guardar(self.marcas_, m)
    def eliminar_marca_pintura(self, i): del self.marcas_[i]

    def colores_laca(self):
        return [self._uso("color", replace(c, marca=self.marcas_[c.id_marca].nombre,
                                           marca_activa=self.marcas_[c.id_marca].es_activo))
                for c in self.colores_.values()]

    def guardar_color_laca(self, c): return self._guardar(self.colores_, c)
    def eliminar_color_laca(self, i): del self.colores_[i]
    def terminaciones(self): return [self._uso("terminacion", t) for t in self.terminaciones_.values()]
    def guardar_terminacion(self, t): return self._guardar(self.terminaciones_, t)
    def eliminar_terminacion(self, i): del self.terminaciones_[i]
    def estilos(self): return [self._uso("estilo", e) for e in self.estilos_.values()]
    def guardar_estilo(self, e): return self._guardar(self.estilos_, e)
    def eliminar_estilo(self, i): del self.estilos_[i]
    def guias(self): return [self._uso("guia", g) for g in self.guias_.values()]

    def guardar_guia(self, g):
        anterior = self.guias_.get(g.id)
        i = self._guardar(self.guias_, g)
        if anterior:   # los largos y las piezas no se tocan al editar los datos de la guía
            self.guias_[i] = replace(self.guias_[i], largos=anterior.largos, piezas=anterior.piezas)
        return i

    def eliminar_guia(self, i): del self.guias_[i]

    def copiar_piezas_guia(self, origen, destino):
        self.guias_[destino] = replace(self.guias_[destino], piezas=self.guias_[origen].piezas)

    def agregar_largo_guia(self, i, largo):
        self.guias_[i] = replace(self.guias_[i], largos=tuple(sorted(self.guias_[i].largos + (largo,))))

    def quitar_largo_guia(self, i, largo):
        self.guias_[i] = replace(self.guias_[i], largos=tuple(x for x in self.guias_[i].largos if x != largo))

    def guardar_pieza_guia(self, i, pieza):
        otras = tuple(p for p in self.guias_[i].piezas if p.id_tipo_pieza != pieza.id_tipo_pieza)
        self.guias_[i] = replace(self.guias_[i], piezas=otras + (pieza,))

    def id_tipo_pieza(self, nombre): return self.tipos_pieza.get(nombre)


class MueblesEnMemoria:
    def __init__(self) -> None:
        self.muebles_, self.modulos_, self.zocalos_, self.piezas_ = {}, {}, {}, {}
        self.cajones_ = {}   # id_cajon -> (id_modulo, orden)

    @staticmethod
    def _nuevo(d):
        return max(d, default=0) + 1

    def muebles(self, id_trabajo):
        return [m for m in self.muebles_.values() if m.id_trabajo == id_trabajo]

    def mueble(self, i):
        return self.muebles_.get(i)

    def guardar_mueble(self, m):
        i = m.id or self._nuevo(self.muebles_)
        self.muebles_[i] = replace(m, id=i)
        return i

    def eliminar_mueble(self, i):
        for mod in [x for x in self.modulos_.values() if x.id_mueble == i]:
            self.eliminar_modulo(mod.id)
        for z in [x for x in self.zocalos_.values() if x.id_mueble == i]:
            self.eliminar_zocalo(z.id)
        self._borrar_piezas(lambda p: p.id_mueble == i)
        del self.muebles_[i]

    def modulos(self, id_mueble):
        return [m for m in self.modulos_.values() if m.id_mueble == id_mueble]

    def modulo(self, i):
        return self.modulos_.get(i)

    def _borrar_piezas(self, condicion):
        for k in [k for k, p in self.piezas_.items() if condicion(p)]:
            del self.piezas_[k]

    def guardar_modulo(self, m, piezas_nuevas):
        i = m.id or self._nuevo(self.modulos_)
        self.modulos_[i] = replace(m, id=i)
        actuales = {orden: c for c, (mod, orden) in self.cajones_.items() if mod == i}
        for orden, id_cajon in list(actuales.items()):
            if orden > len(m.cajones):
                self._borrar_piezas(lambda p, c=id_cajon: p.id_cajon == c)
                del self.cajones_[id_cajon]
                del actuales[orden]
        for orden in range(1, len(m.cajones) + 1):
            if orden not in actuales:
                nuevo = self._nuevo(self.cajones_)
                self.cajones_[nuevo] = (i, orden)
                actuales[orden] = nuevo
        ids_cajones = set(actuales.values())
        self._borrar_piezas(lambda p: not p.editada and (p.id_modulo == i or p.id_cajon in ids_cajones))
        for p in piezas_nuevas:
            k = self._nuevo(self.piezas_)
            if p.orden_cajon:
                self.piezas_[k] = replace(p, id=k, id_modulo=None, id_cajon=actuales[p.orden_cajon])
            else:
                self.piezas_[k] = replace(p, id=k, id_modulo=i)
        return i

    def eliminar_modulo(self, i):
        ids = {c for c, (mod, _) in self.cajones_.items() if mod == i}
        self._borrar_piezas(lambda p: p.id_modulo == i or p.id_cajon in ids)
        for c in ids:
            del self.cajones_[c]
        del self.modulos_[i]

    def zocalos(self, id_mueble):
        return [z for z in self.zocalos_.values() if z.id_mueble == id_mueble]

    def zocalo(self, i):
        return self.zocalos_.get(i)

    def guardar_zocalo(self, z, piezas_nuevas):
        i = z.id or self._nuevo(self.zocalos_)
        self.zocalos_[i] = replace(z, id=i)
        self._borrar_piezas(lambda p: not p.editada and p.id_zocalo == i)
        for p in piezas_nuevas:
            k = self._nuevo(self.piezas_)
            self.piezas_[k] = replace(p, id=k, id_zocalo=i)
        return i

    def eliminar_zocalo(self, i):
        self._borrar_piezas(lambda p: p.id_zocalo == i)
        del self.zocalos_[i]

    def _con_orden(self, p):
        if p.id_cajon:
            id_modulo, orden = self.cajones_[p.id_cajon]
            modulo = self.modulos_[id_modulo]
            return replace(p, orden_cajon=orden, veces=modulo.cantidad, id_guia_cajon=modulo.cajones[orden - 1].id_guia)
        if p.id_modulo:
            return replace(p, veces=self.modulos_[p.id_modulo].cantidad)
        return p

    def piezas_de_modulo(self, i):
        ids = {c for c, (mod, _) in self.cajones_.items() if mod == i}
        return [self._con_orden(p) for p in self.piezas_.values() if p.id_modulo == i or p.id_cajon in ids]

    def piezas_de_zocalo(self, i):
        return [p for p in self.piezas_.values() if p.id_zocalo == i]

    def trabajo_de_pieza(self, i):
        p = self.piezas_.get(i)
        if p is None:
            return None
        if p.id_mueble:
            id_mueble = p.id_mueble
        elif p.id_zocalo:
            id_mueble = self.zocalos_[p.id_zocalo].id_mueble
        else:
            id_modulo = p.id_modulo or self.cajones_[p.id_cajon][0]
            id_mueble = self.modulos_[id_modulo].id_mueble
        return self.muebles_[id_mueble].id_trabajo

    def piezas_de_trabajo(self, id_trabajo):
        return [self._con_orden(p) for p in self.piezas_.values() if self.trabajo_de_pieza(p.id) == id_trabajo]

    def pieza(self, i):
        p = self.piezas_.get(i)
        return self._con_orden(p) if p else None

    def guardar_pieza(self, p):
        i = p.id or self._nuevo(self.piezas_)
        self.piezas_[i] = replace(p, id=i)
        return i

    def eliminar_pieza(self, i):
        del self.piezas_[i]
