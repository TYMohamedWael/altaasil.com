"""
books/services/ai.py
AI Service for Littattafan Hausa

مزودان:
  ┌─────────────────────────────────────────────────────┐
  │  Groq  (Llama 3)  ← البحث والجلب في crawler.py     │
  │  Gemini           ← توليد الـ metadata (وصف/SEO/…) │
  └─────────────────────────────────────────────────────┘

.env المطلوبة:
  GROQ_API_KEY=gsk_...          ← للبحث
  GEMINI_API_KEY=AIza...        ← للـ metadata
  # اختياري:
  GROQ_MODEL=llama-3.3-70b-versatile
  GEMINI_MODEL=gemini-2.0-flash
"""

import os
import json
import re
import time
import hashlib
import logging
from typing import Optional

os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("https_proxy", None)
os.environ.pop("http_proxy", None)

logger = logging.getLogger(__name__)

# ── Groq ───────────────────────────────────────────────────────────────────────
try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False
    logger.warning("Groq غير مثبت — pip install groq")

# ── Gemini ─────────────────────────────────────────────────────────────────────
try:
    from google import genai as google_genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    logger.warning("Gemini غير مثبت — pip install google-genai")

# ── OpenAI (fallback اختياري) ──────────────────────────────────────────────────
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ── إعدادات الموديلات ──────────────────────────────────────────────────────────
#
# Groq models:
#   llama-3.3-70b-versatile   ← الأدق (افتراضي)
#   llama-3.1-8b-instant      ← الأسرع
#
# Gemini models:
#   gemini-2.0-flash           ← الأسرع (افتراضي)
#   gemini-1.5-pro             ← الأدق
#
GROQ_MODEL   = os.environ.get("GROQ_MODEL",   "llama-3.3-70b-versatile")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ── Cache & Retry ──────────────────────────────────────────────────────────────
_CACHE: dict = {}
CACHE_TTL_SECONDS = int(os.environ.get("AI_CACHE_TTL",        3600))
MAX_RETRIES       = int(os.environ.get("AI_MAX_RETRIES",       3))
RETRY_BASE_DELAY  = float(os.environ.get("AI_RETRY_BASE_DELAY", 1.5))


# ══════════════════════════════════════════════════════════════════════════════
# Key Management
# ══════════════════════════════════════════════════════════════════════════════

def _get_keys(env_var: str) -> list[str]:
    """بيجيب الـ API keys من .env (مفصولة بفاصلة)."""
    raw = os.environ.get(env_var, "")
    return [k.strip() for k in raw.split(",") if k.strip()]

def get_groq_keys()   -> list[str]: return _get_keys("GROQ_API_KEY")
def get_gemini_keys() -> list[str]: return _get_keys("GEMINI_API_KEY")
def get_openai_keys() -> list[str]: return _get_keys("OPENAI_API_KEY")


def get_ai_provider() -> str | None:
    """
    بيرجع اسم الـ provider المتاح للـ metadata.
    بيتستخدم في admin/book.py عشان يعرض رسالة خطأ لو مفيش key.
    """
    if HAS_GEMINI and get_gemini_keys():
        return f"Gemini ({GEMINI_MODEL})"
    if HAS_OPENAI and get_openai_keys():
        return "OpenAI"
    if HAS_GROQ and get_groq_keys():
        return f"Groq ({GROQ_MODEL})"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Low-level Callers
# ══════════════════════════════════════════════════════════════════════════════

def call_groq(prompt: str, api_key: str, max_tokens: int = 2000) -> str:
    """
    يستدعي Groq API (Llama 3).
    مخصص للبحث والجلب — بيستخدمه call_groq_search() مباشرة.
    """
    client = Groq(
        api_key=api_key,
        timeout=float(os.environ.get("GROQ_TIMEOUT", 30)),
    )
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert Islamic librarian. "
                    "Always respond in valid JSON format with no markdown and no extra text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content.strip()


def call_gemini(prompt: str, api_key: str, model_name: str = None) -> str:
    """
    يستدعي Gemini API.
    مخصص لتوليد الـ metadata — بيستخدمه call_ai() مباشرة.
    """
    selected_model = model_name or GEMINI_MODEL
    client   = google_genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model    = selected_model,
        contents = prompt,
    )
    return response.text.strip()


