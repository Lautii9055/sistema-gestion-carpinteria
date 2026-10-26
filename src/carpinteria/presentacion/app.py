"""Arranque de la aplicación y navegación entre pantallas.

Este archivo "arma" el sistema: crea los repositorios de la capa de datos, se
los pasa al servicio de negocio y muestra las pantallas. Es el único lugar que
conoce las tres capas a la vez (raíz de composición).
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os

import flet as ft

from carpinteria.datos.conexion import ErrorConexion
from carpinteria.datos.repositorios import (RepositorioAuditoriaSql, RepositorioParametrosSql,
                                            RepositorioUsuariosSql)
from carpinteria.negocio.autenticacion import ErrorAutenticacion, ServicioAutenticacion
from carpinteria.negocio.entidades import Sesion
from carpinteria.presentacion import tema, vista_cambio_contrasena, vista_inicio, vista_ingreso

registro = logging.getLogger("carpinteria")

MENSAJE_ERROR_INESPERADO = "Ocurrió un error inesperado. Si se repite, avisale a Lautaro."


def configurar_registro() -> Path:
    """Log técnico en un archivo local con rotación (RNF-05.4).

    El usuario nunca ve el detalle técnico de un error; queda acá para
    diagnosticarlo. No se registran contraseñas ni datos de clientes.
    """
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SistemaCarpinteria" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    manejador = RotatingFileHandler(base / "sistema.log", maxBytes=1_000_000, backupCount=5,
                                    encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    registro.addHandler(manejador)
    registro.setLevel(logging.INFO)
    return base


class Aplicacion:
    def __init__(self, page: ft.Page, servicio: ServicioAutenticacion) -> None:
        self.page = page
        self.servicio = servicio
        self.modo_oscuro = True
        self._pantalla_actual = self.mostrar_ingreso
        self._sesion: Sesion | None = None

    # ---------- apariencia ----------
    @property
    def paleta(self) -> tema.Paleta:
        return tema.OSCURA if self.modo_oscuro else tema.CLARA

    def alternar_modo(self) -> None:
        self.modo_oscuro = not self.modo_oscuro
        self._pantalla_actual()

    def _mostrar(self, contenido: ft.Control) -> None:
        p = self.paleta
        self.page.theme_mode = ft.ThemeMode.DARK if p.oscura else ft.ThemeMode.LIGHT
        self.page.bgcolor = p.fondo
        self.page.controls.clear()
        self.page.controls.append(contenido)
        self.page.update()

    # ---------- pantallas ----------
    def mostrar_ingreso(self) -> None:
        self._sesion = None
        self._pantalla_actual = self.mostrar_ingreso
        self._mostrar(vista_ingreso.construir(self))

    def mostrar_cambio_contrasena(self) -> None:
        self.page.on_resize = None
        self._pantalla_actual = self.mostrar_cambio_contrasena
        self._mostrar(vista_cambio_contrasena.construir(self, self._sesion))

    def mostrar_inicio(self) -> None:
        self.page.on_resize = None
        self._pantalla_actual = self.mostrar_inicio
        self._mostrar(vista_inicio.construir(self, self._sesion))

    # ---------- acciones ----------
    def intentar_ingreso(self, usuario: str, contrasena: str) -> str | None:
        """Devuelve un mensaje de error para mostrar, o None si ingresó."""
        try:
            self._sesion = self.servicio.ingresar(usuario, contrasena)
        except (ErrorAutenticacion, ErrorConexion) as error:
            return str(error)
        except Exception:
            registro.exception("Error al ingresar")
            return MENSAJE_ERROR_INESPERADO
        registro.info("Ingreso del usuario id=%s", self._sesion.usuario.id)
        if self._sesion.debe_cambiar_contrasena:
            self.mostrar_cambio_contrasena()
        else:
            self.mostrar_inicio()
        return None

    def intentar_cambio_contrasena(self, sesion: Sesion, nueva: str, confirmacion: str) -> str | None:
        try:
            self.servicio.cambiar_contrasena(sesion.usuario.id, nueva, confirmacion)
        except (ErrorAutenticacion, ErrorConexion) as error:
            return str(error)
        except Exception:
            registro.exception("Error al cambiar la contraseña")
            return MENSAJE_ERROR_INESPERADO
        self.mostrar_inicio()
        return None

    def cerrar_sesion(self) -> None:
        if self._sesion:
            try:
                self.servicio.cerrar_sesion(self._sesion)
            except Exception:
                registro.exception("Error al registrar el cierre de sesión")
        self.mostrar_ingreso()


def main(page: ft.Page) -> None:
    configurar_registro()
    page.title = "Zanino · Gestión del taller"
    page.fonts = tema.FUENTES
    page.theme = tema.tema_flet(tema.CLARA)
    page.dark_theme = tema.tema_flet(tema.OSCURA)
    page.padding = 0
    page.window.width = 1280
    page.window.height = 820
    page.window.min_width = 720
    page.window.min_height = 600

    servicio = ServicioAutenticacion(
        usuarios=RepositorioUsuariosSql(),
        auditoria=RepositorioAuditoriaSql(),
        parametros=RepositorioParametrosSql(),
    )
    Aplicacion(page, servicio).mostrar_ingreso()


def iniciar() -> None:
    ft.run(main, assets_dir=str(tema.CARPETA_RECURSOS))
