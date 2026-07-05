import hashlib
import logging
import threading
import time
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.core.cache import cache
from .models import Book, Language


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Signal 1: Auto AI generation for new Books
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender=Book)
def trigger_auto_ai_generation(sender, instance, created, **kwargs):
    """
    Triggered after saving a new Book.
    Queues automatic AI metadata generation in the background,
    while using a cache lock to prevent duplicate runs.
    """
    if created:
        # 1. Check bypass lock (set by manual review/approval flow)
        hashed_title = hashlib.md5(instance.title.encode('utf-8')).hexdigest()
        bypass_key = f"prevent_auto_ai_{hashed_title}"
        if cache.get(bypass_key):
            logger.info(f"Auto AI bypassed for '{instance.title}' (Handled by manual review approval).")
            cache.delete(bypass_key)
            return

        # 2. Deduplication lock
        lock_key = f"auto_ai_queued_{instance.pk}"
        if not cache.get(lock_key):
            cache.set(lock_key, True, 600)  # 10-minute lock
            logger.info(f"Triggering auto AI generation for Book {instance.pk}")

            from .tasks import queue_auto_generate_book_metadata_task
            transaction.on_commit(lambda: queue_auto_generate_book_metadata_task(instance.pk))


# ─────────────────────────────────────────────────────────────
# Signal 2: Auto provision new Languages
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender=Language)
def auto_provision_language(sender, instance, created, **kwargs):
    """
    Triggered after saving a new Language.
    Runs the full provisioning flow (locale dirs, .po/.json translation,
    compilemessages) in a background thread.
    """
    if created:
        code = instance.code.strip().lower()

        def run_in_thread():
            time.sleep(0.5)  # small delay to ensure DB commit
            try:
                from .services.language_setup import provision_language
                provision_language(instance)
            except Exception as exc:
                logger.error("Language provision failed for %s: %s", code, exc)

        thread = threading.Thread(target=run_in_thread, name=f"provision_lang_{code}")
        thread.daemon = True
        transaction.on_commit(lambda: thread.start())


@receiver(post_save, sender=Book)
def invalidate_book_cache_on_save(sender, instance, **kwargs):
    """Invalidate master books cache when a book is created or updated."""
    from .services.cache import invalidate_book_caches
    invalidate_book_caches()


@receiver(post_delete, sender=Book)
def invalidate_book_cache_on_delete(sender, instance, **kwargs):
    """Invalidate master books cache when a book is deleted."""
    from .services.cache import invalidate_book_caches
    invalidate_book_caches()

