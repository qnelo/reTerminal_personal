// Self-check del horario de deep sleep.
// Uso: g++ -std=c++17 projects/second_brain_display/firmware/test_schedule.cpp -o /tmp/test_schedule && /tmp/test_schedule
#include <cassert>
#include <cstdio>

#include "schedule.h"

int main() {
  const uint32_t H = 3600000, M = 60000, NO_CAP = UINT32_MAX;
  enum { DOM = 1, LUN, MAR, MIE, JUE, VIE, SAB };

  assert(!is_work_hours(LUN, 8, 44) && is_work_hours(LUN, 8, 45));
  assert(is_work_hours(VIE, 18, 59) && !is_work_hours(VIE, 19, 0));
  assert(!is_work_hours(SAB, 12, 0) && !is_work_hours(DOM, 12, 0));

  assert(ms_until_workday(MAR, 19, 0, 0, NO_CAP) == 13 * H + 45 * M);  // martes noche → miércoles
  assert(ms_until_workday(MIE, 2, 0, 0, NO_CAP) == 6 * H + 45 * M);    // madrugada → mismo día
  assert(ms_until_workday(VIE, 19, 0, 0, NO_CAP) == 61 * H + 45 * M);  // viernes → lunes
  assert(ms_until_workday(SAB, 10, 0, 0, NO_CAP) == 46 * H + 45 * M);
  assert(ms_until_workday(DOM, 23, 0, 0, NO_CAP) == 9 * H + 45 * M);
  assert(ms_until_workday(VIE, 19, 0, 0, SLEEP_CHUNK_MS) == 4 * H);    // tope por desvío del RTC
  assert(ms_until_workday(LUN, 8, 44, 30, NO_CAP) == M);               // mínimo 1 min

  puts("OK: horario");
}
