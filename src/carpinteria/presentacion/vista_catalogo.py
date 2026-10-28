"""Pestañas de Materiales para filos, lacas, estilos de frente y guías."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.catalogo import SIN_FILO, formato, texto_regla
from carpinteria.negocio.entidades import EstiloFrente, TipoFilo, TipoGuia
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.tema import SANS_MEDIA
from carpinteria.presentacion.vista_materiales import (FILTRO_NUMERO, _acciones, _cambiar_estado, _confirmar_eliminar,
                                                       _dialogo, _etiquetas, _fila, _hacer, _insignia, _recargar)

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

FILTRO_CON_SIGNO = ft.InputFilter(regex_string=r"^-?[0-9.,]{0,6}$", allow=True, replacement_string="")


def _par(a: ft.Control, b: ft.Control, c: ft.Control | None = None) -> ft.Row:
    return ft.Row([ft.Container(x, expand=True) for x in (a, b, c) if x is not None], spacing=12,
                  vertical_alignment=ft.CrossAxisAlignment.START)


def _titulo_seccion(app: Aplicacion, texto: str, *acciones: ft.Control) -> ft.Row:
    p = app.paleta
    return ft.Row([ft.Text(texto, font_family=tema.SERIF, size=26, color=p.texto), ft.Container(expand=True),
                   *acciones], spacing=8)


def _boton_texto(app: Aplicacion, texto: str, al_tocar, icono=ft.Icons.ADD) -> ft.TextButton:
    p = app.paleta
    return ft.TextButton(content=ft.Row([ft.Icon(icono, size=18, color=p.acento_texto),
                                         ft.Text(texto, size=14, color=p.acento_texto)], spacing=4, tight=True),
                         on_click=al_tocar)


# ---------- filos ----------
def dialogo_filo(app: Aplicacion, filo: TipoFilo | None = None) -> None:
    p = app.paleta
    nombre = tema.campo("Nombre", p, value=filo.nombre if filo else "", max_length=30, autofocus=True,
                        hint_text="por ejemplo: 1 mm")
    espesor = tema.campo("Espesor (mm)", p, value=formato(filo.espesor_mm) if filo else "", input_filter=FILTRO_NUMERO)
    descuento = tema.campo("Descuento por canto (cm)", p, value=formato(filo.descuento_cm) if filo else "",
                           input_filter=FILTRO_NUMERO, helper="Se resta en la medida de corte por cada canto con filo")
    aviso = ([tema.aviso("Este filo ya se usa: el espesor y el descuento no se pueden cambiar.", p, tipo="info")]
             if filo and filo.en_uso else [])
    _dialogo(app, "Editar filo" if filo else "Nuevo tipo de filo", [*aviso, nombre, _par(espesor, descuento)],
             "Guardar", lambda: _hacer(app, app.catalogo.guardar_filo, filo.id if filo else None, nombre.value,
                                       espesor.value, descuento.value, mensaje="Filo guardado."))


def vista_filos(app: Aplicacion, estado: dict) -> list[ft.Control]:
    p = app.paleta
    filos, error = app.ejecutar(app.catalogo.filos)
    if error:
        return [tema.aviso(error, p)]
    filas = []
    for f in filos:
        acciones: list[ft.Control] = [ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=p.texto_secundario,
                                                    tooltip="Editar", on_click=lambda _, f=f: dialogo_filo(app, f),
                                                    visible=f.nombre != SIN_FILO)]
        if not f.en_uso and f.nombre != SIN_FILO:
            acciones.append(ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE, icon_color=p.texto_tenue, tooltip="Eliminar (nunca se usó)",
                on_click=lambda _, f=f: _confirmar_eliminar(app, f"el filo {f.nombre}", app.catalogo.eliminar_filo,
                                                            f.id)))
        detalle = ("Para piezas sin filo y las laqueadas (no se modifica)" if f.nombre == SIN_FILO
                   else f"Descuento por canto: {formato(f.descuento_cm)} cm")
        filas.append(_fila(app, _insignia(app, formato(f.espesor_mm), "mm"), f.nombre, detalle,
                           _etiquetas(app, True, f.en_uso), acciones, True))
    return filas


# ---------- lacas ----------
def dialogo_marca_pintura(app: Aplicacion, marca=None) -> None:
    p = app.paleta
    nombre = tema.campo("Marca de pintura", p, value=marca.nombre if marca else "", max_length=50, autofocus=True,
                        hint_text="por ejemplo: Alba, Sherwin Williams")
    _dialogo(app, "Editar marca" if marca else "Nueva marca de pintura", [nombre], "Guardar",
             lambda: _hacer(app, app.catalogo.guardar_marca_pintura, marca.id if marca else None, nombre.value,
                            mensaje="Marca guardada."))


def dialogo_color_laca(app: Aplicacion, color=None, id_marca: int | None = None) -> None:
    p = app.paleta
    marcas, _ = app.ejecutar(app.catalogo.marcas_pintura, True)
    opciones = [(str(m.id), m.nombre) for m in marcas or [] if m.es_activo or (color and m.id == color.id_marca)]
    if not opciones:
        componentes.aviso_flotante(app.page, "Primero cargá una marca de pintura.", p)
        return
    marca = componentes.desplegable("Marca", opciones, str(color.id_marca if color else (id_marca or opciones[0][0])), p)
    nombre = tema.campo("Nombre del color", p, value=(color.nombre or "") if color else "", max_length=60,
                        hint_text="por ejemplo: Gris Topo")
    codigo = tema.campo("Código", p, value=(color.codigo or "") if color else "", max_length=30,
                        hint_text="por ejemplo: SW 7062")
    _dialogo(app, "Editar color de laca" if color else "Nuevo color de laca", [marca, _par(nombre, codigo)], "Guardar",
             lambda: _hacer(app, app.catalogo.guardar_color_laca, color.id if color else None,
                            int(marca.value) if marca.value else None, nombre.value, codigo.value,
                            mensaje="Color guardado."))


def dialogo_terminacion(app: Aplicacion, terminacion=None) -> None:
    p = app.paleta
    nombre = tema.campo("Terminación", p, value=terminacion.nombre if terminacion else "", max_length=30,
                        autofocus=True, hint_text="por ejemplo: Satinado")
    _dialogo(app, "Editar terminación" if terminacion else "Nueva terminación", [nombre], "Guardar",
             lambda: _hacer(app, app.catalogo.guardar_terminacion, terminacion.id if terminacion else None,
                            nombre.value, mensaje="Terminación guardada."))


def vista_lacas(app: Aplicacion, estado: dict) -> list[ft.Control]:
    p = app.paleta
    c = app.catalogo
    terminaciones, e1 = app.ejecutar(c.terminaciones, estado["bajas"])
    marcas, e2 = app.ejecutar(c.marcas_pintura, estado["bajas"])
    colores, e3 = app.ejecutar(c.colores_laca, estado["texto"], True)
    if e1 or e2 or e3:
        return [tema.aviso(e1 or e2 or e3, p)]

    controles: list[ft.Control] = [_titulo_seccion(app, "Terminaciones",
                                                   _boton_texto(app, "Terminación", lambda _: dialogo_terminacion(app)))]
    for t in terminaciones:
        controles.append(_fila(app, _insignia(app, t.nombre[:2].upper()), t.nombre, "Obligatoria en toda pieza laqueada",
                               _etiquetas(app, t.es_activo, t.en_uso),
                               _acciones(app, t.es_activo, t.en_uso, lambda t=t: dialogo_terminacion(app, t),
                                         lambda t=t: _cambiar_estado(app, c.cambiar_estado_terminacion, t.id,
                                                                     not t.es_activo, t.nombre),
                                         lambda t=t: _confirmar_eliminar(app, f"la terminación {t.nombre}",
                                                                         c.eliminar_terminacion, t.id)),
                               t.es_activo))
    for m in marcas:
        propios = [x for x in colores if x.id_marca == m.id and (estado["bajas"] or x.es_activo)]
        if estado["texto"] and not propios:
            continue
        controles.append(ft.Row([
            ft.Text(m.nombre, font_family=tema.SERIF, size=26, color=p.texto if m.es_activo else p.texto_tenue),
            *_etiquetas(app, m.es_activo, False), ft.Container(expand=True),
            ft.Container(_boton_texto(app, "Color", lambda _, i=m.id: dialogo_color_laca(app, id_marca=i)),
                         visible=m.es_activo),
            *_acciones(app, m.es_activo, any(x.id_marca == m.id for x in colores),
                       lambda m=m: dialogo_marca_pintura(app, m),
                       lambda m=m: _cambiar_estado(app, c.cambiar_estado_marca_pintura, m.id, not m.es_activo, m.nombre),
                       lambda m=m: _confirmar_eliminar(app, f"la marca {m.nombre}", c.eliminar_marca_pintura, m.id)),
        ], spacing=8))
        if not propios:
            controles.append(ft.Text("Sin colores cargados.", size=14, color=p.texto_tenue))
        for x in propios:
            controles.append(_fila(
                app, _insignia(app, (x.codigo or x.nombre or "?")[:4].upper()), x.descripcion, f"Laca {m.nombre}",
                _etiquetas(app, x.es_activo, x.en_uso),
                _acciones(app, x.es_activo, x.en_uso, lambda x=x: dialogo_color_laca(app, x),
                          lambda x=x: _cambiar_estado(app, c.cambiar_estado_color_laca, x.id, not x.es_activo,
                                                      x.descripcion),
                          lambda x=x: _confirmar_eliminar(app, f"el color {x.descripcion}", c.eliminar_color_laca,
                                                          x.id)),
                x.es_activo))
    return controles


# ---------- estilos de frente ----------
def dialogo_estilo(app: Aplicacion, estilo: EstiloFrente | None = None) -> None:
    p = app.paleta
    nombre = tema.campo("Nombre", p, value=estilo.nombre if estilo else "", max_length=50, autofocus=True,
                        hint_text="por ejemplo: Con tirador")
    superior = tema.campo("Luz superior (cm)", p, value=formato(estilo.luz_superior) if estilo else "",
                          input_filter=FILTRO_CON_SIGNO)
    inferior = tema.campo("Luz inferior (cm)", p, value=formato(estilo.luz_inferior) if estilo else "",
                          input_filter=FILTRO_CON_SIGNO)
    entre = tema.campo("Entre frentes (cm)", p, value=formato(estilo.luz_entre_frentes) if estilo else "",
                       input_filter=FILTRO_NUMERO)
    descripcion = tema.campo("Indicaciones (opcional)", p, value=(estilo.descripcion or "") if estilo else "",
                             multiline=True, min_lines=2, max_lines=4, max_length=200)
    aviso = ([tema.aviso("Ya se usa en módulos: los cambios se aplican a los módulos que se calculen de ahora en más.",
                         p, tipo="info")] if estilo and estilo.en_uso else [])
    _dialogo(app, "Editar estilo de frente" if estilo else "Nuevo estilo de frente", [
        *aviso, nombre, _par(superior, inferior, entre),
        ft.Text("Una luz negativa significa que el frente sobresale (ej.: alacena, −1,3 abajo).", size=13,
                color=p.texto_tenue),
        descripcion], "Guardar",
        lambda: _hacer(app, app.catalogo.guardar_estilo, estilo.id if estilo else None, nombre.value, superior.value,
                       inferior.value, entre.value, descripcion.value, mensaje="Estilo guardado."), 600)


def vista_estilos(app: Aplicacion, estado: dict) -> list[ft.Control]:
    p = app.paleta
    c = app.catalogo
    estilos, error = app.ejecutar(c.estilos, estado["bajas"])
    if error:
        return [tema.aviso(error, p)]
    return [_fila(app, _insignia(app, formato(e.luz_entre_frentes), "entre"), e.nombre,
                  f"Arriba {formato(e.luz_superior)} · abajo {formato(e.luz_inferior)} · entre frentes "
                  f"{formato(e.luz_entre_frentes)} cm" + (f" — {e.descripcion}" if e.descripcion else ""),
                  _etiquetas(app, e.es_activo, e.en_uso),
                  _acciones(app, e.es_activo, e.en_uso, lambda e=e: dialogo_estilo(app, e),
                            lambda e=e: _cambiar_estado(app, c.cambiar_estado_estilo, e.id, not e.es_activo, e.nombre),
                            lambda e=e: _confirmar_eliminar(app, f"el estilo {e.nombre}", c.eliminar_estilo, e.id)),
                  e.es_activo) for e in estilos]


# ---------- guías ----------
def dialogo_guia(app: Aplicacion, guia: TipoGuia | None = None) -> None:
    p = app.paleta
    nombre = tema.campo("Nombre", p, value=guia.nombre if guia else "", max_length=50, autofocus=True,
                        hint_text="por ejemplo: Lateral oculto Häfele")
    marca = tema.campo("Marca (opcional)", p, value=(guia.marca or "") if guia else "", max_length=50)
    espacio = tema.campo("Espacio adicional (cm)", p, value=formato(guia.espacio_adicional) if guia else "0",
                         input_filter=FILTRO_NUMERO, helper="Profundidad extra que necesita la guía")
    controles: list[ft.Control] = [nombre, _par(marca, espacio)]
    base = None
    if guia is None:
        guias, _ = app.ejecutar(app.catalogo.guias, True)
        opciones = [(str(g.id), g.nombre) for g in guias or []]
        base = componentes.desplegable("Basada en", opciones, opciones[0][0] if opciones else "", p)
        controles += [base, ft.Text("Copia las piezas que lleva el cajón con esa guía. Para una guía lateral oculta de "
                                    "otra marca, basala en otra oculta y después cargá el alto del contrafrente.",
                                    size=13, color=p.texto_tenue)]
    _dialogo(app, "Editar guía" if guia else "Nueva guía", controles, "Guardar",
             lambda: _hacer(app, app.catalogo.guardar_guia, guia.id if guia else None, nombre.value, marca.value,
                            espacio.value, int(base.value) if base and base.value else None,
                            mensaje="Guía guardada."), 580)


def _dialogo_largo(app: Aplicacion, guia: TipoGuia) -> None:
    p = app.paleta
    largo = tema.campo("Largo (cm)", p, autofocus=True, input_filter=FILTRO_NUMERO, hint_text="por ejemplo: 45")
    _dialogo(app, f"Largo de {guia.nombre}", [largo, ft.Text("Los largos comerciales que se consiguen; el sistema "
                                                             "propone el que entra según la profundidad del módulo.",
                                                             size=13, color=p.texto_tenue)],
             "Agregar", lambda: _hacer(app, app.catalogo.agregar_largo, guia.id, largo.value, mensaje="Largo agregado."),
             440)


def _dialogo_contrafrente(app: Aplicacion, guia: TipoGuia) -> None:
    p = app.paleta
    actual = app.catalogo.alto_contrafrente(guia)
    alto = tema.campo("Alto del contrafrente (cm)", p, value=formato(actual), autofocus=True, input_filter=FILTRO_NUMERO)
    _dialogo(app, "Alto del contrafrente", [
        ft.Text(f"En {guia.nombre} el contrafrente mide (ancho interior − 8,7) × este alto, que depende de la marca.",
                size=15, color=p.texto_secundario), alto], "Guardar",
        lambda: _hacer(app, app.catalogo.guardar_alto_contrafrente, guia.id, alto.value, mensaje="Alto guardado."), 480)


def _quitar_largo(app: Aplicacion, guia: TipoGuia, largo: Decimal) -> None:
    _, error = app.ejecutar(app.catalogo.quitar_largo, guia.id, largo)
    if error:
        componentes.aviso_flotante(app.page, error, app.paleta)
        return
    _recargar(app, f"Largo {formato(largo)} cm quitado.")


def _tarjeta_guia(app: Aplicacion, g: TipoGuia) -> ft.Container:
    p = app.paleta
    c = app.catalogo
    largos = ft.Row([
        *[ft.Container(content=ft.Row([ft.Text(f"{formato(x)} cm", size=13, color=p.texto),
                                       ft.IconButton(icon=ft.Icons.CLOSE, icon_size=14, icon_color=p.texto_tenue,
                                                     tooltip="Quitar", width=28, height=28,
                                                     on_click=lambda _, x=x: _quitar_largo(app, g, x))],
                                      spacing=0, tight=True),
                       bgcolor=p.superficie_alta, border_radius=99, padding=ft.Padding.only(left=12, right=2))
          for x in g.largos],
        _boton_texto(app, "Largo", lambda _: _dialogo_largo(app, g)),
    ], spacing=6, wrap=True)
    contenido: list[ft.Control] = [
        ft.Row([ft.Column([ft.Row([ft.Text(g.nombre, size=17, font_family=SANS_MEDIA,
                                           color=p.texto if g.es_activo else p.texto_tenue),
                                   *_etiquetas(app, g.es_activo, g.en_uso)], spacing=8),
                           ft.Text(("Marca " + g.marca + " · " if g.marca else "")
                                   + f"espacio adicional {formato(g.espacio_adicional)} cm", size=13,
                                   color=p.texto_tenue)], spacing=2, expand=True),
                *_acciones(app, g.es_activo, g.en_uso, lambda: dialogo_guia(app, g),
                           lambda: _cambiar_estado(app, c.cambiar_estado_guia, g.id, not g.es_activo, g.nombre),
                           lambda: _confirmar_eliminar(app, f"la guía {g.nombre}", c.eliminar_guia, g.id))]),
        tema.etiqueta_superior("Largos disponibles", p),
        largos if g.largos else ft.Row([ft.Text("Todavía no se cargaron los largos.", size=14, color=p.texto_tenue),
                                        _boton_texto(app, "Largo", lambda _: _dialogo_largo(app, g))]),
        tema.etiqueta_superior("Piezas del cajón", p),
        *[ft.Row([ft.Text(x.pieza, size=14, color=p.texto, width=200), ft.Text(texto_regla(x), size=14,
                                                                              color=p.texto_secundario, expand=True)])
          for x in g.piezas],
    ]
    if c.usa_contrafrente_fijo(g):
        alto = c.alto_contrafrente(g)
        if alto is None:
            contenido.append(ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, size=18, color=p.error_texto),
                                     ft.Text("Falta el alto del contrafrente (dato de la marca): sin él no se puede "
                                             "calcular el cajón.", size=14, color=p.error_texto, expand=True),
                                     _boton_texto(app, "Cargar alto", lambda _: _dialogo_contrafrente(app, g),
                                                  ft.Icons.EDIT_OUTLINED)], spacing=8))
        else:
            contenido.append(_boton_texto(app, f"Cambiar alto del contrafrente ({formato(alto)} cm)",
                                          lambda _: _dialogo_contrafrente(app, g), ft.Icons.EDIT_OUTLINED))
    return componentes.tarjeta(ft.Column(contenido, spacing=10), p, padding=20)


def vista_guias(app: Aplicacion, estado: dict) -> list[ft.Control]:
    p = app.paleta
    guias, error = app.ejecutar(app.catalogo.guias, estado["bajas"])
    if error:
        return [tema.aviso(error, p)]
    return [_tarjeta_guia(app, g) for g in guias] or [
        componentes.estado_vacio(ft.Icons.VIEW_AGENDA_OUTLINED, "Sin guías", "No hay guías cargadas.", p)]
