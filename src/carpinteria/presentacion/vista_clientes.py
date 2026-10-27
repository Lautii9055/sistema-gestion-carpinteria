"""Clientes: listado con búsqueda y formulario de alta/modificación (RF-04 y RF-06)."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.entidades import Cliente, ClienteResumen, Obra
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.tema import SANS_MEDIA

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

ESPERA_BUSQUEDA = 0.3  # segundos sin tipear antes de buscar (no se consulta la base por cada letra)
FILTRO_TELEFONO = ft.InputFilter(regex_string=r"^[0-9+()\- ]*$", allow=True, replacement_string="")


# ---------- formulario de cliente (alta y modificación) ----------
def campos_obra(p: tema.Paleta, obra: Obra | None = None) -> tuple[list[ft.Control], callable]:
    """Campos de una obra y una función que arma la Obra con lo escrito."""
    direccion = tema.campo("Dirección", p, value=obra.direccion if obra else "",
                           hint_text="Calle y número", max_length=150)
    localidad = tema.campo("Localidad", p, value=obra.localidad if obra else "", max_length=80,
                           capitalization=ft.TextCapitalization.WORDS)
    alias = tema.campo("Nombre de la obra (opcional)", p, value=(obra.alias or "") if obra else "",
                       hint_text="por ejemplo: Casa Nordelta", max_length=100)

    def leer(id_obra: int | None, id_cliente: int | None) -> Obra:
        return Obra(id_obra, id_cliente, direccion.value or "", localidad.value or "",
                    alias=alias.value, observaciones=obra.observaciones if obra else None)

    return [direccion, ft.Row([ft.Container(localidad, expand=3), ft.Container(alias, expand=4)],
                              spacing=12)], leer


def abrir_formulario(app: Aplicacion, cliente: Cliente | None = None) -> None:
    """Alta (cliente=None, con primera obra opcional) o modificación de un cliente."""
    p = app.paleta
    es_alta = cliente is None
    nombre = tema.campo("Nombre", p, value="" if es_alta else cliente.nombre, autofocus=True,
                        max_length=50, capitalization=ft.TextCapitalization.WORDS)
    apellido = tema.campo("Apellido", p, value="" if es_alta else cliente.apellido,
                          max_length=50, capitalization=ft.TextCapitalization.WORDS)
    telefono = tema.campo("Teléfono", p, value="" if es_alta else cliente.telefono, max_length=25,
                          keyboard_type=ft.KeyboardType.PHONE, input_filter=FILTRO_TELEFONO,
                          hint_text="por ejemplo: 11 4567-8901")
    email = tema.campo("Email (opcional)", p, value="" if es_alta else (cliente.email or ""),
                       max_length=100, keyboard_type=ft.KeyboardType.EMAIL)
    observaciones = tema.campo("Observaciones (opcional)", p, multiline=True, min_lines=2, max_lines=4,
                               max_length=500,
                               value="" if es_alta else (cliente.observaciones or ""))
    caja_error = ft.Container(visible=False)

    controles: list[ft.Control] = [
        caja_error,
        ft.Row([ft.Container(nombre, expand=True), ft.Container(apellido, expand=True)], spacing=12),
        ft.Row([ft.Container(telefono, expand=True), ft.Container(email, expand=True)], spacing=12),
        observaciones,
    ]

    leer_obra = None
    cargar_obra = None
    if es_alta:
        # Divulgación progresiva: la obra se puede cargar ahora o después, desde la ficha.
        campos, leer_obra = campos_obra(p)
        bloque_obra = ft.Column(campos, spacing=12, visible=True)

        def alternar(_):
            bloque_obra.visible = bool(cargar_obra.value)
            app.page.update()

        cargar_obra = ft.Checkbox(label="Cargar ahora la dirección de la obra", value=True,
                                  active_color=p.acento, check_color=p.sobre_acento,
                                  label_style=ft.TextStyle(color=p.texto, size=15), on_change=alternar)
        controles += [ft.Divider(color=p.borde), cargar_obra, bloque_obra]

    def guardar(_=None) -> None:
        datos = Cliente(None if es_alta else cliente.id, nombre.value or "", apellido.value or "",
                        telefono.value or "", email.value, observaciones.value,
                        True if es_alta else cliente.es_activo)
        if es_alta:
            obra = leer_obra(None, None) if cargar_obra.value else None
            resultado, error = app.ejecutar(app.clientes.crear, datos, obra)
        else:
            resultado, error = app.ejecutar(app.clientes.actualizar, datos)
        if error:
            caja_error.content = tema.aviso(error, p)
            caja_error.visible = True
            app.page.update()
            return
        app.cerrar_dialogo()
        id_cliente = resultado if es_alta else cliente.id
        app.ir_a("cliente", id_cliente=id_cliente)
        componentes.aviso_flotante(app.page, "Cliente guardado." if es_alta else "Cambios guardados.", p)

    nombre.on_submit = lambda _: apellido.focus()
    apellido.on_submit = lambda _: telefono.focus()
    telefono.on_submit = lambda _: email.focus()
    app.mostrar_dialogo(componentes.dialogo(
        p, "Nuevo cliente" if es_alta else "Editar cliente",
        ft.Column(controles, spacing=14, tight=True, scroll=ft.ScrollMode.AUTO),
        [componentes.boton_cancelar(p, lambda _: app.cerrar_dialogo()),
         tema.boton_principal("Guardar cliente" if es_alta else "Guardar cambios", p, guardar)],
        ancho=560,
    ))


# ---------- listado ----------
def _fila(app: Aplicacion, resumen: ClienteResumen) -> ft.Container:
    p = app.paleta
    c = resumen.cliente
    color_nombre = p.texto if c.es_activo else p.texto_tenue
    if resumen.cantidad_obras == 0:
        detalle_obras = "Sin obras cargadas"
    elif resumen.cantidad_obras == 1:
        detalle_obras = resumen.primera_direccion
    else:
        detalle_obras = f"{resumen.primera_direccion} y {resumen.cantidad_obras - 1} obra(s) más"

    titulo = [ft.Text(c.nombre_completo, font_family=SANS_MEDIA, size=16, color=color_nombre)]
    if not c.es_activo:
        titulo.append(componentes.etiqueta_estado("Dado de baja", p.texto_tenue, p.fondo))

    return ft.Container(
        content=ft.Row([
            componentes.avatar(c.nombre_completo, p, 44),
            ft.Column([
                ft.Row(titulo, spacing=10),
                ft.Text(detalle_obras, size=13, color=p.texto_tenue, max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS),
            ], spacing=4, expand=True),
            ft.Row([ft.Icon(ft.Icons.PHONE_OUTLINED, size=16, color=p.texto_tenue),
                    ft.Text(c.telefono, size=14, color=p.texto_secundario)], spacing=6, tight=True),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=p.texto_tenue),
        ], spacing=16),
        bgcolor=p.superficie, border=ft.Border.all(1, p.borde), border_radius=14,
        padding=ft.Padding.symmetric(horizontal=18, vertical=14),
        on_click=lambda _: app.ir_a("cliente", id_cliente=c.id), ink=True,
        tooltip="Ver la ficha del cliente",
    )


def construir(app: Aplicacion) -> ft.Control:
    p = app.paleta
    # Lo último buscado se recuerda al volver desde una ficha.
    estado = app.recuerdos.setdefault("clientes", {"texto": "", "inactivos": False})

    resultados = ft.Column(spacing=10)
    contador = ft.Text("", size=13, color=p.texto_tenue)
    # Sin max_length a propósito (no muestra contador); el servicio limita a 5 palabras.
    busqueda = tema.campo("Buscar", p, value=estado["texto"], autofocus=True,
                          prefix_icon=ft.Icons.SEARCH,
                          hint_text="Nombre, apellido, teléfono, email o dirección")
    ver_bajas = ft.Switch(label="Mostrar dados de baja", value=estado["inactivos"],
                          active_color=p.acento,
                          label_text_style=ft.TextStyle(color=p.texto_secundario, size=14))
    boton_nuevo = componentes.boton_con_icono("Nuevo cliente", ft.Icons.PERSON_ADD_ALT_1_OUTLINED, p,
                                              lambda _: abrir_formulario(app))

    def cargar() -> None:
        lista, error = app.ejecutar(app.clientes.buscar, estado["texto"], estado["inactivos"])
        if error:
            resultados.controls = [tema.aviso(error, p)]
            contador.value = ""
        elif not lista and not estado["texto"]:
            resultados.controls = [componentes.estado_vacio(
                ft.Icons.PEOPLE_OUTLINE, "Todavía no hay clientes",
                "Cargá el primero con su teléfono y la dirección de la obra.", p,
                componentes.boton_con_icono("Nuevo cliente", ft.Icons.PERSON_ADD_ALT_1_OUTLINED, p,
                                            lambda _: abrir_formulario(app)))]
            contador.value = ""
        elif not lista:
            resultados.controls = [componentes.estado_vacio(
                ft.Icons.SEARCH_OFF, "Sin resultados",
                f"No encontramos clientes con “{estado['texto']}”. Probá con menos palabras "
                "o con parte del teléfono.", p)]
            contador.value = ""
        else:
            resultados.controls = [_fila(app, r) for r in lista]
            contador.value = (f"{len(lista)} cliente{'s' if len(lista) != 1 else ''}"
                              + (" (se muestran los primeros)" if len(lista) >= 100 else ""))
        app.page.update()

    pedido = {"numero": 0}

    async def buscar_cuando_deje_de_tipear(numero: int) -> None:
        await asyncio.sleep(ESPERA_BUSQUEDA)
        if numero == pedido["numero"]:  # si siguió tipeando, esta búsqueda ya no sirve
            cargar()

    def al_tipear(_) -> None:
        estado["texto"] = busqueda.value or ""
        pedido["numero"] += 1
        app.page.run_task(buscar_cuando_deje_de_tipear, pedido["numero"])

    def al_cambiar_bajas(_) -> None:
        estado["inactivos"] = bool(ver_bajas.value)
        cargar()

    busqueda.on_change = al_tipear
    busqueda.on_submit = lambda _: cargar()
    ver_bajas.on_change = al_cambiar_bajas
    app.al_mostrar(cargar)

    return ft.Column([
        componentes.encabezado_seccion(
            "Taller", "Clientes",
            "Buscá por cualquier dato: podés escribir varias palabras o una parte del teléfono.",
            p, boton_nuevo),
        busqueda,
        ft.Row([contador, ft.Container(expand=True), ver_bajas]),
        resultados,
    ], spacing=16)
