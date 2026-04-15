"""
🕷️ Smart Book Scraper - Littattafan Hausa
==========================================
Crawls digital libraries and book sites for Hausa Islamic books.
Uses LLM to verify content is Islamic before importing.

Usage:
    python manage.py scrape_books                    # Scrape all sources
    python manage.py scrape_books --source archive   # Specific source
    python manage.py scrape_books --verify-only      # Only verify discovered books
    python manage.py scrape_books --import-verified   # Import verified books into library
    python manage.py scrape_books --list-sources      # Show available sources
    python manage.py scrape_books --dry-run           # Don't save, just show what would be found
"""
import os
import re
import json
import time
import logging
import hashlib
import requests
from urllib.parse import urljoin, urlparse, quote
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils.text import slugify

from books.models import Book, Category, ScrapedBook

logger = logging.getLogger(__name__)

# ============================================================
# SCRAPER SOURCES CONFIGURATION
# ============================================================
SCRAPER_SOURCES = {
    'archive': {
        'name': 'Internet Archive',
        'base_url': 'https://archive.org',
        'search_url': 'https://archive.org/advancedsearch.php',
        'enabled': True,
        'type': 'api',
        'description': 'Largest digital library - has Hausa Islamic texts',
    },
    'openlibrary': {
        'name': 'Open Library',
        'base_url': 'https://openlibrary.org',
        'search_url': 'https://openlibrary.org/search.json',
        'enabled': True,
        'type': 'api',
        'description': 'Open Library catalog search',
    },
    'google_books': {
        'name': 'Google Books',
        'base_url': 'https://www.googleapis.com/books/v1',
        'search_url': 'https://www.googleapis.com/books/v1/volumes',
        'enabled': True,
        'type': 'api',
        'description': 'Google Books API - metadata and previews',
    },
}

# Search queries to find Hausa Islamic books
SEARCH_QUERIES = [
    'hausa islamic books',
    'littattafan hausa',
    'hausa quran tafsir',
    'hausa fiqh',
    'hausa hadith',
    'hausa aqeedah',
    'islamiyya hausa',
    'sheikh hausa pdf',
    'hausa arabic islamic',
    'tawheed hausa',
    'sunnah hausa',
    'fiqhu hausa',
]

# Islamic categories for classification
ISLAMIC_CATEGORIES = [
    'Aqeedah', 'Fiqh', 'Hadith', 'Tafsir', 'Seerah',
    'Tazkiyah', 'Arabic', 'Usul al-Fiqh', 'Quran', 'Dawah',
    'Islamic History', 'Islamic Education',
]


