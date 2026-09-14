"""Field conversions. Unsupported values raise ValueError; nothing is guessed."""

from datetime import date
from decimal import Decimal, InvalidOperation


def parse_decimal(value: str, aliases=None) -> Decimal:
    text = " ".join(value.split())
    if not text:
        raise ValueError("missing")
    text = (aliases or {}).get(text.casefold(), text)
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError("not_numeric") from error
    if not number.is_finite():
        raise ValueError("not_finite")
    return number


def parse_positive_integer(value: str, aliases=None) -> int:
    number = parse_decimal(value, aliases)
    if number <= 0 or number > 9223372036854775807:
        raise ValueError("outside_positive_int64")
    if number != number.to_integral_value():
        raise ValueError("not_integer")
    return int(number)


def parse_amount(value: str) -> Decimal:
    number = parse_decimal(value, {"one hundred pounds": "100"})
    if number < 0:
        raise ValueError("negative_amount")
    if number == 0:
        return Decimal(0)
    # Check BigQuery NUMERIC limits without rounding to Decimal's default precision.
    digits = list(number.as_tuple().digits)
    exponent = number.as_tuple().exponent
    while digits[-1] == 0:
        digits.pop()
        exponent += 1
    if exponent < -9 or len(digits) + exponent > 29:
        raise ValueError("outside_bigquery_numeric")
    return number


def parse_order_date(value: str) -> date:
    text = value.strip()
    if not text:
        raise ValueError("missing")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise ValueError("invalid_iso_date") from error
    if parsed.isoformat() != text:
        raise ValueError("invalid_iso_date")
    return parsed


def parse_region(value: str) -> str:
    text = " ".join(value.split())
    if not text:
        raise ValueError("missing")
    # Preserve the source region's meaning; there is no current-CRM fallback.
    return text
