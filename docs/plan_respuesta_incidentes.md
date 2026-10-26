# Plan de respuesta a incidentes — Sistema de Gestión para Carpintería

**Versión:** 1.0 · **Responsable técnico:** Lautaro Zanino · **Basado en:** NIST SP 800-61 (preparación → detección y análisis → contención, erradicación y recuperación → lecciones aprendidas)

Este plan dice qué hacer cuando algo falla. Está pensado para que cualquiera de los dos usuarios pueda seguirlo, y para que las decisiones importantes no se tomen apurados.

---

## 1. Reglas generales
1. **Calma.** Casi todo se puede recuperar si no se actúa a las apuradas.
2. **Avisar primero al responsable técnico** (Lautaro) antes de intentar arreglar algo.
3. **No apagar, no borrar, no reinstalar** hasta que el responsable lo indique: se puede perder información o evidencia.
4. **Anotar** qué pasó, a qué hora y qué se hizo (en papel o en el celular, si la PC no es confiable).
5. Al terminar, completar la sección 10 (**lecciones aprendidas**).

## 2. Preparación (antes de que pase algo)
- [ ] Copia diaria automática, cifrada y fuera de la PC (RNF-08). Revisar en la auditoría que los eventos `BACKUP_OK` aparezcan todos los días.
- [ ] Prueba de restauración mensual (sección 9). Fecha de la última prueba: ____/____/______
- [ ] **Clave de cifrado de las copias** impresa y guardada en un sobre cerrado, fuera del taller (por ejemplo, en la casa). Sin ella las copias no sirven.
- [ ] Clave de recuperación de BitLocker / cifrado de dispositivo guardada fuera de la PC.
- [ ] Contraseña de administrador de Windows y de SQL Server conocida por el responsable técnico.
- [ ] Instaladores a mano: SQL Server Express, SSMS, ODBC Driver 18 y el sistema (repositorio de GitHub).

| Dato | Dónde está |
|------|-----------|
| Clave de cifrado de copias | Sobre cerrado en ____________ |
| Clave de recuperación del disco | ____________ |
| Carpeta de copias en la nube | ____________ |
| Cuenta de la nube (usuario) | ____________ |

---

## 3. Escenario: robo o pérdida de la PC
**Riesgo:** exposición de datos de clientes y pérdida del sistema.
1. Avisar al responsable técnico.
2. Desde otro equipo, **cambiar la contraseña de la cuenta de la nube** donde están las copias y cerrar las sesiones abiertas en otros dispositivos.
3. Si el disco estaba cifrado, los datos no son legibles sin la contraseña de Windows o la clave de recuperación. Si no lo estaba, considerar los datos de clientes expuestos (ver sección 8).
4. Hacer la denuncia policial (sirve también para el seguro).
5. **Recuperar:** en la PC nueva, aplicar la verificación de seguridad (requerimientos 6.1.4), instalar el sistema y **restaurar la última copia** (sección 9).
6. En el sistema restaurado, **blanquear las contraseñas** de ambos usuarios.

## 4. Escenario: ransomware (aparece un mensaje pidiendo un rescate o los archivos no abren)
1. **Desconectar la PC de la red** (cable y wifi). **No apagarla.**
2. Sacar una foto del mensaje con el celular y anotar la hora.
3. Avisar al responsable técnico. **No pagar** el rescate ni contactar a los atacantes.
4. **No conectar** discos externos ni pendrives con copias a esa PC.
5. Revisar desde otro equipo que las copias de la nube estén sanas: si la carpeta sincronizada también se cifró, usar el historial de versiones de la nube (OneDrive y Google Drive guardan versiones anteriores de los archivos).
6. **Erradicar:** formatear y reinstalar Windows desde cero. No alcanza con "limpiar" la PC.
7. **Recuperar:** instalar el sistema y restaurar la última copia **anterior** al ataque (sección 9), verificando su hash.
8. Cambiar todas las contraseñas (Windows, nube, sistema, SQL Server).

## 5. Escenario: falla del disco o la PC no arranca
1. No forzar reinicios repetidos.
2. Avisar al responsable técnico.
3. Si el disco se puede recuperar, copiar los datos y reemplazarlo. Si no, seguir el paso 5 del escenario 3 (PC nueva + restaurar).

## 6. Escenario: olvido de contraseñas
- **Un usuario se olvidó la suya:** el otro usuario le blanquea la contraseña desde el sistema (RF-03.4).
- **Los dos se olvidaron la suya:** el responsable técnico, con la cuenta de administrador de SQL Server, genera un hash bcrypt de una contraseña provisoria y lo carga en `hash_contrasena_usu` con `debe_cambiar_contrasena_usu = 1`. Queda registrado como intervención manual en la sección 10.
- **Usuario bloqueado por intentos fallidos:** esperar 15 minutos. Si se repite sin que nadie lo explique, tratarlo como el escenario 7.

## 7. Escenario: sospecha de acceso no autorizado
Señales: el aviso de último ingreso (RF-03.7) muestra un horario en que nadie usó el sistema, hay intentos fallidos que nadie hizo, bloqueos inesperados, o trabajos y montos cambiados sin explicación.
1. Abrir la **pantalla de auditoría** y filtrar los eventos críticos de los últimos días: ¿quién, cuándo, desde qué PC, qué cambió?
2. Cambiar la contraseña del usuario afectado y la de Windows.
3. Si hubo cambios en montos o trabajos, corregirlos usando el detalle de la auditoría (valor anterior → nuevo) o comparando con una copia anterior restaurada en una base de prueba.
4. Revisar quién tiene acceso físico a la PC y que el bloqueo de pantalla de Windows esté activo.

## 8. Escenario: exposición de datos de clientes
(Por ejemplo, la PC robada sin cifrar o una copia sin cifrar compartida por error.)
1. Determinar qué datos se expusieron y de cuántos clientes.
2. Corregir la causa (cifrar el disco, borrar el archivo compartido, cambiar contraseñas).
3. Evaluar avisar a los clientes afectados para que estén atentos a llamadas o mensajes sospechosos (estafas usando sus datos).

## 9. Procedimiento: restaurar una copia
Lo hace el responsable técnico con la cuenta de administrador.
1. Copiar el archivo de la copia (`.bak.enc`) y su archivo `.sha256` desde la nube.
2. **Verificar el hash:** calcular el SHA-256 del archivo y compararlo con el guardado. Si no coincide, la copia está dañada o fue alterada: usar la anterior.
3. Descifrar la copia con la clave de cifrado.
4. Restaurar en SSMS (*Restore Database*). Para la **prueba mensual**, restaurar con otro nombre (`Carpinteria_Prueba`), verificar que estén los últimos trabajos y borrar la base de prueba.
5. Si se restauró la base real, volver a ejecutar `05_seguridad.sql` si el login de la aplicación no funciona (puede pasar en una PC nueva) y verificar que el sistema ingrese.
6. Registrar la restauración en la sección 10.

### Escenario: pérdida de la clave de cifrado
Las copias existentes no se pueden descifrar. Mientras la base actual funcione:
1. Generar una clave nueva, guardarla en el Administrador de credenciales y **en papel, fuera del taller**.
2. Hacer una copia nueva de inmediato y comprobar que se restaura.
3. Las copias viejas quedan inservibles; se pueden borrar.

---

## 10. Registro de incidentes y lecciones aprendidas
| Fecha | Qué pasó | Qué se hizo | Qué cambiamos para que no se repita |
|-------|----------|-------------|-------------------------------------|
| | | | |
