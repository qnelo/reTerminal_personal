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
    ip = params.get("ip", [client_ip])[0]   # la IP que reporta el reTerminal gana a la de origen
    if ip and "vbat" in params:             # solo el reTerminal manda vbat
        GLOBAL_TELEMETRY["client_ip"] = str(ipaddress.ip_address(ip))
```
- **Mecanismo de descubrimiento instantáneo**: Al presionar el botón verde (`KEY0`), el microcontrolador contacta al servidor y su IP queda registrada.
- **Script automatizado**: Se creó [`scripts/flash_ota.sh`](../scripts/flash_ota.sh), que consulta automáticamente `/api/gallery` para extraer la IP viva del dispositivo y lanzar el flasheo OTA sin intervención manual.

### Trampa: la IP de origen puede ser la de un router con NAT (2026-11-11)
El backend registraba una IP de la LAN principal como si fuera la del reTerminal, y el OTA respondía `Connection refused`.
No era el reTerminal. Estaba conectado a la Wi-Fi de un router secundario (Xiaomi), que entrega otra subred y sale a la
LAN principal con NAT. La IP registrada era la WAN de ese router: rechaza (RST) el puerto 3232 y no reenvía nada hacia adentro.
- **Cómo se detectó**: `ip neigh` mostró una MAC Xiaomi (no Espressif) para esa IP. Además, `tailscale status` mostró
  que otro equipo conectado a ese router salía por la misma IP.
- **Arreglo**: el firmware agrega `&ip=` con su propia IP en cada petición (`get_ip_addresses()[0]`), y el backend la prefiere
  sobre la de origen. Además, un curl local sin `vbat` ya no pisa la IP guardada (antes el OTA terminó apuntando a `127.0.0.1`).
- **Si el reTerminal queda detrás de un NAT**: el OTA solo llega desde un equipo de esa misma red. Si no, se flashea por USB.
  El reTerminal usa un CH340 (`/dev/ttyUSB0`). Se copian los 4 binarios de `build/flasher_args.json` y se flashea así:
  `uvx --from esptool esptool.py write_flash 0x0 bootloader.bin 0x8000 partition-table.bin 0x9000 ota_data_initial.bin 0x10000 reterminal-second-brain.bin`.
- **Wi-Fi con respaldo**: `wifi.networks` con `priority` (1 para la principal, 0 para la de respaldo). Si la clave de la principal
  está mal, el equipo no queda en modo AP: cae a la de respaldo. En el log serie, `reason='4-Way Handshake Timeout'` en WPA2
  significa contraseña incorrecta.
- Los nombres de red y las claves viven solo en `secrets.yaml`, que no se versiona. Ni el ejemplo ni la documentación los llevan.

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

> ⚠️ **Corrección (2026-11-10):** cuantizar a N colores *arbitrarios* sirve para bajar el peso, pero no para fotos: el panel vuelve a mapear esos colores sin tramar y la foto se colapsa. Ver la [sección 6](#6-el-driver-de-la-pantalla-no-tramea-fotos-que-se-ven-como-manchas).

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

## 4. Transición Automática Noche/Fin de Semana y Supresión de Refrescos en Modos Estáticos

### Problema
El reTerminal tiene un reloj SNTP que refresca la pantalla cada 15 minutos en horario laboral (09:00 a 18:45). Se requerían dos comportamientos clave:
1. Al terminar la jornada laboral (19:00) y durante todo el fin de semana, el dispositivo debe pasar automáticamente a **Modo Galería** (cuadro digital de arte/fotografía) y suspender los refrescos periódicos laborales.
2. Al iniciar la jornada laboral (08:45 Lun-Vie), debe volver automáticamente a **Modo Pendientes** para mostrar las tareas del día.
3. Si el usuario conmuta manualmente a Galería durante la jornada laboral para leer o apreciar una lámina, los refrescos periódicos cada 15 minutos no deben sobreescribir la pantalla.

### Solución: Disparadores Horarios de Modo y Filtro en Refrescos Periódicos
Se implementaron reglas horarias con conmutación de modo y comprobación al sincronizar la hora:
```yaml
time:
  - platform: sntp
    on_time_sync:
      then:
        # Al arrancar, si la hora actual es noche o fin de semana, asegura Modo Galería
    on_time:
      # 08:45 Lun-Vie: activa Modo Pendientes
      - minutes: 45
        hours: 8
        days_of_week: MON-FRI
        then:
          - lambda: 'id(display_mode) = 0;'
          - script.execute: fetch_view
      # 09:00-18:45 Lun-Vie: refresco cada 15 min solo si está en Pendientes
      - minutes: /15
        hours: 9-18
        days_of_week: MON-FRI
        then:
          - if:
              condition:
                lambda: 'return id(display_mode) == 0;'
              then:
                - script.execute: fetch_view
      # 19:00 diario: activa Modo Galería para noche y fin de semana
      - minutes: 0
        hours: 19
        then:
          - if:
              condition:
                lambda: 'return id(display_mode) == 0;'
              then:
                - lambda: 'id(display_mode) = 1;'
                - script.execute: fetch_view
