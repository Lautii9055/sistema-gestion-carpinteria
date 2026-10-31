"""Asistente de carga de módulos, paso a paso (diseño 4, RF-14.1).

Una pregunta por pantalla; cada respuesta define las siguientes (una cajonera
no pregunta por techo, estantes, puertas ni pinos). El dibujo de la izquierda
se actualiza con cada dato y el último paso muestra todas las piezas antes de
guardar. Los filos se definen después, en "Piezas y filos".
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from carpinteria.negocio.catalogo import leer_decimal
from carpinteria.negocio.despiece import Despiece, Material
from carpinteria.negocio.entidades import CajonGuardado, ModuloGuardado
from carpinteria.negocio.materiales import formato_numero, leer_numero
from carpinteria.presentacion import componentes, tema
from carpinteria.presentacion.tema import SANS_MEDIA, SANS_SEMI
from carpinteria.presentacion.vista_muebles import FILTRO_NUMERO, mostrar_avisos, opciones_placas

if TYPE_CHECKING:
    from carpinteria.presentacion.app import Aplicacion

PASOS = ["Tipo", "Medidas", "Frentes", "Cajones", "Materiales", "Revisar"]
ARMADOS = [("Módulo", "Módulo", "Piso y techo enteros, laterales entre ellos. Puertas, estantes y cajones."),
           ("Cajonera con fajas de luz", "Cajonera · fajas de luz", "Laterales enteros y 4 fajas entre ellos."),
           ("Cajonera con laterales de luz", "Cajonera · laterales de luz", "4 fajas enteras y los laterales entre ellas."),
           ("Cajonera con piso y fajas de luz", "Cajonera con piso · fajas de luz",
            "Piso entero abajo; laterales sobre el piso y 2 fajas arriba entre ellos."),
           ("Cajonera con piso y laterales de luz", "Cajonera con piso · laterales de luz",
            "Piso entero abajo y 2 fajas enteras arriba; los laterales entre ellos.")]
FILTRO_CON_SIGNO = ft.InputFilter(regex_string=r"^-?[0-9.,]{0,6}$", allow=True, replacement_string="")
PERSONALIZADO = "personalizado"
LUZ_COSTADO, LUZ_JUNTO = "0,3", "0,15"     # costado libre / junto a otro módulo (entre los dos suman 0,3)
VETA_VERTICAL = {"Puerta", "Lateral", "Fondo", "Ajuste"}   # Tipo_Pieza.veta_vertical_tpi
GRUPOS = [("Estructura", {Material.ESTRUCTURA, Material.FONDO, Material.LISTON}), ("Frentes", {Material.FRENTES}),
          ("Cajones", {Material.CAJONES, Material.PISO_CAJON})]


# ---------- borrador ----------
def _f(numero: Decimal | None) -> str:
    return formato_numero(numero) if numero is not None else ""


def _borrador_nuevo(app: Aplicacion, id_mueble: int) -> dict:
    placas = opciones_placas(app)
    de_55 = opciones_placas(app, solo_espesor_mm=Decimal("5.5"))
    listones, _ = app.ejecutar(app.materiales.listones)
    return {"id": None, "id_mueble": id_mueble, "paso": 0, "armado": "Módulo", "nombre": "", "ancho": "", "alto": "",
            "profundidad": "", "lleva_techo": True, "ancho_faja": "10", "estantes": 0, "puertas": 0, "fondo": False,
            "pinos": False, "id_estilo": "", "luz_superior": "0", "luz_inferior": "0", "luz_entre": "0",
            "luz_izquierda": _luz_costado(app), "luz_derecha": _luz_costado(app),
            "cajones": 0, "id_guia": "", "largo_guia": "", "alto_caja": "12", "altos_frente": [], "id_placa_piso": "",
            "id_placa": placas[0][0] if placas else "", "id_placa_frentes": "", "id_placa_cajones": "",
            "id_placa_fondo": de_55[0][0] if de_55 else (placas[0][0] if placas else ""),
            "id_liston": str(listones[0].id) if listones else "",
            "id_color_laca": "", "id_terminacion": "", "rotar": set(), "cantidad": 1}


def _luz_costado(app: Aplicacion) -> str:
    """Luz a un costado libre (parámetro luz_lateral_frente, 0,3)."""
    reglas, _ = app.ejecutar(app.muebles.reglas)
    return _f(reglas.luz_lateral) if reglas else LUZ_COSTADO


def _luz_junto(app: Aplicacion) -> str:
    """Junto a otro módulo, la mitad: entre los dos frentes suman la luz de un costado."""
    reglas, _ = app.ejecutar(app.muebles.reglas)
    return _f(_mitad(reglas.luz_lateral)) if reglas else LUZ_JUNTO


def _mitad(luz: Decimal) -> Decimal:
    return (luz / 2).quantize(Decimal("0.01"))


def _borrador_de(m: ModuloGuardado) -> dict:
    c0 = m.cajones[0] if m.cajones else None
    return {"id": m.id, "id_mueble": m.id_mueble, "paso": 0, "armado": m.armado, "nombre": m.nombre or "",
            "ancho": _f(m.ancho), "alto": _f(m.alto), "profundidad": _f(m.profundidad), "lleva_techo": m.lleva_techo,
            "ancho_faja": _f(m.ancho_faja) or "10", "estantes": m.estantes, "puertas": m.puertas,
            "fondo": m.id_placa_fondo is not None, "pinos": m.id_liston is not None,
            "id_estilo": str(m.id_estilo) if m.id_estilo else PERSONALIZADO, "luz_superior": _f(m.luz_superior),
            "luz_inferior": _f(m.luz_inferior), "luz_entre": _f(m.luz_entre_frentes), "cajones": len(m.cajones),
            "luz_izquierda": _f(m.luz_izquierda), "luz_derecha": _f(m.luz_derecha),
            "id_guia": str(c0.id_guia) if c0 else "", "largo_guia": _f(c0.largo_guia) if c0 else "",
            "alto_caja": _f(c0.alto_caja) if c0 else "12", "altos_frente": [_f(c.alto_frente) for c in m.cajones],
            "id_placa_piso": str(c0.id_placa_piso) if c0 else "", "id_placa": str(m.id_placa),
            "id_placa_frentes": str(m.id_placa_frentes or ""), "id_placa_cajones": str(m.id_placa_cajones or ""),
            "id_placa_fondo": str(m.id_placa_fondo or ""), "id_liston": str(m.id_liston or ""),
            "id_color_laca": str(m.id_color_laca or ""), "id_terminacion": str(m.id_terminacion or ""),
            "rotar": set(m.rotar), "cantidad": m.cantidad}


def _id(valor: str) -> int | None:
    return int(valor) if valor else None


def a_modulo(b: dict) -> ModuloGuardado:
    """Lo cargado en el asistente → el módulo a calcular o guardar (valida los números)."""
    cajonera = b["armado"] != "Módulo"
    altos = (b["altos_frente"] + [""] * b["cajones"])[:b["cajones"]]
    cajones = tuple(
        CajonGuardado(None, int(b["id_guia"]) if b["id_guia"] else 0, int(b["id_placa_piso"] or b["id_placa"]),
                      leer_numero(b["alto_caja"], "el alto de la caja"), leer_numero(b["largo_guia"], "el largo de la guía"),
                      leer_numero(alto, f"el alto del frente del cajón {i}") if alto else None)
        for i, alto in enumerate(altos, 1))
    luz = lambda texto, campo: leer_decimal(texto or "0", campo, Decimal(-10), Decimal(10))  # noqa: E731
    return ModuloGuardado(
        b["id"], b["id_mueble"], b["armado"], int(b["id_placa"]) if b["id_placa"] else 0,
        leer_numero(b["ancho"], "el ancho"), leer_numero(b["alto"], "el alto"),
        leer_numero(b["profundidad"], "la profundidad"), nombre=b["nombre"] or None,
        id_estilo=_id(b["id_estilo"]) if b["id_estilo"] != PERSONALIZADO else None,
        id_placa_frentes=_id(b["id_placa_frentes"]), id_placa_cajones=_id(b["id_placa_cajones"]) if b["cajones"] else None,
        id_placa_fondo=_id(b["id_placa_fondo"]) if b["fondo"] else None,
        id_liston=_id(b["id_liston"]) if b["pinos"] and not cajonera and not b["lleva_techo"] else None,
        id_color_laca=_id(b["id_color_laca"]), id_terminacion=_id(b["id_terminacion"]) if b["id_color_laca"] else None,
        lleva_techo=False if cajonera else b["lleva_techo"],
        ancho_faja=leer_numero(b["ancho_faja"], "el ancho de las fajas") if cajonera else None,
        estantes=0 if cajonera else b["estantes"], puertas=0 if cajonera else b["puertas"],
        luz_superior=luz(b["luz_superior"], "la luz superior"), luz_inferior=luz(b["luz_inferior"], "la luz inferior"),
        luz_entre_frentes=leer_decimal(b["luz_entre"] or "0", "la luz entre frentes", Decimal(0), Decimal(10)),
        cajones=cajones, rotar=frozenset(b["rotar"]), cantidad=b.get("cantidad", 1),
        luz_izquierda=leer_decimal(b["luz_izquierda"] or "0", "la luz izquierda", Decimal(0), Decimal(10)),
        luz_derecha=leer_decimal(b["luz_derecha"] or "0", "la luz derecha", Decimal(0), Decimal(10)))


def _calcular(app: Aplicacion, b: dict) -> tuple[Despiece | None, str | None]:
    if b["cajones"]:
        _ajustar_guia(app, b)
    return app.ejecutar(lambda: app.muebles.previsualizar(a_modulo(b)))


def _guias(app: Aplicacion) -> list:
    guias, _ = app.ejecutar(app.catalogo.guias)
    return guias or []


def _largos_posibles(app: Aplicacion, b: dict) -> list[Decimal]:
    """Largos cargados de la guía elegida que entran en la caja (de mayor a menor)."""
    try:
        espesor = app.muebles.espesor_frentes(_id(b["id_placa_frentes"]), _id(b["id_placa"]))
        return app.muebles.largos_que_entran(int(b["id_guia"]), leer_numero(b["profundidad"], "x"), espesor)
    except Exception:
        return []


def _ajustar_guia(app: Aplicacion, b: dict, guias: list | None = None) -> None:
    """Guía por defecto (la telescópica, si está) y largo SIEMPRE de los cargados en
    Materiales que entran en la caja: si el elegido deja de entrar (cambió la
    profundidad o la guía), pasa al más largo que entra. Placa del piso: 5,5 mm con
    telescópica; con lateral oculto, la de la estructura."""
    guias = _guias(app) if guias is None else guias
    if not guias:
        return
    if not any(str(g.id) == b["id_guia"] for g in guias):
        telescopica = next((g for g in guias if any(x.pieza == "Lateral de cajón" for x in g.piezas)), None)
        b["id_guia"] = str((telescopica or guias[0]).id)
    posibles = [_f(x) for x in _largos_posibles(app, b)]
    if b["largo_guia"] not in posibles:
        b["largo_guia"] = posibles[0] if posibles else ""
    guia = next((g for g in guias if str(g.id) == b["id_guia"]), None)
    lleva_laterales = guia is not None and any(x.pieza == "Lateral de cajón" for x in guia.piezas)
    de_55 = opciones_placas(app, solo_espesor_mm=Decimal("5.5"))
    if lleva_laterales:
        # Telescópica: el piso es un fondo de 5,5 mm, siempre.
        if b["id_placa_piso"] not in [k for k, _ in de_55]:
            b["id_placa_piso"] = de_55[0][0] if de_55 else ""
    elif not b["id_placa_piso"] or b.get("_piso_de_guia", b["id_guia"] if b["id"] else None) != b["id_guia"]:
        # Lateral oculto: se propone la de la estructura al elegir la guía; si después se cambia, se respeta.
        b["id_placa_piso"] = b["id_placa"]
    b["_piso_de_guia"] = b["id_guia"]


def _habilitar(boton: ft.FilledButton, habilitado: bool) -> None:
    """Botón principal apagado mientras haya un error: no se sigue sin resolverlo."""
    boton.disabled = not habilitado
    boton.opacity = 1 if habilitado else 0.4


def _error_de_medidas(b: dict, al_avanzar: bool) -> str | None:
    """Medidas del paso 2. Mientras se escribe solo avisa lo mal escrito; al tocar
    «Siguiente», también lo que falta."""
    campos = [("ancho", "el ancho"), ("alto", "el alto"), ("profundidad", "la profundidad")]
    if b["armado"] != "Módulo":
        campos.append(("ancho_faja", "el ancho de las fajas"))
    for clave, nombre in campos:
        if not b[clave] and not al_avanzar:
            continue
        try:
            leer_numero(b[clave], nombre)
        except Exception as error:   # mensaje para el usuario (ErrorMateriales)
            return str(error)
    return None


def _error_del_paso(problema: str | None, paso: int) -> str | None:
    """Los errores de la guía y los cajones recién se muestran desde el paso Cajones."""
    if not problema or paso not in (2, 3, 4):
        return None
    if paso < 3 and ("guía" in problema or "Cajón" in problema or "cajón" in problema):
        return None
    return problema


# ---------- dibujo en vivo ----------
def _dibujo(app: Aplicacion, b: dict, d: Despiece | None) -> ft.Container:
    p = app.paleta
    ancho_max, alto_max = 380, 250
    try:
        A, H = float(leer_numero(b["ancho"], "a")), float(leer_numero(b["alto"], "h"))
    except Exception:
        A, H = 60.0, 75.0
    escala = min(ancho_max / A, alto_max / H)
    w, h = A * escala, H * escala
    x0, y0 = (ancho_max - w) / 2 + 20, 20
    figuras: list[ft.Control] = [ft.Container(left=x0, top=y0, width=w, height=h, bgcolor=p.superficie_alta,
                                              border=ft.Border.all(1.5, p.borde_fuerte))]
    if d is not None:
        sup, entre = _num(b["luz_superior"]), _num(b["luz_entre"])
        y = y0 + sup * escala
        izq, der = _num(b["luz_izquierda"]) * escala, _num(b["luz_derecha"]) * escala
        margen = 0.3 * escala
        for alto in d.altos_frentes_cajon:
            figuras.append(_frente(app, x0 + izq, y, w - izq - der, float(alto) * escala, cajon=True))
            y += (float(alto) + entre) * escala
        if d.alto_puertas is not None and b["puertas"]:
            n = b["puertas"]
            ancho_p = (w - izq - der - (n - 1) * margen) / n
            for i in range(n):
                figuras.append(_frente(app, x0 + izq + i * (ancho_p + margen), y, ancho_p,
                                       float(d.alto_puertas) * escala, cajon=False, lado=i % 2))
        if not d.altos_frentes_cajon and not b["puertas"] and b["armado"] == "Módulo":
            for i in range(1, b["estantes"] + 1):   # sin frentes: se ven los estantes
                figuras.append(ft.Container(left=x0 + 4, top=y0 + h * i / (b["estantes"] + 1), width=w - 8, height=3,
                                            bgcolor=p.borde_fuerte))
    figuras += [
        ft.Container(left=x0, top=y0 + h + 12, width=w, content=ft.Text(f"{b['ancho'] or '—'} cm", size=13,
                                                                          color=p.texto_secundario,
                                                                          text_align=ft.TextAlign.CENTER)),
        ft.Container(left=x0 + w + 8, top=y0 + h / 2 - 10, content=ft.Text(f"{b['alto'] or '—'} cm", size=13,
                                                                             color=p.texto_secundario)),
    ]
    etiquetas = [dict((a, e) for a, e, _ in ARMADOS)[b["armado"]],
                 f"{b['ancho'] or '?'} × {b['alto'] or '?'} × {b['profundidad'] or '?'}"]
    if b["fondo"]:
        etiquetas.append("con fondo")
    return componentes.tarjeta(ft.Column([
        ft.Stack(figuras, width=ancho_max + 80, height=alto_max + 50),
        ft.Row([componentes.etiqueta_estado(e, p.texto_secundario, p.superficie_alta) for e in etiquetas],
               spacing=8, wrap=True, alignment=ft.MainAxisAlignment.CENTER),
    ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER), p, padding=24)


def _num(texto: str) -> float:
    """Número escrito con coma o punto; 0 si está vacío o incompleto (solo para dibujar)."""
    try:
        return float(Decimal((texto or "0").replace(",", ".")))
    except Exception:
        return 0.0


def _frente(app: Aplicacion, x: float, y: float, w: float, h: float, cajon: bool, lado: int = 0) -> ft.Container:
    p = app.paleta
    tirador = ft.Container(width=min(40, w * 0.4) if cajon else 4, height=4 if cajon else min(36, h * 0.3),
                           bgcolor=p.texto_tenue, border_radius=2)
    return ft.Container(left=x, top=y, width=max(w, 1), height=max(h, 1), bgcolor=p.superficie,
                        border=ft.Border.all(1.5, p.acento), border_radius=2, content=tirador,
                        alignment=ft.Alignment.CENTER if cajon else (ft.Alignment.CENTER_RIGHT if lado == 0
                                                                     else ft.Alignment.CENTER_LEFT),
                        padding=ft.Padding.symmetric(horizontal=6))


# ---------- controles ----------
def _campo_num(p, etiqueta: str, b: dict, clave: str, signo: bool = False, al_escribir=None,
               **opciones) -> ft.TextField:
    """Campo de medida. al_escribir se llama con cada tecla: el error aparece en el
    momento, sin esperar a salir del campo."""
    campo = tema.campo(etiqueta, p, value=b[clave], input_filter=FILTRO_CON_SIGNO if signo else FILTRO_NUMERO,
                       suffix=ft.Text("cm", color=p.texto_tenue), **opciones)

    def al_cambiar(_):
        b[clave] = campo.value or ""
        if al_escribir:
            al_escribir()
    campo.on_change = al_cambiar
    return campo


def _contador(app: Aplicacion, b: dict, clave: str, etiqueta: str, al_cambiar=None, maximo: int = 12) -> ft.Column:
    p = app.paleta
    valor = ft.Text(str(b[clave]), size=24, font_family=SANS_SEMI, color=p.texto, width=60,
                    text_align=ft.TextAlign.CENTER)

    def cambiar(delta: int) -> None:
        b[clave] = max(0, min(maximo, b[clave] + delta))
        valor.value = str(b[clave])
        if al_cambiar:
            al_cambiar()
        else:
            app.page.update()

    boton = lambda texto, delta: ft.OutlinedButton(  # noqa: E731
        content=ft.Text(texto, size=22, color=p.texto), on_click=lambda _: cambiar(delta), width=56, height=52,
        style=ft.ButtonStyle(side=ft.BorderSide(1, p.borde_fuerte), shape=ft.RoundedRectangleBorder(radius=12)))
    return ft.Column([ft.Text(etiqueta, size=15, font_family=SANS_MEDIA, color=p.texto),
                      ft.Row([boton("−", -1), valor, boton("+", 1)], spacing=10)], spacing=8)


def _interruptor(app: Aplicacion, b: dict, clave: str, etiqueta: str, al_cambiar=None) -> ft.Switch:
    p = app.paleta
    s = ft.Switch(label=etiqueta, value=b[clave], active_color=p.acento,
                  label_text_style=ft.TextStyle(color=p.texto, size=15))

    def cambio(_):
        b[clave] = bool(s.value)
        if al_cambiar:
            al_cambiar()
    s.on_change = cambio
    return s


def _desplegable(app: Aplicacion, b: dict, clave: str, etiqueta: str, opciones: list[tuple[str, str]],
                 al_cambiar=None) -> ft.Dropdown:
    p = app.paleta
    valor = b[clave] if any(k == b[clave] for k, _ in opciones) else (opciones[0][0] if opciones else "")
    b[clave] = valor
    d = componentes.desplegable(etiqueta, opciones, valor, p)

    def cambio(_):
        b[clave] = d.value or ""
        if al_cambiar:
            al_cambiar()
    d.on_select = cambio
    return d


def _ayuda(p, texto: str) -> ft.Text:
    return ft.Text(texto, size=13, color=p.texto_tenue)


# ---------- pasos ----------
def _paso_tipo(app: Aplicacion, b: dict, refrescar) -> tuple[str, list[ft.Control]]:
    p = app.paleta

    def elegir(armado: str) -> None:
        b["armado"] = armado
        refrescar()

    tarjetas = []
    for clave, titulo, texto in ARMADOS:
        elegido = b["armado"] == clave
        tarjetas.append(ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.RADIO_BUTTON_CHECKED if elegido else ft.Icons.RADIO_BUTTON_UNCHECKED,
                                    color=p.acento_texto if elegido else p.texto_tenue),
                            ft.Column([ft.Text(titulo, size=16, font_family=SANS_SEMI, color=p.texto),
                                       ft.Text(texto, size=13, color=p.texto_tenue)], spacing=2, expand=True)],
                           spacing=12),
            border=ft.Border.all(2 if elegido else 1, p.acento if elegido else p.borde_fuerte), border_radius=12,
            bgcolor=p.superficie_alta if elegido else None, padding=ft.Padding.all(14), ink=True,
            on_click=lambda _, c=clave: elegir(c)))
    nombre = tema.campo("Nombre del módulo (opcional)", p, value=b["nombre"], max_length=100,
                        hint_text="por ejemplo: Bajo bacha, Cajonera 60")
    nombre.on_change = lambda _: b.__setitem__("nombre", nombre.value or "")
    controles: list[ft.Control] = [*tarjetas, nombre]
    if b["armado"] != "Módulo":
        faja = _campo_num(p, "Ancho de las fajas", b, "ancho_faja")
        chips = ft.Row([ft.OutlinedButton(content=ft.Text(f"{v} cm", color=p.texto),
                                          on_click=lambda _, v=v: (b.__setitem__("ancho_faja", v), refrescar()))
                        for v in ("10", "12")], spacing=8)
        controles += [faja, chips]
    return "¿Qué vas a armar?", controles


def _paso_medidas(app: Aplicacion, b: dict, refrescar, redibujar) -> tuple[str, list[ft.Control]]:
    p = app.paleta
    # El foco automático solo al entrar al paso: si no, al rearmar la pantalla volvería al ancho.
    campos = [_campo_num(p, "Ancho", b, "ancho", al_escribir=redibujar, autofocus=b.get("_primera_vez", False)),
              _campo_num(p, "Alto (sin zócalo)", b, "alto", al_escribir=redibujar),
              _campo_num(p, "Profundidad", b, "profundidad", al_escribir=redibujar,
                         helper="Total, con los frentes incluidos")]
    for c in campos:
        c.on_blur = lambda _: redibujar()
        c.on_submit = lambda _: redibujar()
    controles: list[ft.Control] = [*campos]
    if b["armado"] == "Módulo":
        controles += [
            _interruptor(app, b, "lleva_techo", "Lleva techo (sin techo = bajo mesada)", refrescar),
            _contador(app, b, "estantes", "Estantes", redibujar),
            *([_interruptor(app, b, "pinos", "Pinos de apoyo de mesada (2, adelante y atrás)", redibujar)]
              if not b["lleva_techo"] else []),
        ]
    controles.append(_interruptor(app, b, "fondo", "Lleva fondo (0,3 cm más chico que el módulo)", redibujar))
    return "¿Cuánto mide?", controles


def _paso_frentes(app: Aplicacion, b: dict, refrescar, redibujar) -> tuple[str, list[ft.Control]]:
    p = app.paleta
    estilos, _ = app.ejecutar(app.catalogo.estilos)
    opciones = [(str(e.id), e.nombre) for e in estilos or []] + [(PERSONALIZADO, "Luces personalizadas")]
    if not b["id_estilo"] and estilos:
        # Por defecto, el estilo con tirador que corresponde al tipo de armado.
        preferido = "Cajonera con tirador" if b["armado"] != "Módulo" else "Con tirador"
        _aplicar_estilo(b, next((e for e in estilos if e.nombre == preferido), estilos[0]))

    def al_elegir() -> None:
        estilo = next((e for e in estilos or [] if str(e.id) == b["id_estilo"]), None)
        if estilo:
            _aplicar_estilo(b, estilo)
        refrescar()

    estilo_elegido = next((e for e in estilos or [] if str(e.id) == b["id_estilo"]), None)
    luces = ft.Row([ft.Container(_campo_num(p, "Arriba", b, "luz_superior", signo=True, al_escribir=redibujar),
                                 expand=True),
                    ft.Container(_campo_num(p, "Abajo", b, "luz_inferior", signo=True, al_escribir=redibujar),
                                 expand=True),
                    ft.Container(_campo_num(p, "Entre frentes", b, "luz_entre", al_escribir=redibujar),
                                 expand=True)], spacing=10)
    for c in luces.controls:
        c.content.on_blur = lambda _: redibujar()
    costados = ft.Row([ft.Container(_campo_num(p, "Izquierda", b, "luz_izquierda", al_escribir=redibujar),
                                    expand=True),
                       ft.Container(_campo_num(p, "Derecha", b, "luz_derecha", al_escribir=redibujar),
                                    expand=True)], spacing=10)
    for c in costados.controls:
        c.content.on_blur = lambda _: redibujar()

    libre, unido = _luz_costado(app), _luz_junto(app)

    def junto(lado: str) -> None:
        clave = f"luz_{lado}"
        b[clave] = libre if b[clave] == unido else unido
        refrescar()

    def boton_junto(lado: str, texto: str) -> ft.OutlinedButton:
        activo = b[f"luz_{lado}"] == unido
        return ft.OutlinedButton(
            content=ft.Row([ft.Icon(ft.Icons.CHECK_BOX if activo else ft.Icons.CHECK_BOX_OUTLINE_BLANK, size=18,
                                    color=p.acento_texto if activo else p.texto_tenue),
                            ft.Text(texto, size=14, color=p.texto)], spacing=6, tight=True),
            on_click=lambda _: junto(lado),
            style=ft.ButtonStyle(side=ft.BorderSide(1, p.acento if activo else p.borde_fuerte),
                                 shape=ft.RoundedRectangleBorder(radius=10)))

    controles: list[ft.Control] = [
        _desplegable(app, b, "id_estilo", "Estilo de frente", opciones, al_elegir),
        *([_ayuda(p, estilo_elegido.descripcion)] if estilo_elegido and estilo_elegido.descripcion else []),
        tema.etiqueta_superior("Luces arriba, abajo y entre frentes", p), luces,
        _ayuda(p, "Negativa = el frente sobresale (ej.: alacena −1,3 abajo). 0 = a filo."),
        tema.etiqueta_superior("Luces a los costados", p), costados,
        ft.Row([boton_junto("izquierda", "Otro módulo a la izquierda"),
                boton_junto("derecha", "Otro módulo a la derecha")], spacing=8, wrap=True, run_spacing=8),
        _ayuda(p, f"Costado libre: {libre}. Junto a otro módulo: {unido} de cada lado, así entre los dos "
                  f"frentes queda {libre} y no el doble."),
    ]
    if b["armado"] == "Módulo":
        controles.append(_contador(app, b, "puertas", "Puertas", redibujar, maximo=8))
    return "¿Cómo son los frentes?", controles


def _aplicar_estilo(b: dict, estilo) -> None:
    b["id_estilo"] = str(estilo.id)
    b["luz_superior"], b["luz_inferior"] = _f(estilo.luz_superior), _f(estilo.luz_inferior)
    b["luz_entre"] = _f(estilo.luz_entre_frentes)


def _ir_a_guias(app: Aplicacion) -> None:
    materiales = app.recuerdos.setdefault("materiales", {"pestana": "guias", "texto": "", "bajas": False})
    materiales["pestana"] = "guias"
    app.ir_a("materiales")


def _paso_cajones(app: Aplicacion, b: dict, refrescar, redibujar) -> tuple[str, list[ft.Control]]:
    p = app.paleta
    guias, _ = app.ejecutar(app.catalogo.guias)
    opciones_guias = [(str(g.id), g.nombre) for g in guias or []]

    def al_cambiar_cantidad() -> None:
        b["altos_frente"] = (b["altos_frente"] + [""] * b["cajones"])[:b["cajones"]]
        refrescar()

    controles: list[ft.Control] = [_contador(app, b, "cajones", "Cantidad de cajones", al_cambiar_cantidad, maximo=8)]
    if not b["cajones"]:
        controles.append(_ayuda(p, "Si no lleva cajones, seguí al paso siguiente."))
        return "¿Lleva cajones?", controles
    if not opciones_guias:
        controles.append(tema.aviso("No hay guías cargadas: agregalas en Materiales › Guías.", p))
        return "¿Cuántos cajones lleva?", controles

    def al_elegir_guia() -> None:
        b["largo_guia"] = ""          # se propone el más largo que entra de la guía nueva
        _ajustar_guia(app, b, guias)
        refrescar()

    _ajustar_guia(app, b, guias)
    guia = next((g for g in guias if str(g.id) == b["id_guia"]), None)
    posibles = _largos_posibles(app, b)
    if guia is not None and not guia.largos:
        largo: ft.Control = ft.Column([
            tema.aviso(f"«{guia.nombre}» no tiene largos cargados. Cargalos en Materiales › Guías y volvé: "
                       "lo que cargaste del módulo queda guardado.", p),
            tema.boton_secundario("Ir a Materiales › Guías", p, lambda _: _ir_a_guias(app))], spacing=8)
    elif not posibles:
        cargados = ", ".join(_f(x) for x in sorted(guia.largos)) if guia else ""
        largo = tema.aviso(f"Ningún largo de «{guia.nombre if guia else 'la guía'}» entra en la caja de este "
                           f"módulo (largos cargados: {cargados}). Elegí otra guía o revisá la profundidad.", p)
    else:
        largo = _desplegable(app, b, "largo_guia", "Largo de la guía", [(_f(x), f"{_f(x)} cm") for x in posibles],
                             redibujar)
    caja = _campo_num(p, "Alto de la caja", b, "alto_caja", al_escribir=redibujar,
                      helper="Estimado; se puede corregir después")
    altos = []
    for i in range(b["cajones"]):
        campo = tema.campo(f"Cajón {i + 1}", p, value=b["altos_frente"][i], input_filter=FILTRO_NUMERO,
                           suffix=ft.Text("cm", color=p.texto_tenue),
                           hint_text="obligatorio" if b["puertas"] else "vacío = reparto")

        def al_escribir(_, i=i, c=campo):
            b["altos_frente"][i] = c.value or ""
            redibujar()
        campo.on_change = al_escribir
        altos.append(ft.Container(campo, col={"xs": 6, "md": 4}))
    telescopica = guia is not None and any(x.pieza == "Lateral de cajón" for x in guia.piezas)
    if telescopica:
        de_55 = opciones_placas(app, solo_espesor_mm=Decimal("5.5"))
        piso: ft.Control = (_desplegable(app, b, "id_placa_piso", "Piso del cajón (5,5 mm, como un fondo)", de_55,
                                         redibujar) if de_55 else
                            tema.aviso("Con guía telescópica el piso del cajón va en placa de 5,5 mm y no hay "
                                       "ninguna cargada. Cargala en Materiales › Placas.", p))
    else:
        piso = _desplegable(app, b, "id_placa_piso", "Placa del piso del cajón",
                            opciones_placas(app, (_id(b["id_placa_piso"]),)), redibujar)
    controles += [
        _desplegable(app, b, "id_guia", "Tipo de guía", opciones_guias, al_elegir_guia),
        ft.Row([ft.Container(largo, expand=True), ft.Container(caja, expand=True)], spacing=10,
               vertical_alignment=ft.CrossAxisAlignment.START),
        _ayuda(p, "Solo aparecen los largos cargados en Materiales › Guías que entran en la caja (la profundidad "
                  "menos el espesor de los frentes). Se propone el más largo."),
        tema.etiqueta_superior("Alto del frente de cada cajón", p),
        _ayuda(p, "Con puertas, cada cajón necesita su alto de frente: las puertas ocupan lo que queda."
               if b["puertas"] else "Dejalos vacíos para repartir el alto en partes iguales."),
        ft.ResponsiveRow(altos, spacing=10, run_spacing=10),
        piso,
    ]
    return "¿Cuántos cajones lleva?", controles


def _paso_materiales(app: Aplicacion, b: dict, refrescar, d: Despiece | None) -> tuple[str, list[ft.Control]]:
    p = app.paleta
    incluidas = tuple(_id(b[k]) for k in ("id_placa", "id_placa_frentes", "id_placa_cajones", "id_placa_fondo"))
    placas = opciones_placas(app, incluidas)
    misma = [("", "La misma que la estructura")] + placas
    controles: list[ft.Control] = [_desplegable(app, b, "id_placa", "Estructura", placas, refrescar)]
    if b["puertas"] or b["cajones"]:
        controles.append(_desplegable(app, b, "id_placa_frentes", "Frentes (puertas y frentes de cajón)", misma, refrescar))
    if b["cajones"]:
        controles.append(_desplegable(app, b, "id_placa_cajones", "Caja de los cajones", misma, refrescar))
    if b["fondo"]:
        controles.append(_desplegable(app, b, "id_placa_fondo", "Fondo", placas, refrescar))
    if b["pinos"] and b["armado"] == "Módulo" and not b["lleva_techo"]:
        listones, _ = app.ejecutar(app.materiales.listones)
        controles.append(_desplegable(app, b, "id_liston", "Pinos", [(str(x.id), x.nombre) for x in listones or []]))
    if b["puertas"] or b["cajones"]:
        colores, _ = app.ejecutar(app.catalogo.colores_laca)
        terminaciones, _ = app.ejecutar(app.catalogo.terminaciones)
        def al_elegir_laca() -> None:
            # La terminación que se ve en pantalla queda elegida de entrada (la primera).
            if b["id_color_laca"] and not b["id_terminacion"] and terminaciones:
                b["id_terminacion"] = str(terminaciones[0].id)
            refrescar()

        laca = _desplegable(app, b, "id_color_laca", "Laca de los frentes (opcional)",
                            [("", "Sin laquear")] + [(str(c.id), f"{c.marca} {c.descripcion}") for c in colores or []],
                            al_elegir_laca)
        controles.append(laca)
        if b["id_color_laca"]:
            controles += [_desplegable(app, b, "id_terminacion", "Terminación",
                                       [(str(t.id), t.nombre) for t in terminaciones or []]),
                          _ayuda(p, "Los frentes laqueados no llevan filo.")]
    # Sentido de la veta por tipo de pieza (RN-02.1).
    if d is not None:
        tipos = []
        for pieza in d.piezas:
            if pieza.medida_2 is not None and pieza.tipo not in tipos:
                tipos.append(pieza.tipo)
        chips = []
        for tipo in tipos:
            rotado = tipo in b["rotar"]
            chips.append(ft.Checkbox(label=tipo, value=rotado, active_color=p.acento, check_color=p.sobre_acento,
                                     label_style=ft.TextStyle(color=p.texto_secundario, size=14),
                                     on_change=lambda e, t=tipo: (b["rotar"].add(t) if e.control.value
                                                                  else b["rotar"].discard(t))))
        controles += [tema.etiqueta_superior("Rotar el sentido de la veta", p),
                      _ayuda(p, "Marcá los tipos de pieza que van con la veta al revés de lo habitual "
                                "(puertas y laterales: vertical; el resto: horizontal). En colores lisos no importa."),
                      ft.Row(chips, wrap=True, spacing=6, run_spacing=0)]
    return "¿De qué material?", controles


def _paso_revisar(app: Aplicacion, b: dict, d: Despiece | None, error: str | None,
                  refrescar) -> tuple[str, list[ft.Control]]:
    p = app.paleta
    if error or d is None:
        return "Revisá antes de guardar", [tema.aviso(error or "Faltan datos.", p)]
    veces = b.get("cantidad", 1)
    controles: list[ft.Control] = [
        ft.Container(ft.Column([
            _contador(app, b, "cantidad", "Cantidad de módulos iguales", refrescar, maximo=50),
            _ayuda(p, "Si hay varios módulos idénticos, cargás uno solo: las piezas se multiplican en el listado "
                      "y los filos se definen una vez para todos."),
        ], spacing=6), padding=ft.Padding.all(14), border_radius=12, bgcolor=p.superficie_alta),
    ]
    if b["cantidad"] < 1:
        b["cantidad"] = 1
    if b["puertas"] or b["cajones"]:
        controles.append(_ayuda(p, f"Luces: arriba {b['luz_superior'] or 0} · abajo {b['luz_inferior'] or 0} · "
                                   f"entre {b['luz_entre'] or 0} · izquierda {b['luz_izquierda'] or 0} · "
                                   f"derecha {b['luz_derecha'] or 0}. La caja va {_f(d.profundidad_caja)} cm "
                                   "de profundidad (sin los frentes)."))
    for titulo, materiales in GRUPOS:
        piezas = [x for x in d.piezas if x.material in materiales]
        if not piezas:
            continue
        controles.append(tema.etiqueta_superior(titulo, p))
        for x in piezas:
            donde = f" · cajón {x.cajon}" if x.cajon else ""
            medidas = (f"{_f(x.medida_1)} × {_f(x.medida_2)}" if x.medida_2 is not None else f"largo {_f(x.medida_1)}")
            vertical = (x.tipo in VETA_VERTICAL) != (x.tipo in b["rotar"])
            veta = "liso (se puede rotar)" if not x.con_veta else ("veta ↕ (en el alto)" if vertical
                                                                   else "veta ↔ (a lo largo)")
            cuantas = f"{x.tipo} × {x.cantidad}" + (f" → ×{x.cantidad * veces}" if veces > 1 else "")
            controles.append(ft.Row([
                ft.Text(f"{cuantas}{donde}", size=15, font_family=SANS_MEDIA, color=p.texto, expand=True),
                ft.Text(medidas, size=15, color=p.texto),
                ft.Text(veta if x.medida_2 is not None else "", size=12, color=p.texto_tenue, width=160,
                        text_align=ft.TextAlign.RIGHT),
            ], spacing=10))
    controles.append(_ayuda(p, "Medidas finales (con el filo incluido). Los filos se definen al guardar, en "
                               "«Piezas y filos»; ahí también se ve la medida de corte."))
    por_modulo = sum(x.cantidad for x in d.piezas)
    if veces > 1:
        return f"{por_modulo} piezas por módulo · {por_modulo * veces} en total", controles
    return f"{por_modulo} piezas", controles


# ---------- pantalla ----------
def construir(app: Aplicacion, id_mueble: int, id_modulo: int | None) -> ft.Control:
    p = app.paleta
    clave = f"modulo:{id_mueble}:{id_modulo}"
    b = app.recuerdos.get("modulo")
    if not b or b.get("_clave") != clave:
        if id_modulo is not None:
            modulo, error = app.ejecutar(lambda: next(m for m in app.muebles.modulos(id_mueble) if m.id == id_modulo))
            if error:
                return tema.aviso(error, p)
            b = _borrador_de(modulo)
        else:
            b = _borrador_nuevo(app, id_mueble)
        b["_clave"] = clave
        app.recuerdos["modulo"] = b
    if b["armado"] != "Módulo" and not b["cajones"]:   # una cajonera lleva al menos un cajón
        b["cajones"], b["altos_frente"] = 1, [""]
    mueble, _ = app.ejecutar(app.muebles.mueble, id_mueble)   # nombre y trabajo para la ruta
    id_trabajo = mueble.id_trabajo if mueble else None
    if not b["id_placa"]:
        return ft.Column([tema.aviso("Para cargar módulos, primero cargá las placas en Materiales.", p),
                          tema.boton_secundario("Ir a Materiales", p, lambda _: app.ir_a("materiales"))], spacing=16)

    def refrescar() -> None:
        app.ir_a("modulo", id_mueble=id_mueble, id_modulo=id_modulo)

    def ir_a_paso(paso: int) -> None:
        b["paso"] = paso
        refrescar()

    def salir(_=None) -> None:
        app.recuerdos.pop("modulo", None)
        if id_trabajo:
            app.ir_a("trabajo", id_trabajo=id_trabajo)

    d, error = _calcular(app, b) if b["paso"] >= 1 else (None, None)
    paso = b["paso"]
    # ¿Es la primera vez que se muestra este paso? (para el foco automático)
    b["_primera_vez"] = b.get("_paso_mostrado") != paso
    b["_paso_mostrado"] = paso
    contenedor_dibujo = ft.Container(content=_dibujo(app, b, d))

    def problema_del_paso(calculo_error: str | None, al_avanzar: bool) -> str | None:
        """El error que frena este paso: mientras haya uno, no se puede seguir."""
        if paso == 0:
            return _error_de_medidas({**b, "ancho": "1", "alto": "1", "profundidad": "1"}, al_avanzar) \
                if b["armado"] != "Módulo" else None
        if paso == 1:
            return _error_de_medidas(b, al_avanzar)
        if paso == len(PASOS) - 1:
            return calculo_error
        return _error_del_paso(calculo_error, paso)

    def mostrar_estado(problema: str | None) -> None:
        caja_error.content, caja_error.visible = (tema.aviso(problema, p) if problema else None), bool(problema)
        _habilitar(boton_avanzar, problema is None)

    def redibujar() -> None:
        """Con cada dato: actualiza el dibujo y el aviso de error en el momento, sin
        rearmar la pantalla (el cursor queda donde se está escribiendo)."""
        nuevo, problema = _calcular(app, b)
        contenedor_dibujo.content = _dibujo(app, b, nuevo)
        mostrar_estado(problema_del_paso(problema, al_avanzar=False))
        app.page.update()
    if paso == 0:
        titulo, controles = _paso_tipo(app, b, refrescar)
    elif paso == 1:
        titulo, controles = _paso_medidas(app, b, refrescar, redibujar)
    elif paso == 2:
        titulo, controles = _paso_frentes(app, b, refrescar, redibujar)
    elif paso == 3:
        titulo, controles = _paso_cajones(app, b, refrescar, redibujar)
    elif paso == 4:
        titulo, controles = _paso_materiales(app, b, refrescar, d)
    else:
        titulo, controles = _paso_revisar(app, b, d, error, refrescar)

    caja_error = ft.Container(visible=False)

    def siguiente(_=None) -> None:
        # No se sigue con un error: primero hay que resolverlo.
        _, problema = _calcular(app, b) if paso >= 2 else (None, None)
        problema = problema_del_paso(problema, al_avanzar=True)
        if problema:
            mostrar_estado(problema)
            app.page.update()
            return
        ir_a_paso(paso + 1)

    def guardar(_=None) -> None:
        resultado, problema = app.ejecutar(lambda: app.muebles.guardar_modulo(a_modulo(b)))
        if problema:
            caja_error.content, caja_error.visible = tema.aviso(problema, p), True
            app.page.update()
            return
        id_guardado, avisos = resultado
        app.recuerdos.pop("modulo", None)
        app.recuerdos.pop("piezas", None)
        if id_trabajo:   # directo a los filos de este módulo
            app.ir_a("piezas", id_trabajo=id_trabajo, id_modulo=id_guardado)
        componentes.aviso_flotante(app.page, "Módulo guardado. Ahora definí los filos de sus piezas.", p)
        if avisos:
            mostrar_avisos(app, avisos)

    # Barra de pasos: se puede volver a cualquiera ya visitado.
    barra = ft.Row([
        ft.Column([ft.Container(height=4, border_radius=4, bgcolor=p.acento if i <= paso else p.borde_fuerte),
                   ft.Text(("✓ " if i < paso else f"{i + 1} · ") + nombre, size=13,
                           font_family=SANS_SEMI if i == paso else tema.SANS,
                           color=p.acento_texto if i == paso else (p.texto_secundario if i < paso else p.texto_tenue))],
                  spacing=6, expand=True)
        if i >= paso else
        ft.Container(content=ft.Column([ft.Container(height=4, border_radius=4, bgcolor=p.acento),
                                        ft.Text("✓ " + nombre, size=13, color=p.texto_secundario)], spacing=6),
                     expand=True, on_click=lambda _, i=i: ir_a_paso(i), ink=True)
        for i, nombre in enumerate(PASOS)], spacing=8)

    botones = [tema.boton_secundario("Atrás", p, lambda _: ir_a_paso(paso - 1)) if paso
               else tema.boton_secundario("Volver al trabajo", p, salir)]
    if paso < len(PASOS) - 1:
        boton_avanzar = tema.boton_principal(f"Siguiente: {PASOS[paso + 1].lower()} →", p, siguiente, expand=True)
    else:
        texto = f"Guardar {b['cantidad']} módulos iguales" if b.get("cantidad", 1) > 1 else "Guardar módulo"
        boton_avanzar = tema.boton_principal(texto, p, guardar, expand=True)
    botones.append(boton_avanzar)
    # Los desplegables de este paso pueden haber completado su primera opción:
    # se recalcula para que el error y el botón reflejen lo que se ve en pantalla.
    if paso >= 2:
        d_actual, error = _calcular(app, b)
        d = d_actual if d_actual is not None else d
    problema_inicial = problema_del_paso(error, al_avanzar=False)
    caja_error.content = tema.aviso(problema_inicial, p) if problema_inicial and paso < len(PASOS) - 1 else None
    caja_error.visible = bool(problema_inicial) and paso < len(PASOS) - 1
    _habilitar(boton_avanzar, problema_inicial is None and (d is not None or paso < len(PASOS) - 1))

    panel = componentes.tarjeta(ft.Column([
        tema.etiqueta_superior(f"Paso {paso + 1} de {len(PASOS)}", p),
        tema.titulo(titulo, p, 34),
        caja_error,
        *controles,
        ft.Divider(color=p.borde, height=1),
        ft.Row(botones, spacing=12),
    ], spacing=16), p, padding=26, col={"xs": 12, "lg": 6})

    # Volver siempre a mano: al paso anterior o, desde el primero, al trabajo (sin guardar).
    volver = ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=p.texto, icon_size=26,
                           tooltip="Paso anterior" if paso else "Volver al trabajo sin guardar",
                           on_click=(lambda _: ir_a_paso(paso - 1)) if paso else salir)
    salir_sin_guardar = ft.TextButton(content=ft.Text("Volver al trabajo sin guardar", color=p.texto_secundario,
                                                      size=14), on_click=salir)
    return ft.Column([
        ft.Row([volver,
                ft.Column([ft.Text(mueble.nombre if mueble else "", size=13, color=p.texto_tenue),
                           tema.titulo("Editar módulo" if b["id"] else "Nuevo módulo", p, 36)], spacing=0, expand=True),
                salir_sin_guardar], spacing=8),
        barra,
        ft.ResponsiveRow([
            ft.Container(ft.Column([contenedor_dibujo,
                                    _ayuda(p, "El dibujo se actualiza con cada dato. El despiece completo se revisa en "
                                              "el último paso.")], spacing=10,
                                   horizontal_alignment=ft.CrossAxisAlignment.CENTER), col={"xs": 12, "lg": 6}),
            panel,
        ], spacing=24, run_spacing=24, vertical_alignment=ft.CrossAxisAlignment.START),
    ], spacing=18)
