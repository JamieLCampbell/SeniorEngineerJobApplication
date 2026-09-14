# Cleaning the supplied orders

Use small parsing functions, a row/batch cleaner, and separate file handling. All code uses Python's standard library. Cloud upload will call these functions rather than embed another set of cleaning rules.

```powershell
python -m orders data/customer_orders.csv --output-dir outputs/cleaning-v1
python -m unittest discover -s tests -v
```

Choose a new output directory for each run. Existing directories are refused to preserve previous evidence. A failed write can leave a partial new directory; only a completed command with all outputs is a completed run. Outputs are ignored by Git.

## Rules and reasons

The table below describes the current implementation. We have now [assumed a unit-price meaning for OrderAmount](spending-metrics.md), subject to stakeholder confirmation in a real project. Requiring quantity for spending and deriving total order value are pending code changes.

| Field/problem | Action | Reason or limitation |
| --- | --- | --- |
| Missing OrderID, CustomerID, region, date, or amount | Reject with reasons | These are needed to identify and analyse an order without guessing |
| Missing ProductID or Quantity | Keep as null and warn | Product analysis is incomplete; these fields do not prevent preserving a supplied amount. Revisit if total value requires quantity |
| Invalid nonblank optional field | Reject | Do not silently erase a bad value by treating it as absent |
| Decimal-looking IDs or quantities, e.g. `1001.0` | Convert only if positive and integral | Rounding would change the identifier or count; enforce INT64 range |
| `One Hundred Pounds` / `Three` | Convert through explicit field-specific mappings | Narrow, auditable support for the supplied phrases; no general language inference or exchange-rate conversion |
| Amounts | Parse exact Decimal, require nonnegative BigQuery NUMERIC-compatible value | Do not round money or accept NaN/infinity. Refund semantics are outside this initial order policy |
| Dates | Accept valid `YYYY-MM-DD`, trim surrounding whitespace, preserve DATE grain | The source supplies dates, not clock times; do not invent a timezone or interpret ambiguous dates |
| Region | Trim/collapse whitespace; preserve case and wording | No CRM fallback or guessed region mapping |
| Same ID, same validated values | Keep one, log each removed repeat | Normalised `1`/`1.0` and `150`/`150.00` can be equivalent |
| Same ID with conflicts or an invalid version | Reject the whole ID group | There is no update timestamp with which to choose the correct version |
| Different IDs with matching other fields | Keep both | Equal purchases are not proof of duplicate records |

One OrderID is assumed to identify one record; if these were order lines, we would need a line-level key. Rejected repeated IDs are retained even when both versions are invalid. All input records appear exactly once among accepted, rejected, and duplicate outputs.

The initial accepted dataset requires valid dates and amounts for both planned analyses. This excludes some records that a different, narrowly defined report might still use; disclose coverage rather than call the result complete revenue. No quantity multiplication or derived total is implemented until OrderAmount's meaning is agreed. No zero/mean imputation is used for missing money.

## Outputs

- `cleaned_orders.csv`: the original seven column names, typed values represented as CSV, dates in ISO format, blanks for optional nulls.
- `rejected.jsonl`: original row, source record number, all detected reasons and warnings.
- `duplicates.jsonl`: removed valid repeats and the retained source record number.
- `report.json`: reconcilable counts and warnings on accepted records. The CLI prints this summary, not raw rejected payloads.

Source row numbers count CSV records with the header at 1, not physical lines in a multiline CSV. Keep rejected files restricted when working with real customer data.

## Sample result

Ten inputs produce six accepted orders (101, 104, 105, 106, 107, 109), four rejected (102, 103, 108, 110), and no removed duplicates. Orders 104 and 109 have missing-product warnings. Rejections preserve missing amounts, unusable dates, and the missing quantity warning on 103. A parsed `Three` on rejected order 108 does not make its unknown date valid.

Tests cover those independently enumerated outcomes, unchanged input, optional fields, both conflict orderings, semantic duplicates, ambiguous/invalid dates, exact numeric limits, malformed input, and file outputs. This is local cleaning evidence; BigQuery loading and the final SQL metrics remain pending.

## Reuse

```python
from orders import clean_orders
from orders.files import read_orders
from pathlib import Path

result = clean_orders(read_orders(Path("data/customer_orders.csv")))
accepted_values = [record.values for record in result.accepted]
```

`orders/parsing.py` owns conversions; `orders/cleaning.py` owns acceptance and deduplication; `orders/files.py` owns file formats; `python -m orders` is the thin CLI. The cleaner deliberately holds the small batch in memory to detect conflicting versions across the entire input. Larger sources would need a database/staged grouping approach, not a claim that this scales indefinitely.