def call_openai(prompt: str, api_key: str, max_tokens: int = 2000) -> str:
    """
    يستدعي OpenAI GPT — Fallback لو Gemini فشل.
    """
    client = openai.OpenAI(
        api_key = api_key,
        timeout = float(os.environ.get("OPENAI_TIMEOUT", 30)),
    )
    response = client.chat.completions.create(
        model    = os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert Islamic scholar and librarian. "
                    "Always respond in valid JSON with no markdown or extra text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens      = max_tokens,
        temperature     = 0.3,
        response_format = {"type": "json_object"},
    )
    return response.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════════════════════════
# Retry + Key-Rotation Helper
# ══════════════════════════════════════════════════════════════════════════════

def _is_quota_error(exc: Exception) -> bool:
    """
    Returns True if the exception is a quota/rate-limit error (429 / RESOURCE_EXHAUSTED / 503).
    """
    msg = str(exc).upper()
    return any(kw in msg for kw in (
        "429", "RESOURCE_EXHAUSTED", "QUOTA", "RATE_LIMIT", "503", "UNAVAILABLE"
    ))


def _get_retry_delay(exc: Exception) -> float:
    """
    Extracts the retry delay from the API error response or defaults to 25 seconds.
    """
    default_delay = 25.0
    try:
        # Check if the exception has a response object with headers (e.g., Google APIError)
        if hasattr(exc, 'response') and exc.response:
            headers = getattr(exc.response, 'headers', {})
            for k, v in headers.items():
                if k.lower() == 'retry-after':
                    return max(float(v), default_delay)
                    
        # Parse retry delay from the exception message
        msg = str(exc)
        match = re.search(r'retry\s+after\s+(\d+(?:\.\d+)?)\s*s', msg, re.IGNORECASE)
        if match:
            return max(float(match.group(1)), default_delay)
            
        match2 = re.search(r'in\s+(\d+(?:\.\d+)?)\s*seconds', msg, re.IGNORECASE)
        if match2:
            return max(float(match2.group(1)), default_delay)
    except Exception:
        pass
    return default_delay


def _call_with_retry(caller, keys: list[str], prompt: str, label: str) -> str | None:
    """
    بيجرب كل key مع retry وexponential backoff وfallback models.
    لو الخطأ 429/503، بيقوم بالنوم فترة أمان (cooldown) بدلاً من الانتقال الفوري أو التكرار السريع.
    """
    is_gemini = (label == "Gemini")
    
    for i, key in enumerate(keys, start=1):
        for attempt in range(1, MAX_RETRIES + 1):
            if is_gemini:
                # Attempt 1 and 2: primary model (gemini-2.5-flash)
                # Attempt 3+: fallback model (gemini-1.5-flash)
                if attempt <= 2:
                    model_name = GEMINI_MODEL
                else:
                    model_name = "gemini-1.5-flash"
                logger.info("Gemini key #%d — attempt %d/%d using model %s", i, attempt, MAX_RETRIES, model_name)
            else:
                logger.info("%s key #%d — attempt %d/%d", label, i, attempt, MAX_RETRIES)
                
            try:
                if is_gemini:
                    return caller(prompt, key, model_name=model_name)
                else:
                    return caller(prompt, key)
            except Exception as exc:
                logger.warning("%s key #%d attempt %d فشل: %s", label, i, attempt, exc)
                
                # Check for rate-limit (429) or temporary server unavailability (503)
                if _is_quota_error(exc):
                    delay = _get_retry_delay(exc)
                    logger.warning("Gemini key #%d waiting %d seconds before retrying...", i, int(delay))
                    time.sleep(delay)
                    # For 429/503, continue retry on the same key rather than skipping immediately.
                else:
                    # Other transient errors: exponential backoff
                    if attempt < MAX_RETRIES:
                        delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                        logger.info("Retry في %.1f ثانية...", delay)
                        time.sleep(delay)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# call_ai — للـ Metadata (Gemini → OpenAI → Groq)
# ══════════════════════════════════════════════════════════════════════════════

