"""Cambio de contraseña.

Dos usos:
- Obligatorio, a pantalla completa, después de ingresar con una contraseña
  provisoria (RNF-10 y RF-03.4).
- Voluntario, desde "Mi contraseña" en el menú: pide además la actual (RF-02).
Los requisitos se tildan a medida que se escribe, para que no haya que adivinar.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import Sesion
from carpinteria.presentacion import componentes, tema

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion


def _formulario(app: Aplicacion, sesion: Sesion, obligatorio: bool) -> ft.Container:
    p = app.paleta
    usuario = sesion.usuario
    minimo = app.autenticacion.largo_minimo_contrasena

    actual = tema.campo("Contraseña actual", p, password=True, can_reveal_password=True,
                        autofocus=True, visible=not obligatorio)
    nueva = tema.campo("Contraseña nueva", p, password=True, can_reveal_password=True,
                       autofocus=obligatorio)
    confirmacion = tema.campo("Repetila", p, password=True, can_reveal_password=True)
    caja_error = ft.Container(visible=False)
    requisitos, actualizar_requisitos = componentes.requisitos_contrasena(p, minimo, usuario.nombre_usuario)

    def actualizar(_=None) -> None:
        actualizar_requisitos(nueva.value or "", confirmacion.value or "")
        app.page.update()

    def guardar(_=None) -> None:
        error = app.intentar_cambio_contrasena(
            sesion, nueva.value or "", confirmacion.value or "",
            actual=None if obligatorio else (actual.value or ""),
        )
        if error:
            caja_error.content = tema.aviso(error, p)
            caja_error.visible = True
            app.page.update()
        elif not obligatorio:
            actual.value = nueva.value = confirmacion.value = ""
            caja_error.visible = False
            actualizar()
            componentes.aviso_flotante(app.page, "Listo, tu contraseña se cambió.", p)

    nueva.on_change = actualizar
    confirmacion.on_change = actualizar
    actual.on_submit = lambda _: nueva.focus()
    nueva.on_submit = lambda _: confirmacion.focus()
    confirmacion.on_submit = guardar

    if obligatorio:
        encabezado = [
            tema.etiqueta_superior("Contraseña provisoria", p),
            tema.titulo("Elegí tu contraseña", p, 36),
            ft.Text(f"Hola, {usuario.nombre_completo.split()[0]}. Por seguridad, la contraseña "
                    "provisoria tiene que cambiarse antes de usar el sistema.",
                    size=15, color=p.texto_secundario),
        ]
    else:
        encabezado = [ft.Text("Usá una contraseña que no uses en otro lado. Si la anotás, "
                              "guardala en un gestor de contraseñas.",
                              size=15, color=p.texto_secundario)]

    return ft.Container(
        width=480, bgcolor=p.superficie, border=ft.Border.all(1, p.borde), border_radius=16,
        padding=ft.Padding.all(32),
        content=ft.Column(
            [*encabezado, caja_error, actual, nueva, confirmacion, requisitos,
             tema.boton_principal("Guardar y continuar" if obligatorio else "Cambiar contraseña",
                                  p, guardar)],
            spacing=18, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )


def construir(app: Aplicacion, sesion: Sesion) -> ft.Control:
    """Pantalla completa del cambio obligatorio."""
    return ft.Container(
        expand=True, alignment=ft.Alignment.CENTER, padding=ft.Padding.all(32),
        content=ft.Column([_formulario(app, sesion, obligatorio=True)], scroll=ft.ScrollMode.AUTO,
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          alignment=ft.MainAxisAlignment.CENTER),
    )


def construir_mi_contrasena(app: Aplicacion, sesion: Sesion) -> ft.Control:
    """Sección "Mi contraseña" dentro del menú."""
    p = app.paleta
    return ft.Column([
        componentes.encabezado_seccion("Configuración", "Mi contraseña",
                                       "Cambiá tu contraseña cuando quieras.", p),
        _formulario(app, sesion, obligatorio=False),
    ], spacing=24)
