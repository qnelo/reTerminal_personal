# CLAUDE.md: reTerminal E1002

Proyecto personal: firmware ESPHome para el reTerminal E1002 (ESP32-S3 + E Ink Spectra 6) y el backend que
le sirve las vistas del second brain (`projects/second_brain_display/`).

## Reglas del repo

- **Los aprendizajes van a `docs/LESSONS_LEARNED_OTA_AND_FIRMWARE.md`, no al second brain.** Esta regla le
  gana a la del CLAUDE.md global: en este repo no se usa el skill `ingerir-aprendizaje`. Al cerrar una tarea
  que deje una trampa, una causa raíz o un criterio, agrega o corrige una sección ahí.
- **Nunca escribas nombres de red Wi-Fi (SSID) ni contraseñas** en archivos versionados: lecciones, READMEs,
  comentarios ni `secrets.yaml.example`. Describe las redes de forma genérica ("la red principal", "el
  router secundario con NAT"). Los valores reales viven solo en `firmware/secrets.yaml`, que está en el
  `.gitignore`. Antes de commitear, busca los nombres de red con `git grep`.
- La documentación se escribe en español. Los commits van en inglés con Conventional Commits
  (`feat(firmware): ...`, `docs(lessons): ...`).

## Backend (`projects/second_brain_display/backend/`)

- Corre como servicio systemd **de usuario**: `second-brain-display.service`, en el puerto 8088.
  - Reiniciar: `systemctl --user restart second-brain-display.service`.
  - Logs: `journalctl _SYSTEMD_USER_UNIT=second-brain-display.service`. Cada pedido del reTerminal trae
    `vbat`, `temp` y `hum`, así que ese log sirve como historial de la batería.
- **No uses `start_service.sh` ni `stop_service.sh`.** Fallan con "Address already in use" porque el
  servicio ya tiene el puerto, y de paso sobrescriben `server.log` y `server.pid`, que están versionados.
- Solo el reTerminal manda `vbat`. Si pruebas con curl un pedido que incluya `vbat`, pasa también la IP y
  los valores reales, o pisarás la telemetría y la IP que usa el OTA.

## Firmware (`projects/second_brain_display/firmware/`)

- Compilar: `.venv/bin/esphome compile projects/second_brain_display/firmware/second_brain_display.yaml`.
- Flashear: `.venv/bin/esphome upload <yaml> --device <IP>`. `esphome run` y `scripts/flash_ota.sh` se
  quedan transmitiendo logs para siempre.
- La IP del equipo es la que reportó al backend: `curl -s localhost:8088/api/gallery`, campo
  `telemetria.client_ip`.
- **Fuera del horario laboral (lun–vie 08:45–19:00) el equipo está en deep sleep** y no responde. Para
  flashear de noche, presiona un botón: quedan 3 minutos despierto.
- El logger está en `INFO`, así que el volcado de configuración (`[C]`) no aparece en `esphome logs`.
- El horario vive en `schedule.h`. Si lo tocas, actualiza `test_schedule.cpp`.

## Tests

```sh
.venv/bin/python projects/second_brain_display/backend/test_server_if_changed.py
.venv/bin/python projects/second_brain_display/backend/test_adapt_gallery_image.py
g++ -std=c++17 projects/second_brain_display/firmware/test_schedule.cpp -o /tmp/test_schedule && /tmp/test_schedule
```
