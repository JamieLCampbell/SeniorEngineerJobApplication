# Source orders

`customer_orders.csv` transcribes the ten rows in the supplied assessment appendix photograph, `20260914_102210.jpg`.

Empty cells stay empty. Decimal-looking identifiers, `INVALID_DATE`, `Three`, and `One Hundred Pounds` are preserved. The visual line wrap in “One Hundred Pounds” is represented as a space. No records have been removed or corrected.

Run `python scripts/profile_orders.py` from the repository root to inspect the issues without changing the source. It uses only Python's standard library. Findings describe syntax and apparent similarities, not final cleaning decisions: different order IDs can represent legitimate repeat purchases.
