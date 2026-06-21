import os
import sys
import json
import re
import subprocess
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

PO_HEADER_TEMPLATE = """\
# Translation for {name_english} ({code})
# This file is distributed under the same license as the project.
#
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Language: {code}\\n"
"""

def _unescape_po_str(s: str) -> str:
    return s.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')

def _escape_po_str(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

def _parse_po(content: str) -> list[dict]:
    entries = []
    lines = content.split('\n')
    current_entry = {'comments': [], 'msgid': None, 'msgstr': None}
    in_msgid, in_msgstr = False, False

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            if current_entry['msgid'] is not None:
                entries.append(current_entry)
                current_entry = {'comments': [], 'msgid': None, 'msgstr': None}
            in_msgid, in_msgstr = False, False
            continue

        if line_stripped.startswith('#'):
            current_entry['comments'].append(line)
            continue

        if line_stripped.startswith('msgid '):
            in_msgid, in_msgstr = True, False
            current_entry['msgid'] = re.match(r'^msgid\s+"(.*)"$', line_stripped).group(1)
            continue

        if line_stripped.startswith('msgstr '):
            in_msgid, in_msgstr = False, True
            current_entry['msgstr'] = re.match(r'^msgstr\s+"(.*)"$', line_stripped).group(1)
            continue

        if line_stripped.startswith('"') and line_stripped.endswith('"'):
            val = line_stripped[1:-1]
            if in_msgid:
                current_entry['msgid'] += val
            elif in_msgstr:
                current_entry['msgstr'] += val
    
    if current_entry['msgid'] is not None:
        entries.append(current_entry)
    return entries

def update_provision_progress(code: str, progress: int, message: str, log_line: str = None, status: str = 'processing', error_msg: str = None):
    from django.core.cache import cache
    cache_key = f"provision_progress_{code.strip().lower()}"
    data = cache.get(cache_key) or {'status': 'pending', 'progress': 0, 'message': '', 'log': [], 'errors': []}
    data['status'] = status
    data['progress'] = progress
    data['message'] = message
    if log_line:
        data['log'].append(log_line)
    if error_msg:
        data['errors'].append(error_msg)
        data['log'].append(f"❌ {error_msg}")
    cache.set(cache_key, data, 3600)

def _translate_po_entries(entries: list[dict], target_lang_name: str, code: str = None) -> dict[str, str]:
    from books.ai_service import call_ai, parse_json_response
    items_to_translate = [{'id': e['msgid'], 'text': _unescape_po_str(e['msgstr']) or e['msgid']} for e in entries if e['msgid']]
    translated_map = {}
    if not items_to_translate: return translated_map

    batch_size = 40
    batches = [items_to_translate[i:i + batch_size] for i in range(0, len(items_to_translate), batch_size)]

    for i, batch in enumerate(batches):
        prompt_data = {item['id']: item['text'] for item in batch}
        prompt = f"Translate the following JSON translation values to {target_lang_name}. Do NOT translate keys:\n{json.dumps(prompt_data, ensure_ascii=False)}"
        percent = 10 + int((i / len(batches)) * 50)
        update_provision_progress(code, percent, f"Translating panel strings (batch {i+1}/{len(batches)})...")
        try:
            res = call_ai(prompt)
            translated_chunk = parse_json_response(res)
            translated_map.update(translated_chunk)
        except Exception as e:
            logger.error("Po translation failed: %s", e)
            translated_map.update({item['id']: item['text'] for item in batch})
    return translated_map

def _translate_json_file(source_path: Path, target_path: Path, target_lang_name: str, code: str = None) -> tuple[bool, str]:
    from books.ai_service import call_ai, parse_json_response
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
    except Exception as e:
        return False, str(e)

    items = [{'key': k, 'text': v} for k, v in source_data.items() if v]
    translated_map = {}
    if items:
        batch_size = 40
        batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
        for i, batch in enumerate(batches):
            prompt_data = {item['key']: item['text'] for item in batch}
            prompt = f"Translate the following frontend strings values to {target_lang_name}. Keep HTML tags intact:\n{json.dumps(prompt_data, ensure_ascii=False)}"
            percent = 65 + int((i / len(batches)) * 20)
            update_provision_progress(code, percent, f"Translating frontend strings (batch {i+1}/{len(batches)})...")
            try:
                res = call_ai(prompt)
                translated_map.update(parse_json_response(res))
            except Exception as e:
                translated_map.update({item['key']: item['text'] for item in batch})

    target_data = {k: translated_map.get(k, v) for k, v in source_data.items()}
    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(target_data, f, ensure_ascii=False, indent=2)
    return True, ""

def provision_language(language) -> dict:
    code = language.code.strip().lower()
    name_english = language.name_english or code
    name_native = language.name_native or code

    update_provision_progress(code, 5, "Starting language provisioning...", f"Initializing language setup for {name_native}")
    result = {"po_path": None, "mo_path": None, "po_created": False, "mo_ok": False, "settings_updated": False, "errors": []}

    locale_paths = getattr(settings, "LOCALE_PATHS", [])
    locale_root = Path(locale_paths[0]) if locale_paths else Path(settings.BASE_DIR) / "locale"
    lc_dir = locale_root / code / "LC_MESSAGES"
    lc_dir.mkdir(parents=True, exist_ok=True)

    po_path = lc_dir / "django.po"
    mo_path = lc_dir / "django.mo"
    result["po_path"] = po_path
    result["mo_path"] = mo_path

    if not po_path.exists():
        try:
            source_po = locale_root / "en" / "LC_MESSAGES" / "django.po"
            if source_po.exists():
                with open(source_po, 'r', encoding='utf-8') as f:
                    entries = _parse_po(f.read())
                translated_map = _translate_po_entries(entries, name_english, code=code)
                header = PO_HEADER_TEMPLATE.format(code=code, name_english=name_english)
                with open(po_path, 'w', encoding='utf-8') as f:
                    f.write(header)
                    for e in entries:
                        if e['msgid'] == '': continue
                        f.write(f'msgid "{_escape_po_str(e["msgid"])}"\n')
                        f.write(f'msgstr "{_escape_po_str(translated_map.get(e["msgid"], e["msgid"]))}"\n\n')
                result["po_created"] = True
        except Exception as e:
            result["errors"].append(str(e))
            update_provision_progress(code, 90, "PO generation failed", error_msg=str(e), status='failed')

    json_path = locale_root / f"{code}.json"
    if not json_path.exists():
        source_json = locale_root / "en.json"
        if source_json.exists():
            ok, err = _translate_json_file(source_json, json_path, name_english, code=code)
            if not ok: 
                result["errors"].append(err)
                update_provision_progress(code, 90, "JSON translation failed", error_msg=err, status='failed')

    # Compile messages
    try:
        update_provision_progress(code, 90, "Compiling message catalogs...")
        subprocess.run([sys.executable, "manage.py", "compilemessages", "-l", code], cwd=settings.BASE_DIR, capture_output=True)
        result["mo_ok"] = mo_path.exists()
    except Exception as e:
        result["errors"].append(str(e))
        update_provision_progress(code, 95, "Message compilation failed", error_msg=str(e))

    # Update dynamically
    try:
        import django.conf.locale
        if code not in django.conf.locale.LANG_INFO:
            django.conf.locale.LANG_INFO[code] = {
                'bidi': language.direction == 'rtl',
                'code': code,
                'name': name_english,
                'name_local': name_native,
            }

        # Clear translation cache
        from django.utils.translation import trans_real
        trans_real._translations = {}
        from django.utils import translation
        translation.deactivate_all()

        # Clear URL resolver cache
        from django.urls import clear_url_caches
        clear_url_caches()
        result["settings_updated"] = True
    except Exception as e:
        logger.error("Failed to clear URL/translation caches: %s", e)

    update_provision_progress(code, 100, "Done!", "Done!", status='completed')
    return result
