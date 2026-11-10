# Especificaciones de Hardware: Seeed Studio reTerminal E1002

El **reTerminal E1002** (SKU: `100017057`) es un terminal inteligente de visualización de información de ultra bajo consumo basado en el microcontrolador **Espressif ESP32-S3** y una pantalla de papel electrónico a todo color **E Ink® Spectra™ 6 de 7.3 pulgadas**.

---

## 1. Resumen de Características Principales

| Componente | Especificación |
| :--- | :--- |
| **SoC / MCU** | Espressif ESP32-S3 (Dual-Core Xtensa LX7 @ hasta 240 MHz) |
| **Memoria PSRAM** | 8 MB Octal PSRAM |
| **Memoria Flash** | 32 MB SPI Flash (Quad/Octal) |
| **Conectividad Inalámbrica** | Wi-Fi 4 (802.11 b/g/n, 2.4 GHz) + Bluetooth 5.0 (BLE) |
| **Pantalla** | E Ink® Spectra™ 6 (Full Color) |
| **Tamaño de Pantalla** | 7.3 pulgadas en diagonal |
| **Resolución** | 800 × 480 píxeles |
| **Colores Soportados** | 6 colores base (Negro, Blanco, Rojo, Amarillo, Azul, Verde) + algoritmos de difuminado (dithering) |
| **Tiempo de Refresco** | 15 a 20 segundos (refresco de pantalla completa; la tecnología Spectra 6 no admite refresco parcial rápido) |
| **Batería** | Batería recargable de polímero de litio de 2000 mAh (~3 meses de autonomía en modo bajo consumo con refrescos periódicos) |
| **Sensores Integrados** | Sensor Sensirion SHT40 de Temperatura y Humedad |
| **Reloj de Tiempo Real (RTC)** | NXP PCF8563 (con soporte para pila de botón CR1220 de respaldo) |
| **Almacenamiento Externo** | Ranura para tarjeta MicroSD (FAT32, hasta 32 GB) con detección por hardware y corte de alimentación |
| **Audio** | Zumbador piezoeléctrico activo/PWM + Micrófono PDM integrado |
| **Indicadores y Botones** | 3 botones de usuario en la parte superior, 1 LED de estado (verde), 1 LED de carga (rojo) |
| **Puerto USB y Programación** | Conector USB-C 5V / 1A con puente USB-a-UART CH340K y circuito auto-boot |
| **Puerto de Expansión** | Header de 8 pines (J2) con UART, I2C, ADC y GPIOs libres |
| **Chasis** | Caja metálica robusta con soporte vertical magnético/atornillable |
| **Dimensiones** | 176 mm × 120 mm × 53 mm (con base) / 17 mm de profundidad (sin base) |
| **Temperatura de Operación** | 0 °C a 40 °C |

---

## 2. Mapa Completo de Pines (GPIO Map - ESP32-S3)

Basado en el esquemático de hardware oficial (`202004321_reTerminal_E1002_V1_2_SCH_251120.pdf`):

