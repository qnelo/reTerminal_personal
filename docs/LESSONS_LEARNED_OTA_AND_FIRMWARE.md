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

## 7. Scripts Reutilizables Desarrollados

| Script | Ubicación | Descripción |
| :--- | :--- | :--- |
| **`flash_ota.sh`** | [`scripts/flash_ota.sh`](../scripts/flash_ota.sh) | Detecta la IP del reTerminal automáticamente y lanza `esphome run` hacia el dispositivo. |
| **`generate_cien_anos_tree.py`** | [`backend/generate_cien_anos_tree.py`](../projects/second_brain_display/backend/generate_cien_anos_tree.py) | Póster del árbol Buendía sin spoilers, definido por datos (personas, uniones, hijos) y dibujado con las 6 tintas exactas. |
| **`adapt_gallery_image.py`** | [`backend/adapt_gallery_image.py`](../projects/second_brain_display/backend/adapt_gallery_image.py) | Encuadre 5:3, tono adaptativo y tramado a las 6 tintas puras (`--mode auto\|bn\|bayer\|acento\|color`, falla si pasa de 64 KB). |
| **`test_adapt_gallery_image.py`** | [`backend/test_adapt_gallery_image.py`](../projects/second_brain_display/backend/test_adapt_gallery_image.py) | Self-check: la salida no cambia al pasar por la réplica del umbral del driver. |
| **`start_service.sh`** | [`backend/start_service.sh`](../projects/second_brain_display/backend/start_service.sh) | Inicia el backend con `-u` (unbuffered logging) y gestión automática de PID. |