def call_ai(prompt: str, target_lang_code: str = None) -> str:
    """
    الـ function الرئيسية لتوليد الـ metadata والترجمات.
    تدعم التوجيه الذكي للموديلات (Smart Model Routing) بناءً على تعقيد اللغة.
    """
    cache_key = hashlib.md5((prompt + ":" + str(target_lang_code)).encode()).hexdigest()
    if cache_key in _CACHE:
        ts, result = _CACHE[cache_key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            logger.debug("Cache hit — hash: %s", cache_key)
            return result

    result = None

    # 1. تحديد التوجيه الذكي بناءً على رمز اللغة
    if target_lang_code:
        lang_code = target_lang_code.lower().strip()
        # قائمة اللغات الكبرى والمتوسطة
        major_medium_langs = {
            'en', 'fr', 'es', 'de', 'it', 'pt', 'ru', 'tr', 'fa', 'zh', 'ar', 'hi', 'id'
        }

        if lang_code in major_medium_langs:
            logger.info("Routing translation to Llama for language: %s", lang_code)
            # أولاً: استخدام Groq (Llama)
            if HAS_GROQ:
                keys = get_groq_keys()
                if keys:
                    result = _call_with_retry(call_groq, keys, prompt, "Groq")

            # ثانياً (fallback): استخدام Gemini
            if result is None and HAS_GEMINI:
                logger.info("Llama failed or unavailable for %s, falling back to Gemini", lang_code)
                keys = get_gemini_keys()
                if keys:
                    result = _call_with_retry(call_gemini, keys, prompt, "Gemini")
        else:
            logger.info("Routing translation to Gemini for language: %s", lang_code)
            # أولاً: استخدام Gemini للغات النادرة/المحلية
            if HAS_GEMINI:
                keys = get_gemini_keys()
                if keys:
                    result = _call_with_retry(call_gemini, keys, prompt, "Gemini")

            # ثانياً (fallback): استخدام OpenAI أو Groq
            if result is None and HAS_OPENAI:
                logger.info("Gemini failed or unavailable for %s, falling back to OpenAI", lang_code)
                keys = get_openai_keys()
                if keys:
                    result = _call_with_retry(call_openai, keys, prompt, "OpenAI")
            if result is None and HAS_GROQ:
                logger.info("Gemini/OpenAI failed or unavailable for %s, falling back to Groq", lang_code)
                keys = get_groq_keys()
                if keys:
                    result = _call_with_retry(call_groq, keys, prompt, "Groq")
    else:
        # التوجيه الافتراضي (خارج سياق الترجمة): Gemini -> OpenAI -> Groq
        # 1. Gemini (الأساسي)
        if HAS_GEMINI:
            keys = get_gemini_keys()
            if keys:
                result = _call_with_retry(call_gemini, keys, prompt, "Gemini")

        # 2. OpenAI (fallback)
        if result is None and HAS_OPENAI:
            keys = get_openai_keys()
            if keys:
                result = _call_with_retry(call_openai, keys, prompt, "OpenAI")

        # 3. Groq (آخر خيار)
        if result is None and HAS_GROQ:
            keys = get_groq_keys()
            if keys:
                result = _call_with_retry(call_groq, keys, prompt, "Groq")

    if result is None:
        raise ValueError(
            "كل الـ AI providers فشلوا أو مش مضبوطين.\n"
            "تحقق من المفاتيح في ملف .env"
        )

    _CACHE[cache_key] = (time.time(), result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# call_groq_search — للبحث والجلب فقط (Groq)
# ══════════════════════════════════════════════════════════════════════════════

def call_groq_search(prompt: str) -> str:
    """
    مخصص للبحث والجلب في crawler.py فقط.
    بيستخدم Groq (Llama 3) مباشرة — بدون fallback لـ Gemini.

    الاستخدام في crawler.py:
        from books.services.ai import call_groq_search, parse_json_response
        raw   = call_groq_search(my_prompt)
        books = parse_json_response(raw)
    """
    if not HAS_GROQ:
        raise ValueError("مكتبة Groq غير مثبتة — pip install groq")

    keys = get_groq_keys()
    if not keys:
        raise ValueError(
            "GROQ_API_KEY غير موجود في .env\n"
            "احصل على مفتاح مجاني من: https://console.groq.com"
        )

    cache_key = hashlib.md5(("groq_search:" + prompt).encode()).hexdigest()
    if cache_key in _CACHE:
        ts, result = _CACHE[cache_key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            logger.debug("Groq Search Cache hit")
            return result

    result = _call_with_retry(call_groq, keys, prompt, "Groq-Search")
    if result is None:
        raise ValueError(
            f"كل الـ Groq keys فشلت ({len(keys)} key). "
            "تحقق من GROQ_API_KEY في .env"
        )

    _CACHE[cache_key] = (time.time(), result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# JSON Parser
# ══════════════════════════════════════════════════════════════════════════════

def parse_json_response(text: str) -> dict:
    """بيحلل JSON من response الـ AI بشكل مرن."""
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$",          "", text, flags=re.MULTILINE)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"مش قادر يحلل الـ response كـ JSON.\nأول 300 حرف: {text[:300]}")


# ══════════════════════════════════════════════════════════════════════════════
# Auto-extract Author & Year
# ══════════════════════════════════════════════════════════════════════════════

def extract_book_metadata(
    text_content: str,
    title: str = "",
    current_author: str = "",
    current_year: Optional[str] = None,
) -> dict:
    """
    لو المؤلف أو السنة مجهولين، يسأل Gemini يستخرجهم من نص الكتاب.
    """
    need_author = not current_author or current_author.strip().lower() in (
        "", "unknown", "غير معروف", "majhul",
    )
    need_year = current_year is None or str(current_year).strip() in ("", "0", "unknown")

    if not need_author and not need_year:
        return {
            "author":           current_author,
            "publication_year": current_year,
            "confidence":       "high",
            "notes":            "Provided by caller, no extraction needed.",
        }

    sample         = text_content[:3000] if text_content else ""
    missing_fields = []
    if need_author: missing_fields.append("author name")
    if need_year:   missing_fields.append("publication year (Hijri or Gregorian)")

    prompt = f"""You are a specialist in Islamic manuscripts and published books.

Analyse the following text sample and extract the missing bibliographic information.

Book context:
- Title: {title or "Unknown"}
- Known author: {current_author or "Not provided"}
- Known year: {current_year or "Not provided"}

Text sample:
\"\"\"{sample}\"\"\"

Extract: {", ".join(missing_fields)}

Guidelines:
- For author: look for "تأليف", "by", "المؤلف", "Author:", colophon, or title-page text.
- For year: look for Hijri (هـ/AH) or Gregorian (م/CE/AD) years.
- If not determinable, set to null.
- Confidence: "high"=explicit, "medium"=inferred, "low"=guessed.

Respond in JSON only:
{{
  "author": "string or null",
  "publication_year": "string or null",
  "confidence": "high|medium|low",
  "notes": "brief explanation"
}}"""

    raw       = call_ai(prompt)   # ← Gemini
    result    = parse_json_response(raw)
    extracted = {
        "author":           result.get("author")           or current_author or None,
        "publication_year": result.get("publication_year") or current_year   or None,
        "confidence":       result.get("confidence", "low"),
        "notes":            result.get("notes", ""),
    }

    logger.info(
        "Metadata extraction — author: %s | year: %s | confidence: %s",
        extracted["author"], extracted["publication_year"], extracted["confidence"],
    )
    return extracted


# ══════════════════════════════════════════════════════════════════════════════
# Language Guidelines
# ══════════════════════════════════════════════════════════════════════════════

LANGUAGE_GUIDELINES = {
    "ha": {
        "language_name":           "Hausa",
        "description_prompt":      "Write a detailed description for this Islamic book in Hausa language.",
        "description_requirement": (
            "A 3-5 sentence description in Hausa language about this book, "
            "its importance, and what readers will learn."
        ),
        "chapters_instruction":    'Generate 5-15 realistic chapter titles in Hausa. Use "Babi".',
        "chapter_example":         "Babi na 1: ...",
        "tags_prompt":             "Generate 8-15 SEO tags mixing Hausa, Arabic transliteration, and English.",
        "seo_title_note":          "SEO title in Hausa (max 60 chars)",
        "seo_description_note":    "Meta description in Hausa (max 155 chars)",
        "slug_note":               "Lowercase Hausa slug with hyphens only",
    },
    "ar": {
        "language_name":           "Arabic",
        "description_prompt":      "اكتب وصفًا تفصيليًا لهذا الكتاب الإسلامي باللغة العربية.",
        "description_requirement": "وصف من 3 إلى 5 جمل باللغة العربية يوضح أهمية الكتاب.",
        "chapters_instruction":    "أنشئ فهرسًا يضم 5-15 عنوان فصل باللغة العربية.",
        "chapter_example":         "الفصل الأول: ...",
        "tags_prompt":             "أنشئ 8-15 وسمًا لمحركات البحث باللغة العربية.",
        "seo_title_note":          "عنوان SEO بالعربية (حد أقصى 60 حرفًا)",
        "seo_description_note":    "وصف ميتا بالعربية (حد أقصى 155 حرفًا)",
        "slug_note":               "مسار URL بحروف لاتينية مفصولة بشرطات",
    },
    "en": {
        "language_name":           "English",
        "description_prompt":      "Write a detailed description for this Islamic book in English.",
        "description_requirement": "A 3-5 sentence description in English about the book and its benefits.",
        "chapters_instruction":    "Generate 5-15 realistic chapter titles in English.",
        "chapter_example":         "Chapter 1: ...",
        "tags_prompt":             "Generate 8-15 SEO keywords in English.",
        "seo_title_note":          "SEO title in English (max 60 chars)",
        "seo_description_note":    "Meta description in English (max 155 chars)",
        "slug_note":               "URL-friendly slug using lowercase and hyphens",
    },
    "sw": {
        "language_name":           "Swahili",
        "description_prompt":      "Write a detailed description for this Islamic book in Swahili.",
        "description_requirement": "A 3-5 sentence description in Swahili about this book.",
        "chapters_instruction":    'Generate 5-15 chapter titles in Swahili. Use "Sura".',
        "chapter_example":         "Sura ya 1: ...",
        "tags_prompt":             "Generate 8-15 SEO tags in Swahili.",
        "seo_title_note":          "SEO title in Swahili (max 60 chars)",
        "seo_description_note":    "Meta description in Swahili (max 155 chars)",
        "slug_note":               "Lowercase Swahili slug with hyphens only",
    },
    "am": {
        "language_name":           "Amharic",
        "description_prompt":      "Write a detailed description for this Islamic book in Amharic.",
        "description_requirement": "A 3-5 sentence description in Amharic about this book.",
        "chapters_instruction":    'Generate 5-15 chapter titles in Amharic. Use "ምዕራፍ".',
        "chapter_example":         "ምዕራፍ 1: ...",
        "tags_prompt":             "Generate 8-15 SEO tags in Amharic.",
        "seo_title_note":          "SEO title in Amharic (max 60 chars)",
        "seo_description_note":    "Meta description in Amharic (max 155 chars)",
        "slug_note":               "Transliterated Amharic slug using lowercase Latin and hyphens",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# Individual Generators (Backward Compatibility — كلهم بيستخدموا Gemini)
# ══════════════════════════════════════════════════════════════════════════════

def generate_book_description(
    title: str, title_hausa: str, author: str,
    category: str, language_code: str = "ha", text_sample: str = "",
) -> str:
    g = LANGUAGE_GUIDELINES.get(language_code, LANGUAGE_GUIDELINES["ha"])
    prompt = f"""{g['description_prompt']}

Book Title: {title}
Author: {author}
Category: {category}
{"Sample text: " + text_sample[:1500] if text_sample else ""}

Respond in JSON: {{"description": "{g['description_requirement']}"}}"""
    return parse_json_response(call_ai(prompt)).get("description", "")


def generate_table_of_contents(
    title: str, title_hausa: str, author: str,
    language_code: str = "ha", text_content: str = "",
) -> list:
    g = LANGUAGE_GUIDELINES.get(language_code, LANGUAGE_GUIDELINES["ha"])
    prompt = f"""{g['chapters_instruction']}

Book Title: {title}
Author: {author}

Respond in JSON: {{"chapters": ["{g['chapter_example']}", "..."]}}"""
    return parse_json_response(call_ai(prompt)).get("chapters", [])


def generate_tags(
    title: str, title_hausa: str, author: str,
    description: str = "", category: str = "", language_code: str = "ha",
) -> list:
    g = LANGUAGE_GUIDELINES.get(language_code, LANGUAGE_GUIDELINES["ha"])
    prompt = f"""{g['tags_prompt']}

Book Title: {title} (Hausa: {title_hausa})
Author: {author}
Category: {category}
Description: {description[:500] or "N/A"}

Respond in JSON: {{"tags": ["keyword1", "keyword2", ...]}}"""
    return parse_json_response(call_ai(prompt)).get("tags", [])


def generate_seo(
    title: str, title_hausa: str,
    description: str = "", language_code: str = "ha",
) -> dict:
    g = LANGUAGE_GUIDELINES.get(language_code, LANGUAGE_GUIDELINES["ha"])
    prompt = f"""Generate SEO metadata in {g['language_name']}.

Book Title: {title} (Hausa: {title_hausa})
Description: {description[:500] or "N/A"}

Respond in JSON:
{{
    "seo_title": "{g['seo_title_note']}",
    "seo_description": "{g['seo_description_note']}",
    "seo_slug": "{g['slug_note']}"
}}"""
    return parse_json_response(call_ai(prompt))


# ══════════════════════════════════════════════════════════════════════════════
# Main Combined Generator (Gemini)
# ══════════════════════════════════════════════════════════════════════════════

def generate_all(
    title: str, title_hausa: str, author: str,
    category: str = "", language_code: str = "ha",
    text_content: str = "", publication_year: Optional[str] = None,
) -> dict:
    """
    يولد كل الـ metadata في call واحد — بيستخدم Gemini.
    الـ flow:
      1. يستخرج المؤلف/السنة لو مجهولين (Gemini)
      2. يولد description, chapters, tags, SEO (Gemini)
      3. يرجع dict كامل جاهز للحفظ في Book model
    """
    g = LANGUAGE_GUIDELINES.get(language_code, LANGUAGE_GUIDELINES["ha"])

    extracted       = extract_book_metadata(text_content, title, author, publication_year)
    resolved_author = extracted["author"] or author or "Unknown"
    resolved_year   = extracted["publication_year"] or publication_year
    year_line       = f"- Publication Year: {resolved_year}" if resolved_year else ""

    prompt = f"""You are a professional SEO expert specialising in digital Islamic libraries.

## Book Information
- Original Title: {title} (Hausa Title: {title_hausa})
- Author: {resolved_author}
- Category: {category}
{year_line}
- Target Language: {g['language_name']}
{"- Sample text: " + text_content[:2000] if text_content else ""}

## Instructions
### Description
{g['description_prompt']}
Requirements: {g['description_requirement']}

### Chapters
{g['chapters_instruction']}
Format: {g['chapter_example']}

### Tags
{g['tags_prompt']}

### SEO
- seo_title: {g['seo_title_note']}
- seo_description: {g['seo_description_note']}
- slug: {g['slug_note']}

## Output — Return ONLY valid JSON:
{{
  "seo_title": "String",
  "seo_description": "String",
  "slug": "String",
  "description": "String",
  "tags": ["String", ...],
  "chapters": ["String", ...]
}}

Rules:
- Output language must be {g['language_name']} only.
- slug: lowercase Latin, hyphens, no spaces.
- seo_title: under 60 chars.
- seo_description: 140-160 chars.
- No markdown, no extra keys."""

    metadata = parse_json_response(call_ai(prompt))   # ← Gemini

    metadata["author"]                = resolved_author
    metadata["publication_year"]      = resolved_year
    metadata["extraction_confidence"] = extracted["confidence"]
    metadata["extraction_notes"]      = extracted["notes"]
    return metadata


# ══════════════════════════════════════════════════════════════════════════════
# PDF Text Extraction
# ══════════════════════════════════════════════════════════════════════════════

def extract_text_from_pdf(file_path: str, max_pages: int = 10) -> str:
    try:
        import fitz
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc[:max_pages]:
                text += page.get_text()
        return text
    except ImportError:
        pass
    except Exception as exc:
        logger.error("PyMuPDF error: %s", exc)

    try:
        import PyPDF2
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:max_pages]:
                text += page.extract_text() or ""
        return text
    except ImportError:
        logger.warning("مفيش مكتبة PDF — pip install pymupdf")
    except Exception as exc:
        logger.error("PyPDF2 error: %s", exc)
    return ""
