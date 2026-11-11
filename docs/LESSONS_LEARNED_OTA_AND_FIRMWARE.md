# 📚 Lecciones Aprendidas: Firmware, Pantalla E-Ink Spectra 6 y Flasheo OTA

Este documento recopila los hallazgos técnicos, limitaciones de hardware/software y soluciones arquitectónicas implementadas durante el desarrollo de la galería de imágenes, el árbol genealógico y el sistema de actualización OTA en el **Seeed Studio reTerminal E1002**.

---

## 1. Detección Automática de IP sin mDNS ni IP Fija

### Problema
En entornos Linux sin `avahi-daemon` o en redes Wi-Fi con aislamiento de clientes (AP Isolation) donde el multicast mDNS (`.local`) es bloqueado, ejecutar `esphome run firmware.yaml --device reterminal.local` falla por timeout de resolución de nombres. Asignar IPs estáticas en routers de oficina o portátiles suele ser engorroso o imposible.

### Solución: Telemetría Pasiva Bidireccional
Como el dispositivo reTerminal E1002 ya realizaba llamadas HTTP al backend (`/render?view=...`), agregamos en `server.py` el registro de la dirección IP del cliente:
```python
def update_telemetry(params: dict, client_ip: str | None = None):
    if client_ip:
        GLOBAL_TELEMETRY["client_ip"] = client_ip
```
- **Mecanismo de descubrimiento instantáneo**: Al presionar el botón verde (`KEY0`), el microcontrolador contacta al servidor, registrando de inmediato su IP exacta (`192.168.4.60`).
- **Script automatizado**: Se creó [`scripts/flash_ota.sh`](../scripts/flash_ota.sh), que consulta automáticamente `/api/gallery` para extraer la IP viva del dispositivo y lanzar el flasheo OTA sin intervención manual.

---

## 2. Límite Crítico de Buffer en ESPHome `online_image`

### Problema
Al compilar ESPHome con una imagen de 800×480 px, el validador arrojó el siguiente error:
```text
image.online_image: value must be at most 65536.
buffer_size: 196608
```
ESPHome impone un límite de esquema estricto de **65.536 bytes (64 KB)** para el buffer de descarga en memoria RAM de `online_image`. Las imágenes PNG RGB de 800×480 px generadas por Pillow rondaban los **110 KB**, desbordando el buffer de descarga.

### Solución: Cuantización y Tramado a Paleta Spectra 6
La pantalla de papel electrónico **Spectra 6** solo reproduce físicamente 6 colores primarios (Negro, Blanco, Rojo, Amarillo, Azul, Verde). Por ende, una imagen a 24 bits RGB desperdicia ancho de banda y memoria.

Implementamos cuantización a 16 colores con tramado Floyd-Steinberg en Python (Pillow):
```python
im_opt = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
im_opt.save(dest_path, format="PNG", optimize=True)
```
- **Resultado en Lámina 1 (Árbol Genealógico)**: Reducción de 110 KB a **14.6 KB**.
- **Resultado en Lámina 2 (Gatito fotorrealista)**: Reducción de 66 KB a **56.1 KB**.
- Ambas láminas quedan con holgura por debajo de los 65.536 bytes y se descargan en menos de 200 ms por Wi-Fi.

---

## 3. Detección de Doble Botón Simultáneo (Chording) en ESP32-S3

### Problema
El usuario quería presionar los dos botones blancos superiores (Izquierdo `GPIO5` y Derecho `GPIO4`) al mismo tiempo para alternar entre el *Modo Pendientes* y el *Modo Galería*.
Físicamente, ningún ser humano puede pulsar dos botones independientes con precisión de microsegundos: siempre hay una dispersión de **20 a 60 milisegundos** entre un dedo y el otro. Si el microcontrolador reacciona inmediatamente en `on_press`, el primer botón siempre dispararía su acción individual (cambiar de página) antes de que el segundo sea detectado.

### Solución: Ventana de Coincidencia Antirrebote (60 ms)
Se configuró una ventana de gracia temporal y una bandera de exclusión mutua en ESPHome:
```yaml
# Botón Izquierdo (GPIO5)
on_press:
  then:
    - delay: 60ms # Ventana de tiempo para detectar pulsación conjunta
    - lambda: |-
        if (id(combo_active)) return;
        if (id(btn_next).state) {
          id(toggle_display_mode).execute(); // ¡Ambos apretados!
          return;
        }
        // Navegación individual si el otro no está presionado...
    - if:
        condition:
          lambda: 'return !id(combo_active);'
        then:
          - script.execute: fetch_view
on_release:
  then:
    - lambda: |-
        if (!id(btn_prev).state && !id(btn_next).state) {
          id(combo_active) = false;
        }
```
1. Al pulsar el primer botón, el firmware espera 60 ms.
2. Si dentro de esa ventana el segundo botón baja su pin a LOW, se activa `combo_active = true` y se invierte el modo con un doble pitido en el buzzer.
3. El segundo botón, al despertar de sus 60 ms, comprueba que `combo_active` ya es verdadero y no ejecuta su acción individual.
4. Cuando ambos dedos se levantan, se restablece `combo_active = false`.

