import json
import re
import zipfile
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.utils import OperationalError

from books.models import Book, Category, Language


NS_MAIN = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_REL = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
SKIP = object()


def _letters_to_index(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha()).upper()
    result = 0
    for ch in letters:
        result = (result * 26) + (ord(ch) - ord("A") + 1)
    return result


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []

    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for si in root.findall("a:si", NS_MAIN):
        parts = [t.text or "" for t in si.findall(".//a:t", NS_MAIN)]
        values.append("".join(parts))
    return values


def _sheet_path(zf: zipfile.ZipFile, sheet_name: str | None, sheet_index: int) -> str:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        node.attrib["Id"]: node.attrib["Target"]
        for node in rels.findall("r:Relationship", NS_REL)
    }

    sheets = workbook.findall("a:sheets/a:sheet", NS_MAIN)
    if not sheets:
        raise CommandError("No sheets found in workbook.")

    target_sheet = None
    if sheet_name:
        for sheet in sheets:
            if (sheet.attrib.get("name") or "").strip() == sheet_name:
                target_sheet = sheet
                break
        if not target_sheet:
            raise CommandError(f'Sheet "{sheet_name}" not found.')
    else:
        if sheet_index < 1 or sheet_index > len(sheets):
            raise CommandError(
                f"sheet-index must be between 1 and {len(sheets)} (received {sheet_index})."
            )
        target_sheet = sheets[sheet_index - 1]

    rel_id = target_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    if not rel_id:
        raise CommandError("Could not resolve sheet relationship id.")

    target = rel_map.get(rel_id)
    if not target:
        raise CommandError("Could not resolve sheet XML target.")

    target = target.lstrip("/")
    if not target.startswith("xl/"):
        target = f"xl/{target}"
    return target


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str | None:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        parts = [t.text or "" for t in cell.findall(".//a:t", NS_MAIN)]
        return "".join(parts)

    value_node = cell.find("a:v", NS_MAIN)
    if value_node is None or value_node.text is None:
        return None

    raw = value_node.text
    if cell_type == "s":
        idx = int(raw)
        return shared_strings[idx] if idx < len(shared_strings) else None
    if cell_type == "b":
        return "1" if raw == "1" else "0"
    return raw


def read_xlsx_rows(path: Path, sheet_name: str | None, sheet_index: int) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as zf:
        shared_strings = _load_shared_strings(zf)
        sheet_xml_path = _sheet_path(zf, sheet_name=sheet_name, sheet_index=sheet_index)
        root = ET.fromstring(zf.read(sheet_xml_path))

    rows = root.findall(".//a:sheetData/a:row", NS_MAIN)
    if not rows:
        return []

    headers_by_col: dict[int, str] = {}
    records: list[dict[str, Any]] = []

    for row_idx, row in enumerate(rows):
        cols: dict[int, Any] = {}
        for cell in row.findall("a:c", NS_MAIN):
            ref = cell.attrib.get("r", "")
            col_idx = _letters_to_index(ref) if ref else 0
            cols[col_idx] = _cell_value(cell, shared_strings)

        if row_idx == 0:
            for col_idx, value in cols.items():
                name = (value or "").strip()
                if name:
                    headers_by_col[col_idx] = name
            continue

        item: dict[str, Any] = {}
        is_blank = True
        for col_idx, header in headers_by_col.items():
            value = cols.get(col_idx)
            item[header] = value
            if value not in (None, ""):
                is_blank = False
        if not is_blank:
            records.append(item)

    return records


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if value.lower() in {"null", "none", "nan"}:
            return None
        return value
    return str(value).strip()