```
En el *Modo Galería*, el dispositivo queda en consumo cero y mantiene la imagen estática sin interrupciones hasta que el usuario decida volver a Pendientes o inicie la jornada laboral.

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
   ```
   > **Corrección (2026-11-12):** en esta solución también se había puesto `power_save_mode: NONE`. No hacía falta, porque el reinicio lo causaba `api.reboot_timeout`, y mantenía la radio Wi-Fi siempre encendida: la batería duraba ~19 h. Ver la sección 8.
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

## 6. El Driver de la Pantalla No Tramea: Fotos que se Ven como Manchas

### Problema
La foto del gato negro (Lámina 2) se veía en la vista previa como una foto en 11 tonos, pero en el panel era una silueta negra con dos ojos. La vista previa engañaba: no mostraba lo que hace el driver.

El driver `epaper_spi` de ESPHome (modelo `Seeed-reTerminal-E1002` → `epaper_spi_spectra_e6.cpp` → `colorconv.h::color_to_bwyrgb`) **no tramea**. Fuerza cada píxel RGB565 a una de las 6 tintas con un umbral duro:
- Si `max(r,g,b) − min(r,g,b) < 50`, el píxel es "gris": luma Rec.601 ≥ 128 → blanco; si no, negro.
- Si no es gris, se mira qué canales pasan de 128 y se elige la esquina del cubo RGB (amarillo, rojo, verde o azul).

Los 11 grises del PNG cuantizado con median-cut terminaban en **73 % negro sólido y 27 % blanco**, sin trama: el pelaje desaparecía. El propio `colorconv.h` lo advierte: *"For optimum output quality on RGB inputs consider offline color keying/dithering"*.

### Solución: Tramar en el Backend contra las 6 Tintas Exactas
[`adapt_gallery_image.py`](../projects/second_brain_display/backend/adapt_gallery_image.py) entrega un PNG en modo paleta cuyos colores son **exactamente** `#000 #FFF #FF0 #F00 #0F0 #00F`. Así el umbral del driver queda como identidad y la trama llega intacta al panel.
1. **Tono antes de tramar** (clave en sujetos oscuros: el 68 % de la foto del gato tenía luma < 80):
   - `autocontrast(cutoff=1, preserve_tone=True)`.
   - Curva gamma calculada desde la mediana de la foto: `γ = clamp(log 0.45 / log(mediana/255), 0.4, 1.0)`. Para el gato da 0.48.
   - Contraste local con `UnsharpMask(radius=40, percent=50)` y detalle fino con `UnsharpMask(radius=1.5, percent=120)`.
2. **Modos de trama** (`--mode`):
   - `bn`: Floyd-Steinberg a negro y blanco.
   - `bayer`: trama ordenada 8×8.
   - `acento`: `bn` más color solo en zonas saturadas.
   - `color`: Floyd-Steinberg a las 6 tintas.
   - `auto`: con saturación HSV media < 40 usa `bn`; si no, `color`.
3. **Tramar contra las tintas reales y emitir los códigos puros**: el modo `color` cuantiza contra los colores reales (apagados) del panel, aproximados, y después cambia la paleta por los códigos puros. La vista previa del dashboard usa las tintas reales, así se parece a lo que se ve.
4. **Paleta compacta en el PNG**: solo se escriben las tintas usadas. Con 2 tintas el PNG es de 1 bit por píxel y con hasta 4, de 2 bits. Con la paleta de 6 completa, el modo `acento` pesaba 67.5 KB; compactada, 48.4 KB.

Resultado para el gato (modo `bn`): **39.7 KB**, con pelaje, bigotes y volumen legibles. B/N con trama ordenada pesaba 21.8 KB. Las 6 tintas sobre esta foto pesaban 81–96 KB y además metían ruido azul y rojo en un gato gris.

