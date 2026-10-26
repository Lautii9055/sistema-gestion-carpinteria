"""Cambio obligatorio de contraseña (RNF-10 y RF-03.2).

Aparece después de ingresar cuando el usuario tiene una contraseña provisoria
(por ejemplo, la del usuario inicial o una blanqueada). Los requisitos se
tildan a medida que se escribe, para que no haya que adivinar.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import Sesion
from carpinteria.presentacion import tema

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion


def construir(app: Aplicacion, sesion: Sesion) -> ft.Control:
    p = app.paleta
    usuario = sesion.usuario
    minimo = app.servicio.largo_minimo_contrasena

    nueva = tema.campo("Contraseña nueva", p, password=True, can_reveal_password=True, autofocus=True)
    confirmacion = tema.campo("Repetila", p, password=True, can_reveal_password=True)
    caja_error = ft.Container(visible=False)

    def requisito(texto: str) -> tuple[ft.Icon, ft.Row]:
        icono = ft.Icon(ft.Icons.RADIO_BUTTON_UNCHECKED, size=18, color=p.texto_tenue)
        return icono, ft.Row([icono, ft.Text(texto, size=14, color=p.texto_secundario)], spacing=8)

    icono_largo, fila_largo = requisito(f"Al menos {minimo} caracteres")
    icono_usuario, fila_usuario = requisito("Distinta de tu nombre de usuario")
    icono_iguales, fila_iguales = requisito("Las dos coinciden")

    def marcar(icono: ft.Icon, cumple: bool) -> None:
        icono.icon = ft.Icons.CHECK_CIRCLE if cumple else ft.Icons.RADIO_BUTTON_UNCHECKED
        icono.color = p.exito if cumple else p.texto_tenue

    def actualizar(_=None) -> None:
        valor = nueva.value or ""
        marcar(icono_largo, len(valor) >= minimo)
        marcar(icono_usuario, bool(valor) and valor.strip().casefold() != usuario.nombre_usuario.casefold())
        marcar(icono_iguales, bool(valor) and valor == confirmacion.value)
        app.page.update()

    def guardar(_=None) -> None:
        error = app.intentar_cambio_contrasena(sesion, nueva.value or "", confirmacion.value or "")
        if error:
            caja_error.content = tema.aviso(error, p)
            caja_error.visible = True
            app.page.update()

    nueva.on_change = actualizar
    confirmacion.on_change = actualizar
    nueva.on_submit = lambda _: confirmacion.focus()
    confirmacion.on_submit = guardar

    tarjeta = ft.Container(
        width=480,
        bgcolor=p.superficie, border=ft.Border.all(1, p.borde), border_radius=16,
        padding=ft.Padding.all(32),
        content=ft.Column(
            [
                tema.etiqueta_superior("Primer ingreso", p),
                tema.titulo("Elegí tu contraseña", p, 36),
                ft.Text(
                    f"Hola, {usuario.nombre_completo.split()[0]}. Por seguridad, la contraseña "
                    "provisoria tiene que cambiarse antes de usar el sistema.",
                    size=15, color=p.texto_secundario,
                ),
                caja_error,
                nueva,
                confirmacion,
                ft.Column([fila_largo, fila_usuario, fila_iguales], spacing=6),
                tema.boton_principal("Guardar y continuar", p, guardar),
            ],
            spacing=18, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )

    return ft.Container(
        expand=True, alignment=ft.Alignment.CENTER, padding=ft.Padding.all(32),
        content=ft.Column([tarjeta], scroll=ft.ScrollMode.AUTO,
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          alignment=ft.MainAxisAlignment.CENTER),
    )
