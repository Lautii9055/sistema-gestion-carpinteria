"""Arranque de la aplicación, navegación entre pantallas y control de la sesión.

Este archivo "arma" el sistema: crea los repositorios de la capa de datos, se
los pasa a los servicios de negocio y muestra las pantallas. Es el único lugar
que conoce las tres capas a la vez (raíz de composición).
"""
import asyncio
import logging
import os
import time
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

import flet as ft

from carpinteria.datos.conexion import ErrorConexion
from carpinteria.datos.repositorios import (RepositorioAuditoriaSql, RepositorioParametrosSql,
                                            RepositorioUsuariosSql)
from carpinteria.datos.repositorios_clientes import RepositorioClientesSql, RepositorioObrasSql
from carpinteria.datos.repositorios_materiales import RepositorioMaterialesSql
from carpinteria.datos.repositorios_trabajos import RepositorioTrabajosSql
from carpinteria.negocio.auditoria import ServicioAuditoria
from carpinteria.negocio.autenticacion import ErrorAutenticacion, ServicioAutenticacion
from carpinteria.negocio.clientes import ServicioClientes
from carpinteria.negocio.inicio import ServicioInicio
from carpinteria.negocio.materiales import ServicioMateriales
from carpinteria.negocio.trabajos import ServicioTrabajos
from carpinteria.negocio.entidades import Sesion
from carpinteria.negocio.usuarios import ServicioUsuarios
from carpinteria.presentacion import (componentes, shell, tema, vista_auditoria,
                                      vista_cambio_contrasena, vista_clientes, vista_ficha_cliente,
                                      vista_inicio, vista_ingreso, vista_materiales, vista_trabajo,
                                      vista_trabajos,
                                      vista_usuarios)

registro = logging.getLogger("carpinteria")

MENSAJE_ERROR_INESPERADO = "Ocurrió un error inesperado. Si se repite, avisale a Lautaro."
SEGUNDOS_ENTRE_CONTROLES = 15     # cada cuánto se revisa la inactividad
SEGUNDOS_DE_AVISO_PREVIO = 60     # aviso antes de cerrar la sesión


def configurar_registro() -> Path:
    """Log técnico en un archivo local con rotación (RNF-05.4).

    El usuario nunca ve el detalle técnico de un error; queda acá para
    diagnosticarlo. No se registran contraseñas ni datos de clientes.
    """
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SistemaCarpinteria" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    if not registro.handlers:
        manejador = RotatingFileHandler(base / "sistema.log", maxBytes=1_000_000, backupCount=5,
                                        encoding="utf-8")
        manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        registro.addHandler(manejador)
        registro.setLevel(logging.INFO)
    return base


class Aplicacion:
    def __init__(self, page: ft.Page, autenticacion: ServicioAutenticacion,
                 usuarios: ServicioUsuarios, auditoria: ServicioAuditoria,
                 clientes: ServicioClientes, trabajos: ServicioTrabajos, inicio: ServicioInicio,
                 materiales: ServicioMateriales) -> None:
        self.page = page
        self.autenticacion = autenticacion
        self.usuarios = usuarios
        self.auditoria = auditoria
        self.clientes = clientes
        self.trabajos = trabajos
        self.inicio = inicio
        self.materiales = materiales
        self.recuerdos: dict = {}  # estado de cada pantalla (ej.: la última búsqueda)
        self.modo_oscuro = True
        self.sesion: Sesion | None = None
        self._redibujar: Callable[[], None] = self.mostrar_ingreso
        self._pendientes_al_mostrar: list[Callable[[], None]] = []
        # Inactividad (RF-03.3)
        self._ultima_actividad = time.monotonic()
        self._minutos_inactividad = 15
        self._avisado = False
        page.on_keyboard_event = lambda _: self.registrar_actividad()

    # ---------- apariencia ----------
    @property
    def paleta(self) -> tema.Paleta:
        return tema.OSCURA if self.modo_oscuro else tema.CLARA

    def alternar_modo(self) -> None:
        self.modo_oscuro = not self.modo_oscuro
        self._redibujar()

    def _mostrar(self, contenido: ft.Control) -> None:
        p = self.paleta
        self.page.theme_mode = ft.ThemeMode.DARK if p.oscura else ft.ThemeMode.LIGHT
        self.page.bgcolor = p.fondo
        if self.sesion is not None:
            # El movimiento del mouse sobre la ventana cuenta como actividad.
            contenido = ft.GestureDetector(content=contenido, expand=True, hover_interval=2000,
                                           on_hover=lambda _: self.registrar_actividad(),
                                           on_tap_down=lambda _: self.registrar_actividad())
        self.page.controls.clear()
        self.page.controls.append(contenido)
        self.page.update()
        pendientes, self._pendientes_al_mostrar = self._pendientes_al_mostrar, []
        for funcion in pendientes:
            funcion()

    def al_mostrar(self, funcion: Callable[[], None]) -> None:
        """Ejecuta algo (por ejemplo, cargar datos) apenas la pantalla está visible."""
        self._pendientes_al_mostrar.append(funcion)

    def mostrar_dialogo(self, dialogo: ft.AlertDialog) -> None:
        self.page.show_dialog(dialogo)

    def cerrar_dialogo(self) -> None:
        self.page.pop_dialog()

    # ---------- pantallas ----------
    def mostrar_ingreso(self, aviso: str | None = None) -> None:
        self.sesion = None
        self.recuerdos.clear()  # lo que buscó un usuario no lo ve el siguiente
        self._redibujar = self.mostrar_ingreso
        self._mostrar(vista_ingreso.construir(self, aviso))

    def mostrar_cambio_obligatorio(self) -> None:
        self.page.on_resize = None
        self._redibujar = self.mostrar_cambio_obligatorio
        self._mostrar(vista_cambio_contrasena.construir(self, self.sesion))

    # Pantallas que no están en el menú y qué opción del menú queda marcada.
    _SECCION_DEL_MENU = {"cliente": "clientes", "trabajo": "trabajos"}

    def ir_a(self, seccion: str, **datos) -> None:
        """Muestra una sección; datos lleva lo que necesita (ej.: id_cliente)."""
        self.page.on_resize = None
        self.registrar_actividad()
        vistas = {
            "inicio": lambda: vista_inicio.construir(self, self.sesion),
            "clientes": lambda: vista_clientes.construir(self),
            "cliente": lambda: vista_ficha_cliente.construir(self, datos["id_cliente"]),
            "trabajos": lambda: vista_trabajos.construir(self),
            "materiales": lambda: vista_materiales.construir(self),
            "trabajo": lambda: vista_trabajo.construir(self, datos["id_trabajo"]),
            "usuarios": lambda: vista_usuarios.construir(self),
            "auditoria": lambda: vista_auditoria.construir(self),
            "contrasena": lambda: vista_cambio_contrasena.construir_mi_contrasena(self, self.sesion),
        }
        self._redibujar = lambda: self.ir_a(seccion, **datos)
        menu = self._SECCION_DEL_MENU.get(seccion, seccion)
        self._mostrar(shell.construir(self, menu, vistas[seccion]()))

    # ---------- acciones ----------
    def ejecutar(self, funcion: Callable, *argumentos):
        """Llama a un servicio y devuelve (resultado, mensaje_de_error).

        Los errores previstos se muestran tal cual; los imprevistos se registran
        en el log y el usuario ve un mensaje general (sin detalles técnicos).
        """
        try:
            return funcion(*argumentos), None
        except (ErrorAutenticacion, ErrorConexion) as error:
            return None, str(error)
        except Exception:
            registro.exception("Error en %s", getattr(funcion, "__name__", funcion))
            return None, MENSAJE_ERROR_INESPERADO

    def intentar_ingreso(self, usuario: str, contrasena: str) -> str | None:
        """Devuelve un mensaje de error para mostrar, o None si ingresó."""
        sesion, error = self.ejecutar(self.autenticacion.ingresar, usuario, contrasena)
        if error:
            return error
        self.sesion = sesion
        minutos, _ = self.ejecutar(lambda: self.autenticacion.minutos_inactividad)
        self._minutos_inactividad = minutos or 15
        registro.info("Cierre por inactividad configurado en %s min", self._minutos_inactividad)
        self.registrar_actividad()
        registro.info("Ingreso del usuario id=%s", sesion.usuario.id)
        if sesion.debe_cambiar_contrasena:
            self.mostrar_cambio_obligatorio()
        else:
            self.ir_a("inicio")
        return None

    def intentar_cambio_contrasena(self, sesion: Sesion, nueva: str, confirmacion: str,
                                   actual: str | None = None) -> str | None:
        if actual is None:
            _, error = self.ejecutar(self.autenticacion.cambiar_contrasena,
                                     sesion.usuario.id, nueva, confirmacion)
        else:
            _, error = self.ejecutar(self.autenticacion.cambiar_contrasena_propia,
                                     sesion.usuario.id, actual, nueva, confirmacion)
        if error:
            return error
        if actual is None:  # era el cambio obligatorio: ahora sí, al inicio
            self.ir_a("inicio")
        return None

    def cerrar_sesion(self, por_inactividad: bool = False) -> None:
        if self.sesion:
            self.ejecutar(self.autenticacion.cerrar_sesion, self.sesion, por_inactividad)
        while self.page.pop_dialog():  # cierra cualquier diálogo abierto
            pass
        aviso = ("Por seguridad, la sesión se cerró después de "
                 f"{self._minutos_inactividad} minutos sin uso. Ingresá de nuevo para continuar."
                 if por_inactividad else None)
        self.mostrar_ingreso(aviso)

    # ---------- inactividad (RF-03.3) ----------
    def registrar_actividad(self) -> None:
        self._ultima_actividad = time.monotonic()
        self._avisado = False

    async def vigilar_inactividad(self) -> None:
        registro.info("Control de inactividad iniciado")
        while True:
            await asyncio.sleep(SEGUNDOS_ENTRE_CONTROLES)
            try:
                self._controlar_inactividad()
            except Exception:
                # Un error puntual no debe apagar el control de inactividad.
                registro.exception("Error en el control de inactividad")

    def _controlar_inactividad(self) -> None:
        if self.sesion is None:
            return
        inactivo = time.monotonic() - self._ultima_actividad
        limite = self._minutos_inactividad * 60
        if inactivo >= limite:
            registro.info("Sesión cerrada por inactividad (%s min)", self._minutos_inactividad)
            self.cerrar_sesion(por_inactividad=True)
        elif inactivo >= limite - SEGUNDOS_DE_AVISO_PREVIO and not self._avisado:
            self._avisado = True
            componentes.aviso_flotante(
                self.page, "Por inactividad, la sesión se va a cerrar en un minuto. "
                           "Mové el mouse o tocá una tecla para seguir.", self.paleta)