### Trampas Encontradas
- **La saturación HSV en sombras es ruido**: `(20,15,10)` da S≈128. Una máscara "zonas saturadas" sin exigir brillo (`V > 80`) llenaba el pelaje negro de puntos azules y rojos.
- **El realce crea halos de color en los bordes**: la máscara de saturación se calcula sobre la foto *sin* realzar.
- **No asumir el color "a ojo"**: el iris del gato, que parecía verde-dorado, tiene S≈47/255. Casi gris: no hay color que acentuar.
- **Lo mismo vale para los gráficos dibujados.** El árbol Buendía original usaba colores «casi» de panel por generación, más `quantize(colors=16)`. En el panel, el verde oscuro y el pizarra salían negros, y el ámbar y el carmesí salían rojos: el código de colores no existía en pantalla. El rediseño dibuja con las 6 tintas exactas y `draw.fontmode = "1"` (texto sin antialias), y bajó de 17 KB a 7 KB.
- **Los 64 KB no son límite para un PNG.** `buffer_size` no se puede subir (el schema de ESPHome lo limita a 65536), pero tampoco hace falta:
  - `online_image` descarga por trozos y `PngDecoder::decode` llama a `pngle_feed`, que consume cada trozo apenas llega.
  - El buffer es solo la ventana de descarga. Solo el JPEG redimensiona el buffer al tamaño total (`online_image.cpp:136`).
  - Verificado en el panel con un PNG de 124 KB.
  - El script ahora pone un tope de cordura de 256 KB.
  - La sección 2 partía de la creencia contraria.
- **En color, menos realce.** El contraste local y la nitidez fuerte que salvan al gato negro, sumados a +20 % de saturación, convertían un gatito atigrado en ruido amarillo y rojo (y 120 KB). El modo `color` usa solo autocontraste, gamma y nitidez leve.
- **La trama ordenada en color no sirve:** con 6 tintas posteriza (el pelaje café quedó como manchas amarillas) y aun así pesaba 69 KB.

### Verificado en el Dispositivo (2026-11-11)
- Un PNG en paleta de **1 bit** (`01_gatito.png`, 40 KB) se decodifica y se pinta bien. Los anteriores eran de 4 bits.
- Un PNG a color de **124 KB** (`02_gatitos_durmiendo.png`), casi el doble del `buffer_size`, se descarga y se pinta bien. Esto confirma la lectura del código: para PNG, los 64 KB no son límite.

Probado con [`test_adapt_gallery_image.py`](../projects/second_brain_display/backend/test_adapt_gallery_image.py): replica `color_to_bwyrgb` y comprueba que ningún píxel de la salida cambia al pasar por el driver.

---

## 7. Refresco Condicional: No Redibujar si las Pendientes No Cambiaron

### Problema
El refresco de cada 15 minutos redibujaba el panel Spectra 6 (unos 20 s de consumo alto) aunque las pendientes fueran las mismas.

### Trampa: el ETag nativo de `online_image` no sirve con URL dinámica
`online_image` ya maneja peticiones condicionales: guarda `ETag` y `Last-Modified`, y los reenvía como `If-None-Match` y `If-Modified-Since`. Pero `set_url()` los borra (`online_image.h:58`, ESPHome 2026.10.2). `fetch_view` llama a `set_url` en cada pedido porque la URL lleva vbat, temp e hum, así que el dispositivo nunca manda el ETag.

### Solución: el estado lo guarda el servidor y el flag es un 304
- **Backend** ([`server.py`](../projects/second_brain_display/backend/server.py)):
  - Guarda el hash de la última vista de pendientes enviada al reTerminal: solo los pedidos con `vbat`, para que la vista previa del navegador no pise el estado.
  - Con `if_changed=1` y el mismo hash, responde `304` sin cuerpo.
  - En el hash entra solo el contenido de la vista: la hora y la telemetría no cuentan como cambio, pero `vence_str` sí (el paso de "Mañana" a "Hoy").
- **Firmware**:
  - Ante un 304, `online_image` no descarga y dispara `on_download_finished` con `cached = true`, que la automatización puede leer (`image.py:100`).
  - Con `cached`, no se llama a `component.update: epaper_display`.
  - Solo el tick de 15 min manda `if_changed=1`. Los botones, el arranque, las 08:45 y las 19:00 siempre dibujan.
- **Que nunca quede atascado en 304**: el servidor anota el estado al *enviar* el 200, pero la descarga puede fallar en el dispositivo. El global `screen_synced` (sin `restore_value`) se pone en `true` solo al dibujar y en `false` en `on_error` y al arrancar. El tick manda `if_changed` solo si es `true`.

Probado con [`test_server_if_changed.py`](../projects/second_brain_display/backend/test_server_if_changed.py).

---

## 8. La Batería Duraba 19 Horas: el ESP32 Nunca Dormía

### Problema
Con carga casi completa (4,11 V a las 10:30), el reTerminal estaba muerto antes de las 05:57 del día siguiente. La telemetría que manda en cada pedido (`vbat` en el log del backend) muestra la curva:
- 3,70 V a las 19:00, al pasar a la galería.
- Reinicios por batería agotada a las 05:57, 07:04 y 10:00, con 2,79–2,85 V.