---

## 4. Supresión de Refrescos Automáticos en Modos Estáticos

### Problema
El reTerminal tiene un reloj SNTP que refresca la pantalla cada 15 minutos en horario laboral (09:00 a 18:45). Si el usuario cambió a la galería para consultar el árbol genealógico mientras lee una novela, un refresco periódico del horario laboral sobreescribiría la pantalla con tareas de trabajo automáticamente.

### Solución: Filtro de Modo en los Disparadores Horarios
Se condicionaron todos los eventos `on_time` al modo activo:
```yaml
time:
  - platform: sntp
    on_time:
      - minutes: /15
        hours: 9-18
        days_of_week: MON-FRI
        then:
          - if:
              condition:
                lambda: 'return id(display_mode) == 0;' # Solo en Modo Pendientes
              then:
                - script.execute: fetch_view
```
En el *Modo Galería*, el dispositivo queda en consumo cero y mantiene la imagen estática sin interrupciones hasta que el usuario decida volver a Pendientes.

---

## 5. El Watchdog Oculto de 15 Minutos de ESPHome (`api: reboot_timeout`)

### Problema
En implementaciones standalone donde el ESP32 no está conectado a una instancia de Home Assistant, el componente `api:` de ESPHome incluye por defecto:
```yaml
api:
  reboot_timeout: 15min # Valor por defecto en ESPHome
```
Si ningún cliente API se autentica en el puerto 6053 durante 15 minutos (900 segundos), ESPHome asume que el sistema perdió control o la red falló catastróficamente y dispara un **reinicio forzado por software** (`esp_restart()`).
Como consecuencia:
- Exactamente cada 15 minutos en punto (confirmado en logs a los 14m 52s, 15m 02s, etc.), la pantalla ePaper realizaba un ciclo de refresco completo de 20 segundos.
- Si `display_mode` tenía `restore_value: false`, el reinicio restauraba el valor `0` ("Pendientes Simpli"), expulsando al usuario de la foto de la galería sin haber tocado ningún botón.

### Solución Arquitectónica
1. **Deshabilitar el temporizador watchdog de la API y de Wi-Fi**:
   ```yaml
   api:
     reboot_timeout: 0s # Desactiva el reinicio por watchdog de Home Assistant
   wifi:
     reboot_timeout: 0s # Evita reinicios ante micro-cortes transitorios de Wi-Fi
     power_save_mode: NONE # Desactiva sleep del módem para mantener puertos y latencia constante
   ```
2. **Persistencia de Estado en Memoria No Volátil (NVS)**:
   Se cambiaron los estados de modo y lámina a persistentes:
   ```yaml
   globals:
     - id: display_mode
       type: int
       restore_value: true # Guarda en NVS el modo (0: Pendientes, 1: Galería)
       initial_value: '0'

     - id: gallery_index
       type: int
       restore_value: true # Guarda en NVS la lámina exacta seleccionada
       initial_value: '0'
   ```
3. **Bandera de Arranque Único (`boot_synced`)**:
   Se evitó que `wifi.on_connect` ejecute `fetch_view` en reconexiones transparentes posteriores a la inicial, reservando la consulta inicial exclusivamente para el primer encendido en frío.

---

## 6. Scripts Reutilizables Desarrollados

| Script | Ubicación | Descripción |
| :--- | :--- | :--- |
| **`flash_ota.sh`** | [`scripts/flash_ota.sh`](../scripts/flash_ota.sh) | Detecta la IP del reTerminal automáticamente y lanza `esphome run` hacia el dispositivo. |
| **`generate_cien_anos_tree.py`** | [`backend/generate_cien_anos_tree.py`](../projects/second_brain_display/backend/generate_cien_anos_tree.py) | Generador paramétrico de diagramas genealógicos optimizados para E-Ink Spectra 6. |
| **`adapt_gallery_image.py`** | [`backend/adapt_gallery_image.py`](../projects/second_brain_display/backend/adapt_gallery_image.py) | Pipeline de encuadre 5:3, realce y tramado de fotos reales para Spectra 6 (<64 KB). |
| **`start_service.sh`** | [`backend/start_service.sh`](../projects/second_brain_display/backend/start_service.sh) | Inicia el backend con `-u` (unbuffered logging) y gestión automática de PID. |
