import logging
import threading
import time
from django.db import transaction, close_old_connections
from .models import Book
from .ai_service import _generate_selected_fields

logger = logging.getLogger(__name__)

# Fallback fake decorator in case celery is not installed
try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

def update_book_processing_progress(book_id: int, progress: int, message: str, log_line: str = None, status: str = 'processing', error_msg: str = None):
    from django.core.cache import cache
    cache_key = f"book_processing_{book_id}"
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

@shared_task(bind=True, max_retries=3)
def auto_generate_book_metadata_task(self, book_id=None, *args, **kwargs):
    """
    Background task to automatically generate SEO and missing metadata for a book.
    """
    if book_id is None and args:
        book_id = args[0]
        
    if book_id is None:
        logger.error("auto_generate_book_metadata_task called without book_id")
        return

    update_book_processing_progress(
        book_id,
        progress=5,
        message="جاري بدء معالجة بيانات الكتاب...",
        log_line="تم بدء المهمة الخلفية لتوليد البيانات."
    )

    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        error_msg = f"الكتاب رقم {book_id} غير موجود."
        logger.error(error_msg)
        update_book_processing_progress(book_id, progress=100, message=error_msg, error_msg=error_msg, status='failed')
        return

    # Check for missing metadata fields to generate
    fields_to_generate = []
    if not book.description or book.description.strip() == '':
        fields_to_generate.append('description')

    if not book.table_of_contents or book.table_of_contents == []:
        fields_to_generate.append('toc')

    if not book.tags or book.tags == []:
        fields_to_generate.append('tags')

    if not book.seo_title or not book.seo_description or not book.seo_slug:
        fields_to_generate.append('seo')

    if not fields_to_generate:
        logger.info('Book %s already has complete metadata.', book_id)
        update_book_processing_progress(
            book_id,
            progress=100,
            message="الكتاب يحتوي بالفعل على كافة البيانات؛ لا حاجة للتوليد بالذكاء الاصطناعي.",
            log_line="تنبيه: كافة الحقول (الوصف، الفهرس، الكلمات الدلالية، والسيو) ممتلئة بالفعل.",
            status='completed'
        )
        return

    logger.info('Starting auto AI generation for Book %s', book_id)
    try:
        _generate_selected_fields(book, fields_to_generate)
        logger.info('Auto AI generation completed for Book %s', book_id)
    except Exception as exc:
        logger.error('Auto AI generation error for Book %s: %s', book_id, exc)
        update_book_processing_progress(
            book_id,
            progress=100,
            message="فشلت عملية توليد البيانات.",
            error_msg=str(exc),
            status='failed'
        )


def queue_auto_generate_book_metadata_task(book_id: int):
    """
    Queues the auto AI generation task. If Celery is active, uses apply_async.
    Otherwise, falls back to a background thread.
    """
    print(f"[AI GENERATION] Queue helper called for Book {book_id}")
    celery_active = False
    try:
        from hausa_books.celery import app as celery_app
        insp = celery_app.control.inspect(timeout=1.0)
        if insp and insp.ping():
            celery_active = True
    except Exception:
        celery_active = False

    if celery_active:
        try:
            if hasattr(auto_generate_book_metadata_task, 'apply_async'):
                auto_generate_book_metadata_task.apply_async(args=(book_id,), ignore_result=True)
                print(f"[AI GENERATION] Queued on Celery for Book {book_id}")
                return "celery"
        except Exception:
            pass

    # Threading fallback
    def thread_target():
        print(f"[AI GENERATION] Background thread started for Book {book_id}")
        time.sleep(1.0)
        close_old_connections()
        try:
            if hasattr(auto_generate_book_metadata_task, 'run'):
                try:
                    auto_generate_book_metadata_task.run(book_id)
                except TypeError:
                    auto_generate_book_metadata_task.run(None, book_id)
            else:
                auto_generate_book_metadata_task(None, book_id)
            print(f"[AI GENERATION] Task finished executing in thread for Book {book_id}")
        except Exception as e:
            logger.error("Thread fallback failed for Book %s: %s", book_id, e)
            print(f"[AI GENERATION] Thread target error for Book {book_id}: {e}")
        finally:
            close_old_connections()

    # Check database transaction context
    from django.db import transaction
    connection = transaction.get_connection()
    if connection.in_atomic_block:
        print(f"[AI GENERATION] Database in atomic block. Deferring thread start to transaction commit.")
        transaction.on_commit(lambda: threading.Thread(target=thread_target, daemon=True).start())
    else:
        print(f"[AI GENERATION] Database autocommit active. Starting thread immediately.")
        threading.Thread(target=thread_target, daemon=True).start()

    return "thread"
