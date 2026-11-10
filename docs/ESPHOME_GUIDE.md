# Guía de ESPHome para reTerminal E1002

El **reTerminal E1002** cuenta con soporte oficial en **ESPHome** (a partir de la versión 2025.11.1 o superior) gracias al controlador nativo `epaper_spi` con el modelo `Seeed-reTerminal-E1002`.

---

## 1. Requisitos de Versión de ESPHome

Asegúrate de tener instalada una versión reciente de ESPHome:
```bash
esphome version
# Debe ser 2025.11.1 o posterior
```

Si ejecutas Home Assistant OS o Supervised, instala el add-on oficial **ESPHome** desde la tienda de complementos de Home Assistant.

---

## 2. Configuración Base del Dispositivo

El bloque inicial de ESPHome para el microcontrolador ESP32-S3 con 8MB PSRAM y 32MB Flash:

```yaml
esphome:
  name: reterminal-e1002
  friendly_name: "reTerminal E1002"
  on_boot:
    priority: 600
    then:
      - output.turn_on: bsp_sd_enable       # Enciende carril MicroSD
      - output.turn_on: bsp_battery_enable  # Habilita lectura de batería
      - delay: 100ms
      - component.update: battery_voltage

esp32:
  board: esp32-s3-devkitc-1
  framework:
    type: arduino

# Activar logging serial por UART0 (CH340K)
logger:
  hardware_uart: UART0
  level: INFO

# Habilitar API de Home Assistant y actualizaciones OTA
api:
  encryption:
    key: !secret ha_api_key

ota:
  - platform: esphome
    password: !secret ota_password

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "reTerminal-E1002-Fallback"
    password: "SetupPassword123"

captive_portal:
```

---

## 3. Bus SPI y Configuración de Pantalla (E Ink Spectra™ 6)

El controlador `epaper_spi` configura internamente las conexiones al panel Spectra 6 de 7.3":

```yaml
spi:
  clk_pin: GPIO7
  mosi_pin: GPIO9

display:
  - platform: epaper_spi
    id: epaper_display
    model: Seeed-reTerminal-E1002
    update_interval: 300s # Refresco periódico cada 5 minutos (o 'never' para refresco manual por botón/evento)
    lambda: |-
      // Definición de la paleta de 6 colores Spectra 6
      const auto BLACK   = Color(0,   0,   0,   0);
      const auto WHITE   = Color(255, 255, 255, 0);
      const auto RED     = Color(255, 0,   0,   0);
      const auto GREEN   = Color(0,   255, 0,   0);
      const auto BLUE    = Color(0,   0,   255, 0);
      const auto YELLOW  = Color(255, 255, 0,   0);

      // Dibujar fondo blanco
      it.fill(WHITE);

      // Dibujar rectángulos y elementos de prueba
      it.filled_rectangle(20, 20, 760, 50, BLUE);
      it.printf(400, 32, id(font_title), WHITE, TextAlign::CENTER, "reTerminal E1002");
```

---

## 4. Sensores Integrados

### 4.1 Bus I2C
Tanto el sensor de temperatura y humedad SHT40 como el reloj PCF8563 comparten el bus I2C:

```yaml
i2c:
  sda: GPIO19
  scl: GPIO20
  scan: true
```

### 4.2 Sensor de Temperatura y Humedad SHT40
```yaml
sensor:
  - platform: sht4x
    temperature:
      name: "Temperatura Ambiente"
      id: room_temp
    humidity:
      name: "Humedad Ambiente"
      id: room_hum
```

### 4.3 Monitoreo de Batería con Calibración
El divisor resistivo requiere activar `GPIO21` para evitar drenaje continuo:

```yaml
output:
  - platform: gpio
    pin: GPIO21
    id: bsp_battery_enable

sensor:
  - platform: adc
    pin: GPIO1
    name: "Voltaje Batería"
    id: battery_voltage
    update_interval: 60s
    attenuation: 12db
    filters:
      - multiply: 2.0 # Factor divisor 1:2

  - platform: template
    name: "Nivel de Batería"
    id: battery_level
    unit_of_measurement: "%"
    device_class: battery
    state_class: measurement
    lambda: 'return id(battery_voltage).state;'
    update_interval: 60s
    filters:
      - calibrate_linear:
          - 4.15 -> 100.0
          - 3.96 -> 90.0
          - 3.91 -> 80.0
          - 3.85 -> 70.0
          - 3.80 -> 60.0
          - 3.75 -> 50.0
          - 3.68 -> 40.0
          - 3.58 -> 30.0
          - 3.49 -> 20.0
          - 3.41 -> 10.0
          - 3.27 -> 0.0
      - clamp:
          min_value: 0
          max_value: 100
```

---

## 5. Botones, LED, Zumbador y Ranura MicroSD

```yaml
output:
  # LED de estado verde
  - platform: gpio
    pin: GPIO6
    id: bsp_led
    inverted: true

  # Alimentación MicroSD
  - platform: gpio
    pin: GPIO16
    id: bsp_sd_enable

  # Zumbador PWM
  - platform: ledc
    pin: GPIO45
    id: buzzer_pwm

light:
  - platform: binary
    name: "LED de Estado"
    output: bsp_led
    id: status_led

  - platform: monochromatic
    name: "Zumbador"
    output: buzzer_pwm
    id: buzzer_tone

binary_sensor:
  # Botón verde (KEY0 / GPIO3): Refrescar pantalla
  - platform: gpio
    pin:
      number: GPIO3
      mode: INPUT_PULLUP
      inverted: true
    name: "Botón Verde"
    id: btn_green
    on_press:
      then:
        - component.update: epaper_display

  # Botón blanco izquierdo (KEY1 / GPIO4): Página anterior / Wakeup
  - platform: gpio
    pin:
      number: GPIO4
      mode: INPUT_PULLUP
      inverted: true
    name: "Botón Izquierdo"
    id: btn_left

  # Botón blanco derecho (KEY2 / GPIO5): Página siguiente
  - platform: gpio
    pin:
      number: GPIO5
      mode: INPUT_PULLUP
      inverted: true
    name: "Botón Derecho"
    id: btn_right

  # Detección de inserción de tarjeta MicroSD
  - platform: gpio
    pin:
      number: GPIO15
      mode: INPUT_PULLUP
      inverted: true
    name: "MicroSD Insertada"
    id: sd_detect
```

---

## 6. Integración de Datos con Home Assistant

Puedes consumir cualquier entidad de Home Assistant directamente en la pantalla del reTerminal:

```yaml
text_sensor:
  # Estado del tiempo meteorológico
  - platform: homeassistant
    entity_id: weather.home
    id: ha_weather_condition
    internal: true

sensor:
  # Temperatura exterior
  - platform: homeassistant
    entity_id: weather.home
    attribute: "temperature"
    id: ha_exterior_temp
    internal: true

  # Humedad exterior
  - platform: homeassistant
    entity_id: weather.home
    attribute: "humidity"
    id: ha_exterior_hum
    internal: true

time:
  - platform: homeassistant
    id: ha_time
```

---

## 7. Modo Deep Sleep (Para Autonomía de Meses)

Si usas el reTerminal alimentado exclusivamente por batería, configura Deep Sleep para que despierte periódicamente o al presionar un botón:

```yaml
deep_sleep:
  id: deep_sleep_control
  run_duration: 30s        # Tiempo activo para actualizar sensores y pantalla
  sleep_duration: 60min    # Duerme 1 hora
  wakeup_pin: GPIO4        # Despierta inmediatamente si se pulsa el botón blanco
  wakeup_pin_mode: INVERT_WAKEUP
```
