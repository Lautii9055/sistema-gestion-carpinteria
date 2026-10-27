"""Pantalla de ingreso (diseño 1 · Ingreso)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from carpinteria.presentacion import tema
from carpinteria.presentacion.tema import SANS, SERIF, SERIF_ITALICA

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

ANCHO_MINIMO_PANEL_MARCA = 980  # en ventanas más angostas se oculta el panel izquierdo


def construir(app: Aplicacion, aviso_info: str | None = None) -> ft.Control:
    p = app.paleta

    caja_error = ft.Container(content=tema.aviso(aviso_info, p, tipo="info") if aviso_info else None,
                              visible=bool(aviso_info))
    usuario = tema.campo("Usuario", p, autofocus=True)
    contrasena = tema.campo("Contraseña", p, password=True, can_reveal_password=True)
    cargando = ft.ProgressRing(width=22, height=22, stroke_width=3, color=p.sobre_acento, visible=False)

    def mostrar_error(mensaje: str) -> None:
        caja_error.content = tema.aviso(mensaje, p)
        caja_error.visible = True

    def ingresar(_=None) -> None:
        if not usuario.value or not contrasena.value:
            mostrar_error("Completá usuario y contraseña.")
            app.page.update()
            return
        boton.disabled = True
        cargando.visible = True
        caja_error.visible = False
        app.page.update()
        error = app.intentar_ingreso(usuario.value, contrasena.value)
        boton.disabled = False
        cargando.visible = False
        if error:
            contrasena.value = ""
            mostrar_error(error)
            app.page.update()
            contrasena.focus()

    usuario.on_submit = lambda _: contrasena.focus()
    contrasena.on_submit = ingresar

    boton = ft.FilledButton(
        content=ft.Row([cargando, ft.Text("Ingresar", font_family=tema.SANS_SEMI, size=16,
                                          color=p.sobre_acento)],
                       alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        on_click=ingresar, height=52,
        style=ft.ButtonStyle(bgcolor=p.acento, shape=ft.RoundedRectangleBorder(radius=tema.RADIO)),
    )

    formulario = ft.Column(
        [
            ft.Column([
                tema.titulo("Bienvenido", p),
                ft.Text("Ingresá con tu usuario para continuar.", color=p.texto_tenue, size=15),
            ], spacing=4),
            caja_error,
            usuario,
            contrasena,
            boton,
            ft.Text(
                "¿Olvidaste tu contraseña? Pedile al otro usuario que la blanquee "
                "desde Configuración › Usuarios.",
                size=13, color=p.texto_tenue, text_align=ft.TextAlign.CENTER,
            ),
        ],
        spacing=20, width=400, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    panel_marca = ft.Container(
        expand=True,
        visible=(app.page.width or 1440) >= ANCHO_MINIMO_PANEL_MARCA,
        padding=ft.Padding.all(64),
        gradient=ft.RadialGradient(
            center=ft.Alignment(-0.6, -0.8), radius=1.4,
            colors=["#2A2219", "#15120E"] if p.oscura else ["#FFFFFF", "#EFE8DC"],
        ),
        border=ft.Border.only(right=ft.BorderSide(1, p.borde)),
        content=ft.Column(
            [
                ft.Text("ZANINO", font_family=SERIF, size=30, color=p.texto,
                        style=ft.TextStyle(letter_spacing=5)),
                ft.Column([
                    tema.etiqueta_superior("Gestión del taller", p),
                    ft.Text(spans=[
                        ft.TextSpan("Cada pieza, ", ft.TextStyle(font_family=SERIF, color=p.texto)),
                        ft.TextSpan("a la medida", ft.TextStyle(font_family=SERIF_ITALICA, color=p.acento_texto)),
                        ft.TextSpan(" justa.", ft.TextStyle(font_family=SERIF, color=p.texto)),
                    ], size=64),
                    ft.Text("Clientes, trabajos, despiece y retazos en un solo lugar.",
                            font_family=SANS, size=16, color=p.texto_tenue),
                ], spacing=18),
                ft.Row([ft.Container(width=32, height=2, bgcolor=p.acento),
                        ft.Container(width=32, height=2, bgcolor=p.borde_fuerte),
                        ft.Container(width=32, height=2, bgcolor=p.borde_fuerte)], spacing=8),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    )

    def al_cambiar_tamano(_):
        panel_marca.visible = (app.page.width or 0) >= ANCHO_MINIMO_PANEL_MARCA
        app.page.update()

    app.page.on_resize = al_cambiar_tamano

    return ft.Row(
        [
            panel_marca,
            ft.Container(
                expand=True,
                padding=ft.Padding.all(48),
                alignment=ft.Alignment.CENTER,
                content=ft.Stack([
                    ft.Container(content=formulario, alignment=ft.Alignment.CENTER, expand=True),
                    ft.Container(content=tema.boton_modo(p, lambda _: app.alternar_modo()),
                                 right=0, top=0),
                ], expand=True),
            ),
        ],
        expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )
