"""Argentine administrative business-day calendar for 2026–2027.

Holidays include national dates plus the 2026 bridges cited in the demo:
23/3, 10/7, 7/12, and the moved dates 15/6 and 23/11.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

HOLIDAYS_2026: frozenset[date] = frozenset(
    {
        date(2026, 1, 1),  # Año Nuevo
        date(2026, 2, 16),  # Carnaval
        date(2026, 2, 17),  # Carnaval
        date(2026, 3, 23),  # puente
        date(2026, 3, 24),  # Día Nacional de la Memoria
        date(2026, 4, 2),  # Malvinas
        date(2026, 4, 3),  # Viernes Santo
        date(2026, 5, 1),  # Día del Trabajador
        date(2026, 5, 25),  # Revolución de Mayo
        date(2026, 6, 15),  # Güemes (trasladado)
        date(2026, 6, 20),  # Belgrano
        date(2026, 7, 9),  # Independencia
        date(2026, 7, 10),  # puente
        date(2026, 8, 17),  # San Martín
        date(2026, 10, 12),  # Diversidad Cultural
        date(2026, 11, 20),  # Soberanía Nacional
        date(2026, 11, 23),  # trasladado / puente
        date(2026, 12, 7),  # puente
        date(2026, 12, 8),  # Inmaculada Concepción
        date(2026, 12, 25),  # Navidad
    }
)

HOLIDAYS_2027: frozenset[date] = frozenset(
    {
        date(2027, 1, 1),
        date(2027, 2, 8),
        date(2027, 2, 9),
        date(2027, 3, 24),
        date(2027, 4, 2),
        date(2027, 3, 26),  # Viernes Santo 2027
        date(2027, 5, 1),
        date(2027, 5, 25),
        date(2027, 6, 17),
        date(2027, 6, 20),
        date(2027, 6, 21),
        date(2027, 7, 9),
        date(2027, 8, 16),
        date(2027, 10, 11),
        date(2027, 11, 20),
        date(2027, 12, 8),
        date(2027, 12, 25),
    }
)

HOLIDAYS = HOLIDAYS_2026 | HOLIDAYS_2027


def as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


def is_business_day(day: date | datetime | str) -> bool:
    d = as_date(day)
    return d.weekday() < 5 and d not in HOLIDAYS


def next_business_day(day: date | datetime | str) -> date:
    d = as_date(day)
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


def add_business_days(start: date | datetime | str, n: int) -> date:
    d = as_date(start)
    if n == 0:
        return next_business_day(d)
    step = 1 if n > 0 else -1
    remaining = abs(n)
    while remaining:
        d += timedelta(days=step)
        if is_business_day(d):
            remaining -= 1
    return d


def business_days_between(start: date | datetime | str, end: date | datetime | str) -> int:
    a, b = as_date(start), as_date(end)
    if b < a:
        return -business_days_between(b, a)
    n = 0
    d = a
    while d < b:
        d += timedelta(days=1)
        if is_business_day(d):
            n += 1
    return n


def iter_business_days(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        if is_business_day(d):
            yield d
        d += timedelta(days=1)
