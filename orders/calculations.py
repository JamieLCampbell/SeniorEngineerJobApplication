"""Derived values based on explicitly documented business assumptions."""

from decimal import Decimal, localcontext

from .parsing import parse_amount


def total_order_value(unit_price: Decimal, quantity: int) -> Decimal:
    # Assessment assumption: OrderAmount is unit price. Confirm with the source
    # owner/stakeholder before real reporting; otherwise multiplication overstates sales.
    # A NUMERIC input has at most 38 significant digits and INT64 at most 19.
    with localcontext() as context:
        context.prec = 60
        total = unit_price * quantity
    # Reject a product that cannot fit the warehouse type; do not round or clamp it.
    return parse_amount(str(total))
