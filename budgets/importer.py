import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from dateutil import parser as date_parser

from .models import Category, CategoryRule, Transaction

# Accept a handful of common header spellings across bank exports.
DATE_FIELDS = {"date", "transaction date", "posted date"}
DESC_FIELDS = {"description", "memo", "details", "merchant"}
AMOUNT_FIELDS = {"amount", "debit", "transaction amount"}


@dataclass
class ImportResult:
    created: int = 0
    skipped_duplicate: int = 0
    skipped_invalid: int = 0
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def _normalize_headers(fieldnames):
    return {name.strip().lower(): name for name in fieldnames}


def _find_column(normalized, candidates):
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def _parse_amount(raw):
    cleaned = raw.strip().replace(",", "").replace("$", "").replace("R", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -value if negative else value


def _parse_date(raw):
    try:
        return date_parser.parse(raw.strip()).date()
    except (ValueError, OverflowError):
        return None


def categorize(description, rules):
    """First keyword rule whose keyword appears (case-insensitively) in the
    description wins. Rules are applied longest-keyword-first so a specific
    rule like "whole foods market" beats a generic one like "market"."""
    lowered = description.lower()
    for rule in sorted(rules, key=lambda r: -len(r.keyword)):
        if rule.keyword.lower() in lowered:
            return rule.category
    return None


def import_csv(user, file_obj):
    result = ImportResult()

    raw = file_obj.read()
    text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        result.errors.append("CSV has no header row.")
        return result

    normalized = _normalize_headers(reader.fieldnames)
    date_col = _find_column(normalized, DATE_FIELDS)
    desc_col = _find_column(normalized, DESC_FIELDS)
    amount_col = _find_column(normalized, AMOUNT_FIELDS)

    missing = [
        label
        for label, col in [("date", date_col), ("description", desc_col), ("amount", amount_col)]
        if col is None
    ]
    if missing:
        result.errors.append(
            f"Could not find required column(s): {', '.join(missing)}. "
            f"Found headers: {reader.fieldnames}"
        )
        return result

    rules = list(CategoryRule.objects.filter(user=user).select_related("category"))

    for row_num, row in enumerate(reader, start=2):  # header is row 1
        date_raw = (row.get(date_col) or "").strip()
        desc_raw = (row.get(desc_col) or "").strip()
        amount_raw = (row.get(amount_col) or "").strip()

        if not date_raw or not desc_raw or not amount_raw:
            result.skipped_invalid += 1
            result.errors.append(f"Row {row_num}: missing required field(s), skipped.")
            continue

        date_val = _parse_date(date_raw)
        amount_val = _parse_amount(amount_raw)

        if date_val is None or amount_val is None:
            result.skipped_invalid += 1
            result.errors.append(f"Row {row_num}: could not parse date/amount, skipped.")
            continue

        external_id = f"{date_val}|{desc_raw}|{amount_val}"

        if Transaction.objects.filter(user=user, external_id=external_id).exists():
            result.skipped_duplicate += 1
            continue

        category = categorize(desc_raw, rules)

        Transaction.objects.create(
            user=user,
            date=date_val,
            description=desc_raw,
            amount=amount_val,
            category=category,
            external_id=external_id,
        )
        result.created += 1

    return result