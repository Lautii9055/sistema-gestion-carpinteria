"""Ficha del cliente: datos, obras e historial de trabajos (RF-05 y RF-07)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import Cliente, Obra, ObraConTrabajos
from carpinteria.presentacion import componentes, tema, vista_clientes
from carpinteria.presentacion.componentes import fecha_larga
from carpinteria.presentacion.tema import SANS_MEDIA

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion


def _abrir_obra(app: Aplicacion, id_cliente: int, obra: Obra | None = None) -> None:
    """Agregar (obra=None) o editar una obra del cliente."""
    p = app.paleta
    campos, leer = vista_clientes.campos_obra(p, obra)
    campos[0].autofocus = True
    observaciones = tema.campo("Observaciones (opcional)", p, multiline=True, min_lines=2,
                               max_lines=4, max_length=500,
                               value=(obra.observaciones or "") if obra else "",
                               hint_text="Acceso, horarios, portero, etc.")
    caja_error = ft.Container(visible=False)

    def guardar(_=None) -> None:
        datos = leer(obra.id if obra else None, id_cliente)
        datos = Obra(datos.id, datos.id_cliente, datos.direccion, datos.localidad,
                     alias=datos.alias, observaciones=observaciones.value)
        funcion = app.clientes.actualizar_obra if obra else app.clientes.agregar_obra
        _, error = app.ejecutar(funcion, datos)
        if error:
            caja_error.content = tema.aviso(error, p)
            caja_error.visible = True
            app.page.update()
            return
        app.cerrar_dialogo()
        app.ir_a("cliente", id_cliente=id_cliente)
        componentes.aviso_flotante(app.page, "Obra guardada." if obra is None else "Cambios guardados.", p)

    app.mostrar_dialogo(componentes.dialogo(
        p, "Editar obra" if obra else "Nueva obra",
        ft.Column([caja_error, *campos, observaciones], spacing=14, tight=True),
        [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo()),
         tema.boton_principal("Guardar obra", p, guardar)],
        ancho=560,
    ))


def _cambiar_estado(app: Aplicacion, cliente: Cliente) -> None:
    p = app.paleta

    def accion() -> None:
        funcion = app.clientes.dar_de_baja if cliente.es_activo else app.clientes.reactivar
        _, error = app.ejecutar(funcion, cliente.id)
        if error:
            componentes.aviso_flotante(app.page, error, p)
            return
        app.ir_a("cliente", id_cliente=cliente.id)
        componentes.aviso_flotante(
            app.page, f"{cliente.nombre_completo} quedó {'dado de baja' if cliente.es_activo else 'activo'}.", p)

    if not cliente.es_activo:
        accion()
        return
    app.mostrar_dialogo(componentes.dialogo(
        p, "Dar de baja",
        ft.Text(f"{cliente.nombre_completo} deja de aparecer en el listado y no se le pueden cargar "
                "trabajos nuevos. Sus obras y su historial se conservan, y se puede reactivar cuando "
                "quieras.", size=15, color=p.texto_secundario),
        [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo()),
         tema.boton_principal("Dar de baja", p, lambda _: (app.cerrar_dialogo(), accion()))],
    ))


def _tarjeta_obra(app: Aplicacion, cliente: Cliente, item: ObraConTrabajos) -> ft.Container:
    p = app.paleta
    obra = item.obra
    ubicacion = f"{obra.direccion}, {obra.localidad}"

    if item.trabajos:
        historial: list[ft.Control] = [
            ft.Row([
                ft.Text(f"#{t.id}", size=13, color=p.texto_tenue, width=48),
                ft.Text(t.descripcion, size=15, color=p.texto, expand=True, max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS),
                componentes.etiqueta_estado(t.estado, p.acento_texto, p.superficie_alta),
                ft.Text(f"{t.fecha_alta:%d/%m/%Y}", size=13, color=p.texto_tenue, width=84,
                        text_align=ft.TextAlign.RIGHT),
            ], spacing=12)
            for t in item.trabajos
        ]
    else:
        historial = [ft.Text("Todavía no tiene trabajos.", size=14, color=p.texto_tenue)]

    return componentes.tarjeta(
        ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.HOME_WORK_OUTLINED, color=p.acento_texto, size=22),
                ft.Column([
                    ft.Text(obra.titulo, font_family=SANS_MEDIA, size=17, color=p.texto),
                    *([ft.Text(ubicacion, size=14, color=p.texto_secundario, selectable=True)]
                      if obra.alias else [ft.Text(obra.localidad, size=14, color=p.texto_secundario)]),
                ], spacing=2, expand=True),
                ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=p.texto_secundario,
                              tooltip="Editar la obra", on_click=lambda _: _abrir_obra(app, cliente.id, obra)),
            ], spacing=12),
            *([ft.Text(obra.observaciones, size=14, color=p.texto_tenue, italic=True)]
              if obra.observaciones else []),
            ft.Divider(color=p.borde, height=1),
            ft.Row([
                tema.etiqueta_superior("Trabajos", p),
                ft.Container(expand=True),
                ft.TextButton(
                    content=ft.Row([ft.Icon(ft.Icons.ADD, size=18, color=p.texto_tenue),
                                    ft.Text("Nuevo trabajo", color=p.texto_tenue, size=14)],
                                   spacing=4, tight=True),
                    disabled=True, tooltip="Disponible cuando esté el módulo de trabajos"),
            ]),
            *historial,
        ], spacing=12),
        p, padding=20,
    )


def construir(app: Aplicacion, id_cliente: int) -> ft.Control:
    p = app.paleta
    volver = ft.TextButton(
        content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, size=18, color=p.texto_secundario),
                        ft.Text("Clientes", color=p.texto_secundario, size=14)], spacing=6, tight=True),
        on_click=lambda _: app.ir_a("clientes"),
    )
    ficha, error = app.ejecutar(app.clientes.ficha, id_cliente)
    if error:
        return ft.Column([volver, tema.aviso(error, p)], spacing=16)

    c = ficha.cliente
    etiquetas = [componentes.etiqueta_estado("Activo", p.exito, p.superficie_alta) if c.es_activo
                 else componentes.etiqueta_estado("Dado de baja", p.texto_tenue, p.fondo)]
    acciones = ft.Row([
        componentes.boton_con_icono("Editar datos", ft.Icons.EDIT_OUTLINED, p,
                                    lambda _: vista_clientes.abrir_formulario(app, c), principal=False),
        ft.TextButton(
            content=ft.Text("Dar de baja" if c.es_activo else "Reactivar", size=14,
                            color=p.error_texto if c.es_activo else p.acento_texto),
            on_click=lambda _: _cambiar_estado(app, c), height=44),
    ], spacing=8, tight=True)

    encabezado = ft.Row([
        componentes.avatar(c.nombre_completo, p, 64),
        ft.Column([
            tema.etiqueta_superior(f"Cliente #{c.id}", p),
            ft.Row([tema.titulo(c.nombre_completo, p, 40), *etiquetas], spacing=14,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=2, expand=True),
        acciones,
    ], spacing=20)

    datos = componentes.tarjeta(
        ft.Column([
            tema.etiqueta_superior("Contacto", p),
            componentes.dato(ft.Icons.PHONE_OUTLINED, c.telefono, p),
            componentes.dato(ft.Icons.MAIL_OUTLINE, c.email, p, vacio="Sin email"),
            *([ft.Divider(color=p.borde, height=1),
               tema.etiqueta_superior("Observaciones", p),
               ft.Text(c.observaciones, size=15, color=p.texto_secundario, selectable=True)]
              if c.observaciones else []),
        ], spacing=12),
        p, padding=20,
    )

    obras: list[ft.Control] = ([_tarjeta_obra(app, c, o) for o in ficha.obras] if ficha.obras
                               else [componentes.estado_vacio(
                                   ft.Icons.HOME_WORK_OUTLINED, "Sin obras",
                                   "Agregá la dirección donde se va a instalar el trabajo.", p)])
    total_trabajos = sum(len(o.trabajos) for o in ficha.obras)
    resumen = (f"{len(ficha.obras)} obra{'s' if len(ficha.obras) != 1 else ''} · "
               f"{total_trabajos} trabajo{'s' if total_trabajos != 1 else ''}")

    return ft.Column([
        volver,
        encabezado,
        datos,
        ft.Row([
            ft.Column([tema.titulo("Obras", p, 30),
                       ft.Text(resumen, size=14, color=p.texto_tenue)], spacing=0, expand=True),
            componentes.boton_con_icono("Agregar obra", ft.Icons.ADD_HOME_OUTLINED, p,
                                        lambda _: _abrir_obra(app, c.id), principal=False),
        ], vertical_alignment=ft.CrossAxisAlignment.END),
        *obras,
    ], spacing=16)
