"""Piezas de interfaz que usan varias pantallas."""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

import flet as ft

from carpinteria.negocio.trabajos import formatear_fecha_al_escribir
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


def dialogo(p: Paleta, titulo: str, contenido: ft.Control, acciones: list[ft.Control],
            ancho: int = 440) -> ft.AlertDialog:
    return ft.AlertDialog(
        modal=True,
        bgcolor=p.superficie,
        title=ft.Text(titulo, font_family=tema.SERIF, size=30, color=p.texto),
        content=ft.Container(content=contenido, width=ancho),
        actions=acciones,
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=16),
    )


def boton_cancelar(p: Paleta, al_tocar) -> ft.TextButton:
    return ft.TextButton(content=ft.Text("Cancelar", color=p.texto_secundario), on_click=al_tocar)


def boton_con_icono(texto: str, icono, p: Paleta, al_tocar, principal: bool = True,
                    **opciones) -> ft.Control:
    """Botón con ícono a la izquierda (principal dorado o secundario con borde).

    Deshabilitado se ve apagado, para que no parezca que hace algo.
    """
    apagado = bool(opciones.get("disabled"))
    if apagado:
        color = p.texto_tenue
    else:
        color = p.sobre_acento if principal else p.texto
    contenido = ft.Row([ft.Icon(icono, color=color, size=20),
                        ft.Text(texto, font_family=SANS_SEMI if principal else tema.SANS_MEDIA,
                                size=15, color=color)], spacing=8, tight=True)
    forma = ft.RoundedRectangleBorder(radius=tema.RADIO)
    if principal and not apagado:
        return ft.FilledButton(content=contenido, on_click=al_tocar, height=48,
                               style=ft.ButtonStyle(bgcolor=p.acento, shape=forma), **opciones)
    return ft.OutlinedButton(content=contenido, on_click=al_tocar, height=48 if principal else 44,
                             style=ft.ButtonStyle(side=ft.BorderSide(1, p.borde if apagado else p.borde_fuerte),
                                                  shape=forma),
                             **opciones)


def estado_vacio(icono, titulo: str, texto: str, p: Paleta,
                 accion: ft.Control | None = None) -> ft.Container:
    """Mensaje amable cuando una lista no tiene nada que mostrar."""
    return tarjeta(
        ft.Column([
            ft.Icon(icono, size=40, color=p.acento_texto),
            ft.Text(titulo, font_family=tema.SERIF, size=26, color=p.texto),
            ft.Text(texto, size=15, color=p.texto_tenue, text_align=ft.TextAlign.CENTER),
            *([accion] if accion else []),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, tight=True),
        p, padding=40, alignment=ft.Alignment.CENTER,
    )


def dato(icono, texto: str | None, p: Paleta, vacio: str = "—") -> ft.Row:
    """Ícono + valor (teléfono, email, dirección...)."""
    return ft.Row([ft.Icon(icono, size=18, color=p.texto_tenue),
                   ft.Text(texto or vacio, size=15, selectable=bool(texto),
                           color=p.texto if texto else p.texto_tenue)], spacing=10)


def desplegable(etiqueta: str, opciones: list[tuple[str, str]], valor: str, p: Paleta,
                ancho: int | None = None) -> ft.Dropdown:
    return ft.Dropdown(
        label=etiqueta, value=valor, width=ancho,
        options=[ft.DropdownOption(key=k, text=t) for k, t in opciones],
        label_style=ft.TextStyle(color=p.texto_secundario),
        text_style=ft.TextStyle(color=p.texto, size=14),
        border_color=p.borde_fuerte, focused_border_color=p.acento, border_radius=tema.RADIO,
        filled=True, fill_color=p.superficie, bgcolor=p.superficie,
    )


def colores_estado_trabajo(nombre: str, p: Paleta) -> tuple[str, str]:
    """(texto, fondo) de la etiqueta de cada estado del trabajo."""
    if nombre == "Presupuestado":
        return p.texto_secundario, p.fondo
    if nombre == "Cobrado":
        return p.exito, p.superficie_alta
    if nombre == "Cancelado":
        return p.error_texto, p.error_fondo
    return p.acento_texto, p.superficie_alta


def etiqueta_estado_trabajo(nombre: str, p: Paleta) -> ft.Container:
    texto, fondo = colores_estado_trabajo(nombre, p)
    return etiqueta_estado(nombre, texto, fondo)


def campo_fecha(etiqueta: str, valor: str, p: Paleta, **opciones) -> ft.TextField:
    """Fecha escrita como dd/mm/aaaa, con un botón "Hoy" al costado."""
    campo = tema.campo(etiqueta, p, value=valor, hint_text="dd/mm/aaaa",
                       input_filter=ft.InputFilter(regex_string=r"^[0-9/\-.]{0,10}$", allow=True,
                                                   replacement_string=""),
                       **opciones)

    def al_escribir(_) -> None:
        con_barras = formatear_fecha_al_escribir(campo.value)
        if con_barras != campo.value:
            campo.value = con_barras
            campo.update()

    campo.on_change = al_escribir

    def hoy(_):
        campo.value = f"{date.today():%d/%m/%Y}"
        campo.update()

    campo.suffix = ft.TextButton(content=ft.Text("Hoy", size=13, color=p.acento_texto), on_click=hoy,
                                 tooltip="Completar con la fecha de hoy")
    return campo