class Command(BaseCommand):
    help = '🕷️ Smart scraper: crawl digital libraries for Hausa Islamic books'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, help='Specific source to scrape (archive/openlibrary/google_books)')
        parser.add_argument('--verify-only', action='store_true', help='Only run LLM verification on discovered books')
        parser.add_argument('--import-verified', action='store_true', help='Import verified books into main library')
        parser.add_argument('--list-sources', action='store_true', help='List available scraper sources')
        parser.add_argument('--dry-run', action='store_true', help='Show results without saving')
        parser.add_argument('--max-results', type=int, default=50, help='Max results per query (default: 50)')
        parser.add_argument('--query', type=str, help='Custom search query')

    def handle(self, *args, **options):
        if options['list_sources']:
            return self._list_sources()

        if options['verify_only']:
            return self._verify_discovered()

        if options['import_verified']:
            return self._import_verified()

        self.dry_run = options['dry_run']
        self.max_results = options['max_results']

        sources = SCRAPER_SOURCES
        if options['source']:
            key = options['source']
            if key not in sources:
                raise CommandError(f"Unknown source: {key}. Use --list-sources")
            sources = {key: sources[key]}

        queries = [options['query']] if options['query'] else SEARCH_QUERIES

        total_found = 0
        total_new = 0

        for source_key, source_config in sources.items():
            if not source_config['enabled']:
                continue
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.SUCCESS(f"🔍 Scraping: {source_config['name']}"))
            self.stdout.write(f"{'='*60}")

            scraper = self._get_scraper(source_key)
            if not scraper:
                self.stdout.write(self.style.WARNING(f"  ⚠️ No scraper for {source_key}"))
                continue

            for query in queries:
                self.stdout.write(f"\n  📝 Query: '{query}'")
                try:
                    results = scraper(query, source_config)
                    total_found += len(results)

                    for item in results:
                        saved = self._save_discovered(item, source_key)
                        if saved:
                            total_new += 1

                    self.stdout.write(f"     Found: {len(results)} results")
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"     ❌ Error: {e}"))
                    logger.exception(f"Scraper error for {source_key}/{query}")

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS(
            f"✅ Done! Found: {total_found} | New: {total_new}"
        ))
        self.stdout.write(f"{'='*60}")

        # Auto-verify new discoveries
        if total_new > 0 and not self.dry_run:
            self.stdout.write(f"\n🤖 Running AI verification on {total_new} new books...")
            self._verify_discovered()

    # ============================================================
    # SCRAPERS
    # ============================================================

    def _get_scraper(self, source_key):
        scrapers = {
            'archive': self._scrape_archive,
            'openlibrary': self._scrape_openlibrary,
            'google_books': self._scrape_google_books,
        }
        return scrapers.get(source_key)

    def _scrape_archive(self, query, config):
        """Scrape Internet Archive via their API"""
        results = []
        params = {
            'q': f'{query} AND mediatype:texts',
            'fl[]': ['identifier', 'title', 'creator', 'description', 'language', 'downloads'],
            'sort[]': 'downloads desc',
            'rows': min(self.max_results, 50),
            'page': 1,
            'output': 'json',
        }

        try:
            resp = requests.get(config['search_url'], params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for doc in data.get('response', {}).get('docs', []):
                identifier = doc.get('identifier', '')
                title = doc.get('title', '')
                if not title:
                    continue

                results.append({
                    'title': title if isinstance(title, str) else title[0] if title else '',
                    'author': self._extract_first(doc.get('creator', '')),
                    'description': self._extract_first(doc.get('description', '')),
                    'language': self._extract_first(doc.get('language', '')),
                    'source_url': f"https://archive.org/details/{identifier}",
                    'file_url': f"https://archive.org/download/{identifier}/{identifier}.pdf",
                })
        except Exception as e:
            logger.error(f"Archive.org error: {e}")

        return results

    def _scrape_openlibrary(self, query, config):
        """Scrape Open Library via their API"""
        results = []
        params = {
            'q': query,
            'limit': min(self.max_results, 50),
            'language': 'hau',  # Hausa ISO code
        }

        try:
            resp = requests.get(config['search_url'], params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for doc in data.get('docs', []):
                title = doc.get('title', '')
                if not title:
                    continue

                key = doc.get('key', '')
                authors = doc.get('author_name', [])

                results.append({
                    'title': title,
                    'author': authors[0] if authors else '',
                    'description': self._extract_first(doc.get('first_sentence', {}).get('value', '') if isinstance(doc.get('first_sentence'), dict) else ''),
                    'language': 'ha' if 'hau' in doc.get('language', []) else '',
                    'source_url': f"https://openlibrary.org{key}",
                    'file_url': '',
                })
        except Exception as e:
            logger.error(f"OpenLibrary error: {e}")

        return results

    def _scrape_google_books(self, query, config):
        """Scrape Google Books via their free API"""
        results = []
        params = {
            'q': query,
            'maxResults': min(self.max_results, 40),
            'printType': 'books',
            'langRestrict': 'ha',
        }

        api_key = os.environ.get('GOOGLE_BOOKS_API_KEY', '')
        if api_key:
            params['key'] = api_key

        try:
            resp = requests.get(config['search_url'], params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get('items', []):
                info = item.get('volumeInfo', {})
                title = info.get('title', '')
                if not title:
                    continue

                authors = info.get('authors', [])
                pdf_link = item.get('accessInfo', {}).get('pdf', {}).get('downloadLink', '')

                results.append({
                    'title': title,
                    'author': authors[0] if authors else '',
                    'description': info.get('description', '')[:500] if info.get('description') else '',
                    'language': info.get('language', ''),
                    'source_url': info.get('infoLink', f"https://books.google.com/books?id={item.get('id', '')}"),
                    'file_url': pdf_link,
                })
        except Exception as e:
            logger.error(f"Google Books error: {e}")

        return results

    # ============================================================
    # SAVE & DEDUPLICATE
    # ============================================================

    def _save_discovered(self, item, source_key):
        """Save a discovered book, skip if already exists"""
        source_url = item.get('source_url', '')
        if not source_url:
            return False

        if self.dry_run:
            self.stdout.write(f"     📖 [DRY] {item['title'][:60]}")
            return True

        if ScrapedBook.objects.filter(source_url=source_url).exists():
            return False

        ScrapedBook.objects.create(
            source_url=source_url,
            source_site=SCRAPER_SOURCES[source_key]['name'],
            title=item.get('title', '')[:500],
            author=item.get('author', '')[:300] if item.get('author') else None,
            language=item.get('language', '')[:50] if item.get('language') else None,
            file_url=item.get('file_url', '') or None,
            description=item.get('description', '') or None,
            status='discovered',
        )
        self.stdout.write(f"     ✅ NEW: {item['title'][:60]}")
        return True

    # ============================================================
    # AI VERIFICATION
    # ============================================================

    def _verify_discovered(self):
        """Use LLM to verify discovered books are Islamic content"""
        unverified = ScrapedBook.objects.filter(status='discovered')
        count = unverified.count()

        if count == 0:
            self.stdout.write(self.style.WARNING("  No unverified books found."))
            return

        self.stdout.write(f"\n🤖 Verifying {count} discovered books with AI...")

        # Batch verify (send multiple books per API call to save costs)
        batch_size = 10
        verified_count = 0
        rejected_count = 0

        for i in range(0, count, batch_size):
            batch = list(unverified[i:i+batch_size])
            try:
                results = self._ai_verify_batch(batch)
                for book, analysis in zip(batch, results):
                    book.ai_analysis = analysis
                    if analysis.get('is_islamic', False) and analysis.get('confidence', 0) >= 0.6:
                        book.status = 'verified'
                        verified_count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f"  ✅ {book.title[:50]} → {analysis.get('suggested_category', '?')} "
                            f"({int(analysis.get('confidence', 0)*100)}%)"
                        ))
                    else:
                        book.status = 'rejected'
                        rejected_count += 1
                        self.stdout.write(self.style.WARNING(
                            f"  ❌ {book.title[:50]} → {analysis.get('reason', 'Not Islamic')}"
                        ))
                    book.save()

                time.sleep(1)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ AI Error: {e}"))
                logger.exception("AI verification error")

        self.stdout.write(f"\n📊 Verification: ✅ {verified_count} verified | ❌ {rejected_count} rejected")

    def _ai_verify_batch(self, books):
        """Send a batch of books to LLM for Islamic content verification"""
        books_text = ""
        for i, book in enumerate(books, 1):
            books_text += f"\n--- Book {i} ---\n"
            books_text += f"Title: {book.title}\n"
            if book.author:
                books_text += f"Author: {book.author}\n"
            if book.description:
                books_text += f"Description: {book.description[:200]}\n"
            if book.language:
                books_text += f"Language: {book.language}\n"

        prompt = f"""You are an Islamic book classifier for a Hausa Islamic library platform.
Analyze each book below and determine:
1. Is it an Islamic/religious book? (true/false)
2. Confidence score (0.0 to 1.0)
3. Suggested category from: {', '.join(ISLAMIC_CATEGORIES)}
4. Brief reason for your decision

Books to analyze:
{books_text}

Return ONLY a JSON array with one object per book:
[
  {{"is_islamic": true/false, "confidence": 0.0-1.0, "suggested_category": "...", "reason": "..."}},
  ...
]
"""

        # Try OpenAI
        openai_key = os.environ.get('OPENAI_API_KEY', '')
        if openai_key:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
                messages=[
                    {"role": "system", "content": "You are an Islamic book classifier. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            text = response.choices[0].message.content.strip()
            # Extract JSON
            text = re.sub(r'^```json?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            results = json.loads(text)

            # Pad if fewer results than books
            while len(results) < len(books):
                results.append({"is_islamic": False, "confidence": 0.0, "suggested_category": "", "reason": "No analysis"})
            return results

        # Try Gemini
        gemini_key = os.environ.get('GEMINI_API_KEY', '')
        if gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            text = response.text.strip()
            text = re.sub(r'^```json?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            results = json.loads(text)
            while len(results) < len(books):
                results.append({"is_islamic": False, "confidence": 0.0, "suggested_category": "", "reason": "No analysis"})
            return results

        raise CommandError("❌ No AI provider configured! Set OPENAI_API_KEY or GEMINI_API_KEY in .env")

    # ============================================================
    # IMPORT VERIFIED → MAIN LIBRARY
    # ============================================================

    def _import_verified(self):
        """Import verified scraped books into the main Book model"""
        verified = ScrapedBook.objects.filter(status='verified')
        count = verified.count()

        if count == 0:
            self.stdout.write(self.style.WARNING("  No verified books to import."))
            return

        self.stdout.write(f"\n📥 Importing {count} verified books...")

        imported = 0
        for scraped in verified:
            try:
                # Find or guess category
                category = self._match_category(scraped.ai_analysis.get('suggested_category', ''))

                # Check for duplicate by title
                if Book.objects.filter(title__iexact=scraped.title).exists():
                    self.stdout.write(f"  ⏭️ Skip (duplicate): {scraped.title[:50]}")
                    scraped.status = 'imported'
                    scraped.save()
                    continue

                # Download PDF if available
                file_content = None
                if scraped.file_url:
                    try:
                        resp = requests.get(scraped.file_url, timeout=60, stream=True)
                        if resp.status_code == 200 and len(resp.content) > 1000:
                            file_content = resp.content
                    except Exception:
                        pass

                # Create book
                book = Book(
                    title=scraped.title,
                    title_hausa=scraped.title,  # Will need translation later
                    author=scraped.author or 'Ba a sani ba',
                    category=category,
                    description=scraped.description or '',
                    language='ha' if scraped.language and 'ha' in scraped.language.lower() else 'ar',
                    status='draft',
                    approved=False,
                )

                if file_content:
                    filename = slugify(scraped.title[:50]) + '.pdf'
                    book.file.save(filename, ContentFile(file_content), save=False)

                book.save()

                scraped.status = 'imported'
                scraped.imported_book = book
                scraped.save()

                imported += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  ✅ Imported: {scraped.title[:50]} → {category or 'Uncategorized'}"
                ))

            except Exception as e:
                scraped.status = 'failed'
                scraped.save()
                self.stdout.write(self.style.ERROR(f"  ❌ Failed: {scraped.title[:50]} - {e}"))

        self.stdout.write(f"\n📊 Imported: {imported}/{count}")

    def _match_category(self, suggested):
        """Match AI suggested category to existing Category model"""
        if not suggested:
            return None

        # Try exact match
        cat = Category.objects.filter(name__iexact=suggested).first()
        if cat:
            return cat

        # Try partial match
        for word in suggested.split():
            cat = Category.objects.filter(name__icontains=word).first()
            if cat:
                return cat

        return None

    # ============================================================
    # UTILITIES
    # ============================================================

    def _list_sources(self):
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(self.style.SUCCESS("📚 Available Scraper Sources"))
        self.stdout.write(f"{'='*50}")
        for key, src in SCRAPER_SOURCES.items():
            status = '✅' if src['enabled'] else '❌'
            self.stdout.write(f"  {status} {key:15} → {src['name']}")
            self.stdout.write(f"     {src['description']}")
        self.stdout.write("")

    def _extract_first(self, value):
        """Extract first value if list, or return string"""
        if isinstance(value, list):
            return value[0] if value else ''
        return str(value) if value else ''