Eso es un consumo estimado de ~90–100 mA promedio sobre 2000 mAh. No es una falla, es la configuración:
- `wifi: power_save_mode: NONE`: la radio no duerme entre los avisos periódicos del router.
- La CPU a 240 MHz (el máximo, que es el default) y ningún `deep_sleep`.

Toda la noche se gastaba en mostrar una lámina fija, que la tinta conserva sin energía.

Lo que **no** era la causa:
- **La pantalla:** el driver la manda a deep sleep después de cada refresco (`epaper_spi.cpp:244`). Unos 40 refrescos de ~20 s al día son menos del 1 %.
- **El refresco condicional de la sección 7:** cuida el panel más que la batería.

### Solución
1. **De día:** `power_save_mode: LIGHT` (el default de ESPHome en ESP32) y `cpu_frequency: 80MHZ`.
2. **Fuera de horario, `deep_sleep`:** una regla cada 30 s duerme el equipo si se cumplen tres condiciones:
   - Está fuera de horario laboral.
   - Pasaron 3 min desde el último arranque, botón o refresco (ventana para OTA y para navegar la galería).
   - La hora vino de SNTP, o pasaron 2 min sin lograrlo.
3. **Despertar programado:** a las 08:45 del próximo día hábil (`schedule.h`, probado con `test_schedule.cpp`).
4. **Despertar con botón:** `esp32_ext1_wakeup` con `ANY_LOW` sobre GPIO3/4/5. El `on_wake` de cada pin replica su acción: avanzar o retroceder la lámina.

### Trampas
- **El timer del deep sleep se desvía:** usa el oscilador RC interno, con unos minutos de error por hora. De viernes a lunes son ~62 h. Por eso se duerme por tramos de 4 h, y cada despertar resincroniza por SNTP. La hora del sistema sí sobrevive al deep sleep, porque la lleva el RTC: un despertar programado tiene hora válida de inmediato, aunque algo desviada.
- **Un despertar programado de noche no debe redibujar:** el arranque normal llama a `fetch_view`, y eso eran 20 s de panel cada 4 h. Al arrancar se distingue la causa con `esp_sleep_get_wakeup_cause()`:
  - **Timer:** solo dibuja si ya es horario laboral.
  - **Botón:** respeta el modo que eligió el usuario.
  - **Arranque en frío:** manda el horario, como antes.
- **ext1 no activa pull-ups en deep sleep:** ESPHome solo los configura para `wakeup_pin` (ext0). Funciona porque los tres botones tienen pull-up externo de 10 kΩ a `SYS_3V3` (R30/R34/R36 en el esquemático) y un condensador de 100 nF.
- **El mismo GPIO en el botón y en el wakeup:** hay que poner `allow_other_uses: true` en los dos lugares.
- **Los `globals` con `restore_value` sobreviven al deep sleep:** `deep_sleep.enter` corre los `on_shutdown`, que guardan los globals y sincronizan las preferencias en NVS.

---

## 9. Scripts Reutilizables Desarrollados

| Script | Ubicación | Descripción |
| :--- | :--- | :--- |
| **`flash_ota.sh`** | [`scripts/flash_ota.sh`](../scripts/flash_ota.sh) | Detecta la IP del reTerminal automáticamente y lanza `esphome run` hacia el dispositivo. |
| **`generate_cien_anos_tree.py`** | [`backend/generate_cien_anos_tree.py`](../projects/second_brain_display/backend/generate_cien_anos_tree.py) | Póster del árbol Buendía sin spoilers, definido por datos (personas, uniones, hijos) y dibujado con las 6 tintas exactas. |
| **`adapt_gallery_image.py`** | [`backend/adapt_gallery_image.py`](../projects/second_brain_display/backend/adapt_gallery_image.py) | Encuadre 5:3, tono adaptativo y tramado a las 6 tintas puras (`--mode auto\|bn\|bayer\|acento\|color`, falla si pasa de 64 KB). |
| **`test_adapt_gallery_image.py`** | [`backend/test_adapt_gallery_image.py`](../projects/second_brain_display/backend/test_adapt_gallery_image.py) | Self-check: la salida no cambia al pasar por la réplica del umbral del driver. |
| **`test_schedule.cpp`** | [`firmware/test_schedule.cpp`](../projects/second_brain_display/firmware/test_schedule.cpp) | Self-check del horario de deep sleep (`schedule.h`): horario laboral y tiempo hasta las próximas 08:45 hábiles. |
| **`test_server_if_changed.py`** | [`backend/test_server_if_changed.py`](../projects/second_brain_display/backend/test_server_if_changed.py) | Self-check del refresco condicional: cuándo `/render?if_changed=1` responde 304 y cuándo 200. |
| **`start_service.sh`** | [`backend/start_service.sh`](../projects/second_brain_display/backend/start_service.sh) | Inicia el backend con `-u` (unbuffered logging) y gestión automática de PID. |