| ESP32-S3 GPIO | Etiqueta Esquemático | Conectado a | Función / Descripción |
| :--- | :--- | :--- | :--- |
| **GPIO1** | `ESP_IO1/VBAT_ADC` | Divisor de tensión de batería | Entrada analógica ADC1_CH0 para medir voltaje de la batería |
| **GPIO2** | `ESP_IO2/ADC1_CH4` | Conector de expansión J2 (Pin 4) | GPIO libre / Entrada analógica ADC1_CH4 |
| **GPIO3** | `ESP_IO3/KEY0` | Botón verde superior (KEY0) | Botón de encendido / Refresco / Reset de red / Wakeup (Pull-up) |
| **GPIO4** | `ESP_IO4/KEY1` | Botón blanco derecho (visto de frente) | Navegación (Página siguiente) / Wakeup de Deep Sleep |
| **GPIO5** | `ESP_IO5/KEY2` | Botón blanco izquierdo (visto de frente) | Navegación (Página anterior) (Pull-up) |
| **GPIO6** | `ESP_IO6/LED` | LED verde de estado | Indicador de encendido y estado de firmware (Invertido/Active Low) |
| **GPIO7** | `ESP_IO7/SCK` | Bus SPI | Reloj SPI (`CLK`) compartido entre Pantalla ePaper y MicroSD |
| **GPIO8** | `ESP_IO8/MISO` | Bus SPI | Datos de entrada SPI (`MISO`) para tarjeta MicroSD |
| **GPIO9** | `ESP_IO9/MOSI` | Bus SPI | Datos de salida SPI (`MOSI`) para Pantalla ePaper y MicroSD |
| **GPIO10** | `ESP_IO10/SCREEN_CS#` | Pantalla ePaper | Chip Select de pantalla (Activo en BAJO) |
| **GPIO11** | `ESP_IO11/SCREEN_DC#` | Pantalla ePaper | Data / Command selector |
| **GPIO12** | `ESP_IO12/SCREEN_RST#`| Pantalla ePaper | Pin de Reset por hardware de pantalla (Activo en BAJO) |
| **GPIO13** | `ESP_IO13/SCREEN_BUSY#`| Pantalla ePaper | Pin Busy de pantalla (Indica que el display está actualizando) |
| **GPIO14** | `ESP_IO14/SD_CS` | Tarjeta MicroSD | Chip Select de la tarjeta MicroSD (Activo en BAJO) |
| **GPIO15** | `ESP_IO15/SD_DET` | Tarjeta MicroSD | Detección de inserción de tarjeta (Activo en BAJO, requiere Pull-up) |
| **GPIO16** | `ESP_IO16/SD_EN` | Conmutador de energía MicroSD | Activa la línea de alimentación de la tarjeta MicroSD |
| **GPIO17** | `ESP_IO17/TX1` | Conector de expansión J2 (Pin 5) | Transmisión UART1 (`TX1`) / GPIO libre |
| **GPIO18** | `ESP_IO18/RX1` | Conector de expansión J2 (Pin 6) | Recepción UART1 (`RX1`) / GPIO libre |
| **GPIO19** | `ESP_IO19/I2C0_SDA` | Bus I2C principal + J2 (Pin 8) | Línea de datos I2C para SHT40, PCF8563 y conector J2 |
| **GPIO20** | `ESP_IO20/I2C0_SCL` | Bus I2C principal + J2 (Pin 7) | Línea de reloj I2C para SHT40, PCF8563 y conector J2 |
| **GPIO21** | `ESP_IO21/VBAT_EN` | Mosfet divisor de batería | Activa el divisor resistivo para leer la batería sin consumo parásito |
| **GPIO38** | `ESP_IO38/PDM_EN` | Conmutador energía Micrófono | Enciende el carril de alimentación del micrófono PDM |
| **GPIO41** | `ESP_IO41/PDM_DATA` | Micrófono digital PDM | Línea de datos PDM (I2S Data In) |
| **GPIO42** | `ESP_IO42/PDM_CLK` | Micrófono digital PDM | Reloj PDM (I2S Clock Out) |
| **GPIO43** | `U0TXD` | Puente USB CH340K | UART0 TX (Consola serial / programación) |
| **GPIO44** | `U0RXD` | Puente USB CH340K | UART0 RX (Consola serial / programación) |
| **GPIO45** | `ESP_IO45/BUZZER_EN` | Zumbador piezoeléctrico | Control PWM de sonido (LEDC) |
| **GPIO46** | `ESP_IO46` | Conector de expansión J2 (Pin 3) | GPIO libre / Entrada analógica ADC |

---

## 3. Dispositivos en el Bus I2C (I2C0)

El bus I2C funciona en **GPIO19 (SDA)** y **GPIO20 (SCL)** con resistencias pull-up de 4.7 kΩ a 3.3V.

