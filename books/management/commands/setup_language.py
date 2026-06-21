"""
books/management/commands/setup_language.py

Management command - Provision locale files for one or more languages.

Usage:
    # Provision a single language already in the DB (e.g. Bengali)
    python manage.py setup_language --code bn

    # Multiple languages at once
    python manage.py setup_language --code fr --code id

    # All active languages in the database
    python manage.py setup_language --all
"""

import io
import sys

from django.core.management.base import BaseCommand, CommandError


def _safe(text):
    """
    Encode text to the current stdout encoding, replacing unmappable
    characters with '?' so the command never crashes on Windows cp1252.
    """
    enc = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
    return text.encode(enc, errors='replace').decode(enc)


class Command(BaseCommand):
    help = 'Provision locale (.po/.mo) files for languages and register them in settings.LANGUAGES'

    def add_arguments(self, parser):
        parser.add_argument(
            '--code', '-c',
            action='append',
            dest='codes',
            metavar='LANG_CODE',
            help='ISO language code. Repeat for multiple languages: --code fr --code id',
        )
        parser.add_argument(
            '--all', '-a',
            action='store_true',
            dest='all_active',
            help='Provision all active languages in the database.',
        )

    def handle(self, *args, **options):
        from books.models import Language
        from books.services.language_setup import provision_language

        codes      = options.get('codes') or []
        all_active = options.get('all_active', False)

        if not codes and not all_active:
            raise CommandError(
                'Specify --code <CODE> or --all.\n'
                'Example: python manage.py setup_language --code bn'
            )

        # ── Collect language objects ──────────────────────────────────────────
        if all_active:
            langs = list(Language.objects.filter(is_active=True))
            if not langs:
                self.stdout.write(self.style.WARNING('No active languages found in the database.'))
                return
        else:
            langs = []
            for code in codes:
                code = code.strip().lower()
                try:
                    langs.append(Language.objects.get(code=code))
                except Language.DoesNotExist:
                    raise CommandError(
                        f"Language '{code}' not found in the database.\n"
                        f"Add it first from the admin: /ha/admin/books/language/add/"
                    )

        # ── Provision each language ───────────────────────────────────────────
        success = 0
        failed  = 0

        for lang in langs:
            self.stdout.write(_safe(
                f'\n[...] Provisioning: {lang.name_english} ({lang.code})'
            ))

            try:
                result = provision_language(lang)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'  [ERROR] Exception: {exc}'))
                failed += 1
                continue

            # Report errors
            if result['errors']:
                for err in result['errors']:
                    self.stderr.write(self.style.WARNING(f'  [WARN]  {err}'))
                failed += 1
                continue

            # Report success details
            success += 1

            if result['po_created']:
                self.stdout.write(self.style.SUCCESS(
                    f"  [OK] django.po created : {result['po_path']}"
                ))
            else:
                self.stdout.write(
                    f"  [--] django.po exists  : {result['po_path']}"
                )

            if result['mo_ok']:
                self.stdout.write(self.style.SUCCESS(
                    f"  [OK] django.mo compiled: {result['mo_path']}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    "  [!!] django.mo NOT compiled — check error logs"
                ))

            if result['settings_updated']:
                self.stdout.write(self.style.SUCCESS(
                    f"  [OK] '{lang.code}' added to settings.LANGUAGES"
                ))
            else:
                self.stdout.write(
                    f"  [--] '{lang.code}' already in settings.LANGUAGES"
                )

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write('=' * 60)

        if success:
            self.stdout.write(self.style.SUCCESS(
                f'[DONE] {success} language(s) provisioned successfully.'
            ))
        if failed:
            self.stdout.write(self.style.ERROR(
                f'[FAIL] {failed} language(s) failed — see errors above.'
            ))

        if success and not failed:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                '[NOTE] Restart the server to load new LANGUAGES across all processes.'
            ))
            self.stdout.write(
                _safe('       Then open Rosetta to translate: /<lang>/admin/rosetta/')
            )
