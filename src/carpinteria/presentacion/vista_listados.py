"""Generar los PDF del trabajo: listado de corte para la maderera y piezas para
el laqueador. Se guardan en Documentos\\Carpintería Zanino\\Listados y se
ofrece abrirlos."""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import DetalleTrabajo
from carpinteria.negocio.listado import nombre_de_archivo
from carpinteria.presentacion import componentes, pdf_listados, tema

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

PUEDE_ABRIR = hasattr(os, "startfile")   # Windows


def _abrir(ruta: Path) -> None:
    if PUEDE_ABRIR:
        os.startfile(ruta)  # noqa: S606 — ruta generada por el sistema, no viene del usuario


def _mostrar_generado(app: Aplicacion, ruta: Path, titulo: str) -> None:
    p = app.paleta
    acciones: list[ft.Control] = [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo())]
    if PUEDE_ABRIR:
        acciones = [ft.TextButton(content=ft.Text("Abrir la carpeta", color=p.acento_texto),
                                  on_click=lambda _: _abrir(ruta.parent)),
                    tema.boton_principal("Abrir el PDF", p, lambda _: (app.cerrar_dialogo(), _abrir(ruta)))]
    app.mostrar_dialogo(componentes.dialogo(p, titulo, ft.Column([
        ft.Text("Se guardó en:", size=14, color=p.texto_secundario),
        ft.Text(str(ruta), size=14, color=p.texto, selectable=True),
    ], spacing=6, tight=True), acciones, ancho=560))


def elegir_listado(app: Aplicacion, d: DetalleTrabajo) -> None:
    """Qué PDF generar: para la maderera, para el control del taller o para el laqueador."""
    p = app.paleta
    laqueadas = app.muebles.tiene_laqueadas(d.trabajo.id)

    def opcion(icono, titulo: str, texto: str, accion, visible: bool = True) -> ft.Container:
        return ft.Container(
            content=ft.Row([ft.Icon(icono, color=p.acento_texto, size=26),
                            ft.Column([ft.Text(titulo, size=16, font_family=tema.SANS_SEMI, color=p.texto),
                                       ft.Text(texto, size=13, color=p.texto_tenue)], spacing=2, expand=True)],
                           spacing=14),
            padding=ft.Padding.all(14), border_radius=12, border=ft.Border.all(1, p.borde_fuerte), ink=True,
            visible=visible, on_click=lambda _: (app.cerrar_dialogo(), accion()))

    app.mostrar_dialogo(componentes.dialogo(p, "¿Qué listado querés generar?", ft.Column([
        opcion(ft.Icons.CONTENT_CUT, "Para la maderera",
               "Medidas de corte, sin filo: cortan a esa medida y después aplican el filo.",
               lambda: generar_listado_de_corte(app, d)),
        opcion(ft.Icons.FACT_CHECK_OUTLINED, "Para el taller (control)",
               "Medida final con filo y medida de corte, una al lado de la otra.",
               lambda: generar_listado_de_corte(app, d, para_taller=True)),
        opcion(ft.Icons.FORMAT_PAINT_OUTLINED, "Para el laqueador",
               "Piezas a laquear por color y terminación, con su medida final.",
               lambda: generar_laqueador(app, d), visible=laqueadas),
    ], spacing=10, tight=True), [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo())], ancho=560))


def generar_listado_de_corte(app: Aplicacion, d: DetalleTrabajo, para_taller: bool = False) -> None:
    p = app.paleta
    secciones, error = app.ejecutar(app.muebles.listado_de_corte, d.trabajo.id)
    if error:
        acciones: list[ft.Control] = [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo())]
        if "filos" in error:
            acciones.append(tema.boton_principal("Ir a Piezas y filos", p, lambda _: (
                app.cerrar_dialogo(), app.ir_a("piezas", id_trabajo=d.trabajo.id))))
        app.mostrar_dialogo(componentes.dialogo(p, "Todavía no se puede generar",
                                                ft.Text(error, size=15, color=p.texto_secundario), acciones,
                                                ancho=520))
        return
    que = "Control del taller" if para_taller else "Listado de corte"
    ruta = pdf_listados.carpeta_de_listados() / nombre_de_archivo(d.trabajo.id, d.trabajo.descripcion, que)
    _, error = app.ejecutar(pdf_listados.generar_listado_de_corte, ruta, d, secciones, para_taller)
    if error:
        componentes.aviso_flotante(app.page, error, p)
        return
    _mostrar_generado(app, ruta, f"{que} generado")


def generar_laqueador(app: Aplicacion, d: DetalleTrabajo) -> None:
    p = app.paleta
    secciones, error = app.ejecutar(app.muebles.listado_laqueador, d.trabajo.id)
    if error:
        componentes.aviso_flotante(app.page, error, p)
        return
    ruta = pdf_listados.carpeta_de_listados() / nombre_de_archivo(d.trabajo.id, d.trabajo.descripcion,
                                                                  "Para el laqueador")
    _, error = app.ejecutar(pdf_listados.generar_listado_laqueador, ruta, d, secciones)
    if error:
        componentes.aviso_flotante(app.page, error, p)
        return
    _mostrar_generado(app, ruta, "Listado para el laqueador generado")
