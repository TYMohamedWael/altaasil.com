"""
books/views_pdf.py
PDF Page Management Views
"""
import os
import json
import io

from django.contrib import admin
from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.template.response import TemplateResponse

from pypdf import PdfReader, PdfWriter

from books.models import Book


def _get_reader_from_memory(book):
    """يقرأ الـ PDF للذاكرة من أي Storage (Local أو Cloud) أو يرجع None إذا لم يوجد."""
    if not book.file:
        return None
    try:
        with book.file.open('rb') as f:
            data = f.read()
        return PdfReader(io.BytesIO(data))
    except Exception:
        return None


def _save_modified_pdf(book, writer: PdfWriter) -> int:
    """يحفظ الـ PDF (سواء كان تعديل لملف موجود أو إنشاء ملف جديد)."""
    output = io.BytesIO()
    writer.write(output)
    
    file_content = ContentFile(output.getvalue())
    if book.file:
        name = book.file.name
        book.file.delete(save=False) # نحذف القديم لتجنب إضافة أرقام للاسم _1.pdf
        book.file.save(os.path.basename(name), file_content, save=True)
    else:
        # إنشاء ملف جديد
        filename = f"book_{book.pk}_generated.pdf"
        book.file.save(filename, file_content, save=True)
        
    return len(writer.pages)


# -------------------------------------------------------
# 1. صفحة محرر الـ PDF
# -------------------------------------------------------
def pdf_editor_view(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    reader = _get_reader_from_memory(book)
    total_pages = len(reader.pages) if reader else 0

    context = {
        **admin.site.each_context(request),
        "book": book,
        "total_pages": total_pages,
        "title": f"محرر PDF — {book}",
    }
    return TemplateResponse(request, "admin/pdf_editor.html", context)


# -------------------------------------------------------
# 2. API: معاينة صفحة
# -------------------------------------------------------
def pdf_page_preview(request, book_id, page_number):
    book = get_object_or_404(Book, pk=book_id)
    reader = _get_reader_from_memory(book)
    
    if not reader:
        return HttpResponse(
            "<h2 style='text-align:center;font-family:sans-serif;color:#666;margin-top:20%;'>"
            "لا يوجد ملف PDF بعد. قم بإضافة صفحات لإنشاء الملف."
            "</h2>", 
            status=404
        )
        
    total = len(reader.pages)
    if page_number < 1 or page_number > total:
        return JsonResponse({"error": "رقم الصفحة غير صحيح"}, status=400)

    writer = PdfWriter()
    writer.add_page(reader.pages[page_number - 1])
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    response = HttpResponse(output.read(), content_type="application/pdf")
    response["X-Frame-Options"] = "SAMEORIGIN"
    response["Content-Disposition"] = "inline"
    return response


# -------------------------------------------------------
# 3. API: حذف صفحة
# -------------------------------------------------------
@require_http_methods(["POST"])
def pdf_delete_page(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    reader = _get_reader_from_memory(book)
    
    if not reader:
        return JsonResponse({"error": "لا يوجد ملف للحذف منه"}, status=400)

    data = json.loads(request.body)
    page_number = int(data.get("page_number", 0))
    total = len(reader.pages)

    if page_number < 1 or page_number > total:
        return JsonResponse({"error": f"رقم الصفحة يجب أن يكون بين 1 و {total}"}, status=400)
    
    if total <= 1:
        # إذا كانت آخر صفحة، نحذف الملف بالكامل
        book.file.delete(save=True)
        return JsonResponse({
            "success": True,
            "message": "تم حذف الصفحة الأخيرة (الملف الآن فارغ)",
            "new_page_count": 0,
        })

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i != page_number - 1:
            writer.add_page(page)

    new_count = _save_modified_pdf(book, writer)
    return JsonResponse({
        "success": True,
        "message": f"تم حذف الصفحة {page_number} بنجاح",
        "new_page_count": new_count,
    })


# -------------------------------------------------------
# 4. API: إضافة صفحة فارغة
# -------------------------------------------------------
@require_http_methods(["POST"])
def pdf_add_blank_page(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    reader = _get_reader_from_memory(book)
    pages = reader.pages if reader else []
    total = len(pages)

    data = json.loads(request.body)
    after_page = int(data.get("after_page", 0))

    if after_page < 0 or after_page > total:
        return JsonResponse({"error": f"موضع الإضافة يجب أن يكون بين 0 و {total}"}, status=400)

    blank_writer = PdfWriter()
    blank_writer.add_blank_page(width=595, height=842)
    blank_buffer = io.BytesIO()
    blank_writer.write(blank_buffer)
    blank_buffer.seek(0)
    blank_page = PdfReader(blank_buffer).pages[0]

    writer = PdfWriter()
    for i, page in enumerate(pages):
        if i == after_page:
            writer.add_page(blank_page)
        writer.add_page(page)
    if after_page == total:
        writer.add_page(blank_page)

    new_count = _save_modified_pdf(book, writer)
    return JsonResponse({
        "success": True,
        "message": f"تم إضافة صفحة فارغة بعد الصفحة {after_page}",
        "new_page_count": new_count,
        "inserted_at": after_page + 1,
    })


# -------------------------------------------------------
# 5. API: رفع صفحة PDF أو صورة
# -------------------------------------------------------
@require_http_methods(["POST"])
def pdf_upload_page(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    reader = _get_reader_from_memory(book)
    pages = reader.pages if reader else []
    total = len(pages)

    uploaded_file = request.FILES.get("page_file")
    after_page = int(request.POST.get("after_page", 0))

    if not uploaded_file:
        return JsonResponse({"error": "لم يتم رفع أي ملف"}, status=400)

    ext = uploaded_file.name.lower()
    if not ext.endswith(('.pdf', '.png', '.jpg', '.jpeg')):
        return JsonResponse({"error": "يمكنك رفع ملفات PDF أو صور فقط"}, status=400)

    if after_page < 0 or after_page > total:
        return JsonResponse({"error": f"موضع الإضافة يجب أن يكون بين 0 و {total}"}, status=400)

    if ext.endswith('.pdf'):
        new_reader = PdfReader(io.BytesIO(uploaded_file.read()))
        new_pages = list(new_reader.pages)
    else:
        from PIL import Image
        img = Image.open(uploaded_file)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img_pdf_io = io.BytesIO()
        img.save(img_pdf_io, format='PDF', resolution=100.0)
        img_pdf_io.seek(0)
        new_reader = PdfReader(img_pdf_io)
        new_pages = list(new_reader.pages)

    writer = PdfWriter()
    for i, page in enumerate(pages):
        if i == after_page:
            for new_page in new_pages:
                writer.add_page(new_page)
        writer.add_page(page)
    if after_page == total:
        for new_page in new_pages:
            writer.add_page(new_page)

    new_count = _save_modified_pdf(book, writer)
    return JsonResponse({
        "success": True,
        "message": f"تم إضافة {len(new_pages)} صفحة بنجاح",
        "new_page_count": new_count,
        "pages_added": len(new_pages),
    })


# -------------------------------------------------------
# 6. API: معلومات الكتاب
# -------------------------------------------------------
def pdf_book_info(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    reader = _get_reader_from_memory(book)
    return JsonResponse({
        "book_id": book.pk,
        "title": str(book),
        "total_pages": len(reader.pages) if reader else 0,
        "pdf_url": book.file.url if book.file else None,
    })
