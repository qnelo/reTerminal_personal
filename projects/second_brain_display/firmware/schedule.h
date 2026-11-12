// Horario del reTerminal. Sin dependencias de ESPHome para poder probarlo en el host (test_schedule.cpp).
// day_of_week como ESPHome: 1 = domingo, 2 = lunes ... 7 = sábado.
#pragma once
#include <cstdint>

inline constexpr int WORK_START_MIN = 8 * 60 + 45;  // 08:45
inline constexpr int WORK_END_MIN = 19 * 60;        // 19:00
// Fuera de horario, tiempo despierto tras el arranque, un botón o un refresco (OTA, navegar la galería).
inline constexpr uint32_t AWAKE_GRACE_MS = 3 * 60 * 1000;
// El timer del deep sleep usa el oscilador RC interno, que se desvía unos minutos por hora: se duerme
// por tramos y cada despertar resincroniza la hora por SNTP.
inline constexpr uint32_t SLEEP_CHUNK_MS = 4 * 60 * 60 * 1000;

inline bool is_workday(int day_of_week) { return day_of_week != 1 && day_of_week != 7; }

inline bool is_work_hours(int day_of_week, int hour, int minute) {
  int m = hour * 60 + minute;
  return is_workday(day_of_week) && m >= WORK_START_MIN && m < WORK_END_MIN;
}

// Milisegundos hasta las próximas 08:45 de un día hábil, entre 1 min y cap_ms.
inline uint32_t ms_until_workday(int day_of_week, int hour, int minute, int second, uint32_t cap_ms) {
  int now_min = hour * 60 + minute;
  int days = 0;
  while (!is_workday((day_of_week - 1 + days) % 7 + 1) || (days == 0 && now_min >= WORK_START_MIN))
    days++;
  int64_t ms = (days * 86400LL + (WORK_START_MIN - now_min) * 60LL - second) * 1000;
  if (ms > cap_ms)
    ms = cap_ms;
  if (ms < 60000)
    ms = 60000;
  return static_cast<uint32_t>(ms);
}
