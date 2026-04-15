import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from books.ai_service import call_ai, parse_json_response

LANGUAGE_MAP = {
    'ar': 'Arabic',
    'en': 'English',
    'sw': 'Swahili',
    'am': 'Amharic',
    'ha': 'Hausa'
}

class Command(BaseCommand):
    help = 'Auto-Translates missing JSON locale strings based on a primary source (default: ha)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='ha',
            help='Source language code (e.g., ha)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Translate strings even if they exist but have the same value as source'
        )

    def handle(self, *args, **options):
        source_lang = options['source']
        force = options['force']
        
        locale_dir = os.path.join(settings.BASE_DIR, 'locale')
        source_path = os.path.join(locale_dir, f'{source_lang}.json')
        
        if not os.path.exists(source_path):
            self.stdout.write(self.style.ERROR(f"Source file not found: {source_path}"))
            return
            
        with open(source_path, 'r', encoding='utf-8') as f:
            try:
                source_data = json.load(f)
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR(f"Invalid JSON in source file: {source_path}"))
                return
        
        target_langs = [lang for lang in LANGUAGE_MAP.keys() if lang != source_lang]
        
        for target_lang in target_langs:
            target_path = os.path.join(locale_dir, f'{target_lang}.json')
            
            target_data = {}
            if os.path.exists(target_path):
                with open(target_path, 'r', encoding='utf-8') as f:
                    try:
                        target_data = json.load(f)
                    except json.JSONDecodeError:
                        self.stdout.write(self.style.ERROR(f"Invalid JSON in target file: {target_path} (replacing with empty dict)"))
            
            missing_keys = {}
            
            # Find what needs translation
            for key, value in source_data.items():
                if not value:
                    continue  # skip empty source values
                    
                target_value = target_data.get(key)
                
                # It needs translation if:
                # 1. It's missing
                # 2. It's empty
                # 3. Force is enabled and it equals the source text (meaning it wasn't translated yet)
                needs_translation = False
                if target_value is None or str(target_value).strip() == "":
                    needs_translation = True
                elif force and target_value == value and key != value:
                    # sometimes the key is english/hausa and value is the same, so translating it is needed.
                    # but maybe some words are exactly the same in both languages (rare).
                    needs_translation = True
                    
                # Small exception: if the value is purely symbols/numbers like "&copy; 2026...", don't translate
                if needs_translation:
                    # Minimal check for exact keys that don't need translation (numbers, exact symbols)
                    # For simplicity, we just pass everything to AI
                    missing_keys[key] = value

            if not missing_keys:
                self.stdout.write(self.style.SUCCESS(f"No missing translations for {target_lang}"))
                continue
                
            self.stdout.write(self.style.WARNING(f"Found {len(missing_keys)} missing translations for {target_lang}"))
            
            # Batch translate in chunks of 20
            chunks = []
            chunk = {}
            for k, v in missing_keys.items():
                chunk[k] = v
                if len(chunk) >= 20:
                    chunks.append(chunk)
                    chunk = {}
            if chunk:
                chunks.append(chunk)
                
            for i, chunk_dict in enumerate(chunks):
                self.stdout.write(f"Translating chunk {i+1}/{len(chunks)} for {target_lang}...")
                
                prompt = self.build_prompt(chunk_dict, source_lang, target_lang)
                try:
                    response_text = call_ai(prompt)
                    translated_chunk = parse_json_response(response_text)
                    
                    # Merge translated chunk
                    for k, v in translated_chunk.items():
                        if k in target_data:
                            target_data[k] = v
                        else:
                            # Reconstruct target_data dict maintaining some order?
                            target_data[k] = v
                            
                    self.stdout.write(self.style.SUCCESS(f"Successfully translated chunk {i+1}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error translating chunk {i+1}: {e}"))
            
            # Sort the dictionary alphabetically by key to maintain consistency
            target_data = dict(sorted(target_data.items()))
            
            # Save the file
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(target_data, f, ensure_ascii=False, indent=2)
                
            self.stdout.write(self.style.SUCCESS(f"Updated {target_path}"))

    def build_prompt(self, items_to_translate: dict, source_lang: str, target_lang: str) -> str:
        source_name = LANGUAGE_MAP.get(source_lang, source_lang)
        target_name = LANGUAGE_MAP.get(target_lang, target_lang)
        
        json_str = json.dumps(items_to_translate, ensure_ascii=False, indent=2)
        
        return f"""You are a professional localization expert. Translate the following JSON values from {source_name} to {target_name}.

Rules:
1. ONLY translate the VALUES. The KEYS must remain EXACTLY the same.
2. Maintain any HTML tags, emojis, or variables like {{name}}.
3. Respond with ONLY the translated JSON object. No Markdown blocks, no explanations.

JSON to translate:
{json_str}
"""