def _trim_to_max(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    if len(value) <= max_length:
        return value
    return value[:max_length]


def _to_int(value: Any) -> int | None:
    text = _clean_text(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return None


def _to_bool(value: Any) -> bool | None:
    text = _clean_text(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    return None


def _to_json_list(value: Any) -> list[Any]:
    text = _clean_text(value)
    if text is None:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    return [part.strip() for part in re.split(r"[,\n]+", text) if part.strip()]


class Command(BaseCommand):
    help = "Update books table from an XLSX file (match by id then seo_slug)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="books.xlsx",
            help="Path to .xlsx file (default: books.xlsx).",
        )
        parser.add_argument(
            "--sheet-name",
            default=None,
            help="Sheet name to read (optional).",
        )
        parser.add_argument(
            "--sheet-index",
            type=int,
            default=1,
            help="1-based sheet index when --sheet-name is not provided (default: 1).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and simulate updates without writing to DB.",
        )
        parser.add_argument(
            "--create-missing",
            action="store_true",
            help="Create rows that do not match existing records.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"]).resolve()
        sheet_name = options["sheet_name"]
        sheet_index = options["sheet_index"]
        dry_run = options["dry_run"]
        create_missing = options["create_missing"]

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        rows = read_xlsx_rows(file_path, sheet_name=sheet_name, sheet_index=sheet_index)
        if not rows:
            self.stdout.write(self.style.WARNING("No data rows found in Excel sheet."))
            return

        try:
            categories = Category.objects.in_bulk()
            language_codes = set(Language.objects.values_list("code", flat=True))
            Book.objects.only("id").first()
        except OperationalError as exc:
            raise CommandError(
                "Database tables are missing. Run migrations first: "
                "`python manage.py migrate`."
            ) from exc
        valid_status = {choice for choice, _ in Book.STATUS_CHOICES}

        counters = {
            "updated": 0,
            "created": 0,
            "skipped_missing": 0,
            "skipped_invalid": 0,
            "errors": 0,
        }

        def run_sync(*, use_row_transactions: bool):
            for row_no, row in enumerate(rows, start=2):
                try:
                    if use_row_transactions:
                        with transaction.atomic():
                            result = self._sync_one_row(
                                row=row,
                                row_no=row_no,
                                categories=categories,
                                language_codes=language_codes,
                                valid_status=valid_status,
                                create_missing=create_missing,
                                dry_run=dry_run,
                            )
                    else:
                        result = self._sync_one_row(
                            row=row,
                            row_no=row_no,
                            categories=categories,
                            language_codes=language_codes,
                            valid_status=valid_status,
                            create_missing=create_missing,
                            dry_run=dry_run,
                        )
                    counters[result] += 1
                except Exception as exc:
                    counters["errors"] += 1
                    self.stdout.write(
                        self.style.ERROR(f"Row {row_no}: error -> {exc}")
                    )

        if dry_run:
            run_sync(use_row_transactions=False)
        else:
            run_sync(use_row_transactions=True)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Done: "
                f"updated={counters['updated']} | "
                f"created={counters['created']} | "
                f"skipped_missing={counters['skipped_missing']} | "
                f"skipped_invalid={counters['skipped_invalid']} | "
                f"errors={counters['errors']} | "
                f"dry_run={dry_run}"
            )
        )

    def _sync_one_row(
        self,
        *,
        row: dict[str, Any],
        row_no: int,
        categories: dict[int, Category],
        language_codes: set[str],
        valid_status: set[str],
        create_missing: bool,
        dry_run: bool,
    ) -> str:
        row_id = _to_int(row.get("id"))
        slug = _clean_text(row.get("seo_slug"))

        book = None
        if row_id is not None:
            book = Book.objects.filter(pk=row_id).first()
        if book is None and slug:
            book = Book.objects.filter(seo_slug=slug).first()

        is_new = book is None
        if is_new and not create_missing:
            return "skipped_missing"

        if is_new:
            book = Book()
            if row_id is not None:
                book.id = row_id

        data = self._build_payload(
            row=row,
            row_no=row_no,
            categories=categories,
            language_codes=language_codes,
            valid_status=valid_status,
            is_new=is_new,
        )
        if data is SKIP:
            return "skipped_invalid"

        for field_name, value in data.items():
            setattr(book, field_name, value)

        if not dry_run:
            book.save()

        return "created" if is_new else "updated"

    def _build_payload(
        self,
        *,
        row: dict[str, Any],
        row_no: int,
        categories: dict[int, Category],
        language_codes: set[str],
        valid_status: set[str],
        is_new: bool,
    ) -> dict[str, Any] | object:
        title = _clean_text(row.get("title"))
        author = _clean_text(row.get("author"))
        if is_new and (not title or not author):
            self.stdout.write(
                self.style.WARNING(
                    f"Row {row_no}: missing required title/author for a new record."
                )
            )
            return SKIP

        data: dict[str, Any] = {
            "title": title,
            "title_hausa": _clean_text(row.get("title_hausa")),
            "author": author,
            "translator": _clean_text(row.get("translator")),
            "category_specific": _clean_text(row.get("category_specific")),
            "description": _clean_text(row.get("description")),
            "table_of_contents": _to_json_list(row.get("table_of_contents")),
            "tags": _to_json_list(row.get("tags")),
            "year": _to_int(row.get("year")),
            "status": _clean_text(row.get("status")),
            "approved": _to_bool(row.get("approved")),
            "file": _clean_text(row.get("file")),
            "cover": _clean_text(row.get("cover")),
            "seo_title": _clean_text(row.get("seo_title")),
            "seo_description": _clean_text(row.get("seo_description")),
            "seo_slug": _clean_text(row.get("seo_slug")),
            "view_count": _to_int(row.get("view_count")),
            "download_count": _to_int(row.get("download_count")),
        }

        max_lengths = {
            "title": 500,
            "title_hausa": 500,
            "author": 300,
            "translator": 300,
            "category_specific": 200,
            "status": 20,
            "seo_title": 200,
            "seo_description": 500,
            "seo_slug": 191,
            "file": 100,
            "cover": 100,
        }
        for field_name, max_len in max_lengths.items():
            current = data.get(field_name)
            if not isinstance(current, str):
                continue
            trimmed = _trim_to_max(current, max_len)
            if trimmed != current:
                self.stdout.write(
                    self.style.WARNING(
                        f"Row {row_no}: {field_name} was truncated to {max_len} chars."
                    )
                )
                data[field_name] = trimmed

        status = data["status"]
        if status and status not in valid_status:
            self.stdout.write(
                self.style.WARNING(
                    f"Row {row_no}: invalid status '{status}', expected one of {sorted(valid_status)}."
                )
            )
            return SKIP

        language_code = _clean_text(row.get("language"))
        if language_code and language_code not in language_codes:
            self.stdout.write(
                self.style.WARNING(
                    f"Row {row_no}: unknown language code '{language_code}'."
                )
            )
            return SKIP
        data["language_id"] = language_code

        category_id = _to_int(row.get("category_id"))
        if category_id is not None and category_id not in categories:
            self.stdout.write(
                self.style.WARNING(
                    f"Row {row_no}: category_id '{category_id}' does not exist."
                )
            )
            return SKIP
        data["category"] = categories.get(category_id) if category_id is not None else None

        # Drop required nulls only for updates (to avoid invalid model save).
        if data["title"] is None:
            data.pop("title")
        if data["author"] is None:
            data.pop("author")
        if data["approved"] is None:
            data.pop("approved")
        if data["status"] is None:
            data.pop("status")
        if data["view_count"] is None:
            data.pop("view_count")
        if data["download_count"] is None:
            data.pop("download_count")

        return data