1. **Sensor Sensirion SHT40**:
   - Dirección I2C: `0x44`
   - Precisión: ±0.2 °C (Temperatura), ±1.8% RH (Humedad relativa).
   - Rango: -40 °C a +125 °C, 0% a 100% RH.
2. **Reloj de Tiempo Real (RTC) NXP PCF8563**:
   - Dirección I2C: `0x51`
   - Función: Mantiene la hora exacta incluso si el dispositivo se reinicia o está en modo Deep Sleep prolongado.
   - Batería de respaldo: Zócalo para pila de botón **CR1220** (es necesario colocar una pila CR1220 para que el reloj retenga la hora al desconectar la batería principal).

---

## 4. Circuito de Batería y Medición de Voltaje

Para maximizar la autonomía, el circuito divisor de tensión de la batería no está conectado de forma continua a tierra (lo que causaría una pérdida constante de energía). 

- **Activación previa**: Antes de leer el ADC en `GPIO1`, es obligatorio poner `GPIO21` (`VBAT_EN`) en nivel ALTO (`HIGH`).
- **Tiempo de estabilización**: Se recomienda esperar al menos 10 ms tras activar `GPIO21` antes de llamar a `analogRead(GPIO1)`.
- **Factor de división**: El circuito incorpora un divisor 1:2. Por tanto, el voltaje leído en el pin del ESP32 debe multiplicarse por `2.0`.
- **Curva de calibración recomendada (LiPo 3.7V / 4.2V max)**:
  - `4.15 V` $\rightarrow$ 100%
  - `3.96 V` $\rightarrow$ 90%
  - `3.91 V` $\rightarrow$ 80%
  - `3.85 V` $\rightarrow$ 70%
  - `3.80 V` $\rightarrow$ 60%
  - `3.75 V` $\rightarrow$ 50%
  - `3.68 V` $\rightarrow$ 40%
  - `3.58 V` $\rightarrow$ 30%
  - `3.49 V` $\rightarrow$ 20% (Aviso de batería baja)
  - `3.41 V` $\rightarrow$ 10%
  - `3.27 V` $\rightarrow$ 0% (Límite crítico de descarga)

---

## 5. Header de Expansión J2 (8 Pines)

El conector J2 está ubicado en el lateral/posterior y permite conectar periféricos externos (sensores Grove, módulos UART, relés, etc.):

```
      +---------------+
  1   |  HEADER_3V3   | -> Alimentación 3.3V de salida
  2   |  GND          | -> Tierra común
  3   |  ESP_IO46     | -> GPIO / ADC
  4   |  ESP_IO2      | -> GPIO / ADC1_CH4
  5   |  ESP_IO17     | -> UART1 TX
  6   |  ESP_IO18     | -> UART1 RX
  7   |  ESP_IO20     | -> I2C SCL
  8   |  ESP_IO19     | -> I2C SDA
      +---------------+
```

---

## 6. Cuidados Especiales de la Pantalla E Ink Spectra™ 6

Las pantallas ePaper a color **Spectra 6** ofrecen colores vivos superiores a los paneles e-ink tradicionales, pero tienen requerimientos físicos importantes:

1. **Evitar refrescos continuos de alta frecuencia**: El proceso de migración electroforética para 6 colores toma entre 15 y 20 segundos por ciclo. No refresques la pantalla en intervalos menores a 60 segundos (lo recomendado es cada 5 a 15 minutos en producción).
2. **Evitar imágenes estáticas congeladas por semanas**: Si el equipo no se va a usar, se recomienda limpiar la pantalla (color blanco uniforme).
3. **Función de borrado de fábrica**: Mantener presionado el botón verde durante 5 segundos con el firmware de fábrica limpia la pantalla por completo para evitar imágenes fantasma (*burn-in/residual shadow*).
4. **Carga y Alimentación**: Si el dispositivo no carga con cables USB-C tipo Power Delivery (PD) de gama alta (por ejemplo cargadores de MacBook), utiliza un cargador estándar USB-A a USB-C de 5V / 1A - 2A.
