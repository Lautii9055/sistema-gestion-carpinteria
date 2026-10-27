"""Piezas de interfaz que usan varias pantallas."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import flet as ft

from carpinteria.presentacion import tema
from carpinteria.presentacion.tema import Paleta, SANS_SEMI

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(fecha: datetime) -> str:
    return f"{DIAS[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]}"


def iniciales(nombre_completo: str) -> str:
    partes = nombre_completo.split()
    return "".join(p[0] for p in partes[:2]).upper() or "?"


def avatar(nombre_completo: str, p: Paleta, tamano: int = 36) -> ft.Container:
    return ft.Container(
        width=tamano, height=tamano, border_radius=tamano / 2, bgcolor=p.acento,
        alignment=ft.Alignment.CENTER,
        content=ft.Text(iniciales(nombre_completo), font_family=SANS_SEMI,
                        size=tamano * 0.38, color=p.sobre_acento),
    )


def etiqueta_estado(texto: str, color_texto: str, color_fondo: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(texto, size=12, color=color_texto, font_family=tema.SANS_MEDIA),
        bgcolor=color_fondo, border_radius=99,
        padding=ft.Padding.symmetric(horizontal=10, vertical=3),
    )


def tarjeta(contenido: ft.Control, p: Paleta, padding: int = 24, **opciones) -> ft.Container:
    return ft.Container(content=contenido, bgcolor=p.superficie, border=ft.Border.all(1, p.borde),
                        border_radius=14, padding=ft.Padding.all(padding), **opciones)


def encabezado_seccion(etiqueta: str, titulo: str, descripcion: str, p: Paleta,
                       accion: ft.Control | None = None) -> ft.Row:
    textos = ft.Column([
        tema.etiqueta_superior(etiqueta, p),
        tema.titulo(titulo, p, 42),
        ft.Text(descripcion, size=15, color=p.texto_tenue),
    ], spacing=4, expand=True)
    # Sin wrap: un hijo con expand dentro de una fila con wrap rompe el diseño en Flutter.
    return ft.Row([textos] + ([accion] if accion else []),
                  vertical_alignment=ft.CrossAxisAlignment.END, spacing=16)


def requisitos_contrasena(p: Paleta, minimo: int, nombre_usuario: str
                          ) -> tuple[ft.Column, Callable[[str, str], None]]:
    """Lista de requisitos que se tildan mientras se escribe (RF-03.2).

    Devuelve el control y una función actualizar(nueva, confirmacion).
    """
    def fila(texto: str) -> tuple[ft.Icon, ft.Row]:
        icono = ft.Icon(ft.Icons.RADIO_BUTTON_UNCHECKED, size=18, color=p.texto_tenue)
        return icono, ft.Row([icono, ft.Text(texto, size=14, color=p.texto_secundario)], spacing=8)

    largo, fila_largo = fila(f"Al menos {minimo} caracteres")
    distinto, fila_distinto = fila("Distinta de tu nombre de usuario")
    iguales, fila_iguales = fila("Las dos coinciden")

    def marcar(icono: ft.Icon, cumple: bool) -> None:
        icono.icon = ft.Icons.CHECK_CIRCLE if cumple else ft.Icons.RADIO_BUTTON_UNCHECKED
        icono.color = p.exito if cumple else p.texto_tenue

    def actualizar(nueva: str, confirmacion: str) -> None:
        marcar(largo, len(nueva) >= minimo)
        marcar(distinto, bool(nueva) and nueva.strip().casefold() != nombre_usuario.casefold())
        marcar(iguales, bool(nueva) and nueva == confirmacion)

    return ft.Column([fila_largo, fila_distinto, fila_iguales], spacing=6), actualizar


def aviso_flotante(page: ft.Page, texto: str, p: Paleta) -> None:
    """Mensaje breve abajo de la pantalla (confirmaciones)."""
    page.show_dialog(ft.SnackBar(
        content=ft.Text(texto, color=p.texto, size=14),
        bgcolor=p.superficie_alta, behavior=ft.SnackBarBehavior.FLOATING,
        show_close_icon=True, close_icon_color=p.texto_secundario,
        duration=6000,  # milisegundos
    ))