def main(page: ft.Page) -> None:
    configurar_registro()
    page.title = "Zanino · Gestión del taller"
    page.fonts = tema.FUENTES
    page.theme = tema.tema_flet(tema.CLARA)
    page.dark_theme = tema.tema_flet(tema.OSCURA)
    page.padding = 0
    page.window.width = 1280
    page.window.height = 820
    page.window.min_width = 960
    page.window.min_height = 640

    repositorio_usuarios = RepositorioUsuariosSql()
    repositorio_auditoria = RepositorioAuditoriaSql()
    repositorio_parametros = RepositorioParametrosSql()
    repositorio_clientes = RepositorioClientesSql()
    repositorio_obras = RepositorioObrasSql()
    repositorio_trabajos = RepositorioTrabajosSql()
    app = Aplicacion(
        page,
        autenticacion=ServicioAutenticacion(repositorio_usuarios, repositorio_auditoria,
                                            repositorio_parametros),
        usuarios=ServicioUsuarios(repositorio_usuarios, repositorio_auditoria),
        auditoria=ServicioAuditoria(repositorio_auditoria),
        clientes=ServicioClientes(repositorio_clientes, repositorio_obras),
        trabajos=ServicioTrabajos(repositorio_trabajos, repositorio_clientes, repositorio_obras,
                                  repositorio_auditoria, repositorio_parametros),
        inicio=ServicioInicio(repositorio_trabajos),
        materiales=ServicioMateriales(RepositorioMaterialesSql()),
    )
    page.run_task(app.vigilar_inactividad)
    app.mostrar_ingreso()


def iniciar() -> None:
    ft.run(main, assets_dir=str(tema.CARPETA_RECURSOS))
