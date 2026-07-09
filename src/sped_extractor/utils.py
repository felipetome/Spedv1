from __future__ import annotations

import datetime as _dt
import logging
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Iterable, Optional, Sequence

import math

from zoneinfo import ZoneInfo

from .config import defaults

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def configure_logging(log_file: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


def try_decode(raw: bytes, encodings: Sequence[str]) -> str:
    for enc in encodings:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", raw, 0, len(raw), "Unable to decode input with given encodings")


def parse_number(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    v = v.replace(",", ".")
    try:
        dec = Decimal(v)
    except (InvalidOperation, ValueError):
        return None
    return float(dec)


def round_decimal(value: Optional[float], digits: int = 2) -> float:
    if value is None:
        return 0.0
    dec = Decimal(value).quantize(Decimal(f"1.{'0'*digits}"), rounding=ROUND_HALF_UP)
    return float(dec)


def parse_sped_date(value: str, tz: str) -> Optional[str]:
    """
    SPED dates are usually in DDMMAAAA format. Some variations may include YYYYMMDD.
    """
    v = (value or "").strip()
    if not v:
        return None
    if ISO_DATE_RE.match(v):
        return v
    # Attempt DDMMAAAA
    if len(v) == 8:
        if v[:2].isdigit() and v[2:4].isdigit() and v[4:].isdigit():
            day, month, year = v[:2], v[2:4], v[4:]
            try:
                dt = _dt.datetime(int(year), int(month), int(day))
            except ValueError:
                return None
            return dt.date().isoformat()
        if v[:4].isdigit():
            # Possibly AAAAMMDD
            year, month, day = v[:4], v[4:6], v[6:]
            try:
                dt = _dt.datetime(int(year), int(month), int(day))
            except ValueError:
                return None
            return dt.date().isoformat()
    return None


def parse_iso_datetime(value: str, tz: str) -> Optional[str]:
    v = (value or "").strip()
    if not v:
        return None
    try:
        dt = _dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    target = ZoneInfo(tz)
    localized = dt.astimezone(target)
    return localized.date().isoformat()


def ensure_defaults(item: dict) -> dict:
    for field in defaults.numeric_zero_if_missing:
        value = item.get(field)
        if isinstance(value, float):
            if math.isnan(value):
                item[field] = 0.0
            continue
        if isinstance(value, int):
            continue
        if value is None:
            item[field] = 0.0
    for field in defaults.null_if_missing:
        if field not in item or item[field] in ("", "null"):
            item[field] = None
    # Boolean defaults
    item.setdefault("Pis_Mono", False)
    item.setdefault("Cofins_Mono", False)
    return item


def monofasico_flag(value: Optional[str], monofasico_codes: Iterable[str]) -> Optional[bool]:
    if value is None:
        return None
    return value.strip() in set(monofasico_codes)

