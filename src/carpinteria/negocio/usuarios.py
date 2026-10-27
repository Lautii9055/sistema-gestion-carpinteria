"""Gestión de usuarios (RF-02 y RF-03.4).

Reglas:
- Cualquier usuario puede dar de alta a otro, blanquear su contraseña, darlo de
  baja o reactivarlo (no hay roles: son dos personas de confianza).
- Nadie puede darse de baja ni blanquearse a sí mismo (para eso está "Mi
  contraseña"), y siempre tiene que quedar al menos un usuario activo: sino,
  nadie podría volver a entrar.
- Las contraseñas provisorias las genera el sistema al azar, se muestran una
  sola vez y obligan a cambiarlas en el primer ingreso.
- Los usuarios no se borran (la auditoría los necesita): se dan de baja.
- Cada acción queda en la auditoría con quién la hizo y sobre quién.
"""
import re
import secrets
import socket

from carpinteria.negocio.autenticacion import ErrorAutenticacion, generar_hash
from carpinteria.negocio.entidades import Sesion, Usuario
from carpinteria.negocio.puertos import RepositorioAuditoria, RepositorioUsuarios

# Sin caracteres que se confunden al leerlos (0/O, 1/l/I).
_ALFABETO_PROVISORIO = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
LARGO_PROVISORIA = 12
_PATRON_USUARIO = re.compile(r"[a-z0-9][a-z0-9._-]{2,29}")


class ErrorUsuarios(ErrorAutenticacion):
    """Error de una regla de gestión de usuarios; se muestra tal cual."""


def generar_contrasena_provisoria() -> str:
    """Contraseña aleatoria con un generador criptográfico (módulo secrets)."""
    while True:
        clave = "".join(secrets.choice(_ALFABETO_PROVISORIO) for _ in range(LARGO_PROVISORIA))
        # Se exige mayúscula, minúscula y número, para que sea fuerte y legible.
        if (any(c.isupper() for c in clave) and any(c.islower() for c in clave)
                and any(c.isdigit() for c in clave)):
            return clave


class ServicioUsuarios:
    def __init__(self, usuarios: RepositorioUsuarios, auditoria: RepositorioAuditoria,
                 equipo: str | None = None) -> None:
        self._usuarios = usuarios
        self._auditoria = auditoria
        self._equipo = equipo or socket.gethostname()

    def listar(self) -> list[Usuario]:
        return sorted(self._usuarios.listar(),
                      key=lambda u: (not u.es_activo, u.nombre_completo.casefold()))

    def crear(self, sesion: Sesion, nombre_usuario: str, nombre_completo: str) -> str:
        """Crea el usuario y devuelve su contraseña provisoria (se muestra una vez)."""
        nombre_usuario = nombre_usuario.strip().lower()
        nombre_completo = " ".join(nombre_completo.split())
        if not _PATRON_USUARIO.fullmatch(nombre_usuario):
            raise ErrorUsuarios(
                "El usuario tiene que tener entre 3 y 30 caracteres: letras sin tilde, "
                "números, punto, guion o guion bajo (por ejemplo, lautaro o r.zanino)."
            )
        if not nombre_completo or len(nombre_completo) > 100:
            raise ErrorUsuarios("Escribí el nombre y apellido (hasta 100 caracteres).")
        if self._usuarios.buscar_por_nombre(nombre_usuario) is not None:
            raise ErrorUsuarios(f"Ya existe un usuario llamado «{nombre_usuario}».")

        provisoria = generar_contrasena_provisoria()
        nuevo_id = self._usuarios.crear(nombre_usuario, nombre_completo, generar_hash(provisoria))
        self._auditar("ALTA_USUARIO", sesion, nuevo_id, f"usuario: {nombre_usuario}")
        return provisoria

    def blanquear_contrasena(self, sesion: Sesion, id_usuario: int) -> str:
        objetivo = self._obtener(id_usuario)
        if objetivo.id == sesion.usuario.id:
            raise ErrorUsuarios("Para cambiar tu propia contraseña usá «Mi contraseña».")
        provisoria = generar_contrasena_provisoria()
        self._usuarios.asignar_contrasena_provisoria(objetivo.id, generar_hash(provisoria))
        self._auditar("BLANQUEO_CONTRASENA", sesion, objetivo.id, f"usuario: {objetivo.nombre_usuario}")
        return provisoria

    def dar_de_baja(self, sesion: Sesion, id_usuario: int) -> None:
        objetivo = self._obtener(id_usuario)
        if objetivo.id == sesion.usuario.id:
            raise ErrorUsuarios("No podés darte de baja a vos mismo.")
        if not objetivo.es_activo:
            return
        activos = [u for u in self._usuarios.listar() if u.es_activo]
        if len(activos) <= 1:
            raise ErrorUsuarios("Tiene que quedar al menos un usuario activo.")
        self._usuarios.cambiar_estado(objetivo.id, False)
        self._auditar("BAJA_USUARIO", sesion, objetivo.id, f"usuario: {objetivo.nombre_usuario}")

    def reactivar(self, sesion: Sesion, id_usuario: int) -> None:
        objetivo = self._obtener(id_usuario)
        if objetivo.es_activo:
            return
        self._usuarios.cambiar_estado(objetivo.id, True)
        self._auditar("REACTIVACION_USUARIO", sesion, objetivo.id, f"usuario: {objetivo.nombre_usuario}")

    def _obtener(self, id_usuario: int) -> Usuario:
        usuario = self._usuarios.buscar_por_id(id_usuario)
        if usuario is None:
            raise ErrorUsuarios("El usuario ya no existe.")
        return usuario

    def _auditar(self, codigo: str, sesion: Sesion, id_objetivo: int, detalle: str) -> None:
        self._auditoria.registrar(codigo, id_usuario=sesion.usuario.id, entidad="Usuario",
                                  id_entidad=id_objetivo, detalle=detalle, equipo=self._equipo)
