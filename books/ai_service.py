"""
AI Service for Littattafan Hausa
Supports: OpenAI (GPT-4o) and Google Gemini
Generates: Description, Table of Contents, Tags, SEO metadata
"""
import os
import json
import re
import logging

logger = logging.getLogger(__name__)

# Try importing AI libraries
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


def get_ai_provider():
    """Detect which AI provider is available"""
    if os.environ.get('OPENAI_API_KEY') and HAS_OPENAI:
        return 'openai'
    if os.environ.get('GEMINI_API_KEY') and HAS_GEMINI:
        return 'gemini'
    return None


def call_openai(prompt: str, max_tokens: int = 2000) -> str:
    client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    response = client.chat.completions.create(
        model=os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
        messages=[
            {"role": "system", "content": "You are an expert Islamic scholar and librarian who specializes in Hausa Islamic literature. Always respond in valid JSON format."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


#objects.get

def call_gemini(prompt: str) -> str:
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel(os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash'))
    response = model.generate_content(
        f"You are an expert Islamic scholar and librarian who specializes in Hausa Islamic literature. Always respond in valid JSON format.\n\n{prompt}"
    )
    return response.text.strip()


def call_ai(prompt: str) -> str:
    """Call whichever AI provider is available"""
    provider = get_ai_provider()
    if provider == 'openai':
        return call_openai(prompt)
    elif provider == 'gemini':
        return call_gemini(prompt)
    else:
        raise ValueError("No AI provider configured. Set OPENAI_API_KEY or GEMINI_API_KEY in .env")


def parse_json_response(text: str) -> dict:
    """Extract JSON from AI response (handles markdown code blocks)"""
    # Remove markdown code blocks if present
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse AI response as JSON: {text[:200]}")


# def generate_book_description(title: str, title_hausa: str, author: str, 
#                                 category: str, text_sample: str = "") -> str:
#     """Generate a book description in Hausa"""
#     prompt = f"""Write a detailed description for this Islamic book in Hausa language.


# Book Title (Arabic): {title}
# Book Title (Hausa): {title_hausa}
# Author: {author}
# Category: {category}
# {"Sample text from the book: " + text_sample[:1500] if text_sample else ""}

# Respond in JSON format:
# {{"description": "A 3-5 sentence description in Hausa language about this book, its importance, and what readers will learn."}}"""

#     result = parse_json_response(call_ai(prompt))
#     return result.get('description', '')


# def generate_table_of_contents(title: str, title_hausa: str, author: str,
#                                  text_content: str = "") -> list:
#     """Generate or extract table of contents"""
#     prompt = f"""{"Extract" if text_content else "Generate a realistic"} table of contents for this Islamic book.

# Book Title (Arabic): {title}
# Book Title (Hausa): {title_hausa}  
# Author: {author}
# {"Full text or sample: " + text_content[:3000] if text_content else ""}

# Respond in JSON format with chapter titles in Hausa:
# {{"chapters": ["Babi na 1: ...", "Babi na 2: ...", "Babi na 3: ..."]}}

# Generate 5-15 chapter titles that would be realistic for this type of book."""

#     result = parse_json_response(call_ai(prompt))
#     return result.get('chapters', [])

def generate_book_description(title: str, title_hausa: str, author: str, 
                               category: str, language_code: str = "ha", text_sample: str = "") -> str:
    """توليد وصف الكتاب بناءً على اللغة الممررة"""
    guidelines = LANGUAGE_GUIDELINES.get(language_code, LANGUAGE_GUIDELINES['ha'])
    
    prompt = f"""{guidelines['description_prompt']}

Book Title: {title}
Author: {author}
Category: {category}
Target Language: {guidelines['language_name']}
{"Sample text: " + text_sample[:1500] if text_sample else ""}

Respond in JSON format:
{{"description": "{guidelines['description_requirement']}"}}"""

    result = parse_json_response(call_ai(prompt))
    return result.get('description', '')

def generate_table_of_contents(title: str, title_hausa: str, author: str,
                                 language_code: str = "ha", text_content: str = "") -> list:
    """توليد الفهرس باللغة الصحيحة"""
    guidelines = LANGUAGE_GUIDELINES.get(language_code, LANGUAGE_GUIDELINES['ha'])
    
    prompt = f"""{guidelines['chapters_instruction']}

Book Title: {title}
Author: {author}
Target Language: {guidelines['language_name']}

Respond in JSON format with chapters in {guidelines['language_name']}:
{{"chapters": ["{guidelines['chapter_example']}", "..."]}}"""

    result = parse_json_response(call_ai(prompt))
    return result.get('chapters', [])




def generate_tags(title: str, title_hausa: str, author: str,
                   description: str = "", category: str = "") -> list:
    """Generate SEO tags/keywords"""
    prompt = f"""Generate search keywords/tags for this Islamic book. Mix Hausa and Arabic terms.

Book Title (Arabic): {title}
Book Title (Hausa): {title_hausa}
Author: {author}
Category: {category}
Description: {description[:500] if description else "N/A"}

Respond in JSON format:
{{"tags": ["keyword1", "keyword2", "keyword3", ...]}}

Generate 8-15 relevant tags for SEO. Include terms in Hausa, Arabic transliteration, and English."""

    result = parse_json_response(call_ai(prompt))
    return result.get('tags', [])


def generate_seo(title: str, title_hausa: str, description: str = "") -> dict:
    """Generate SEO title, description, and slug"""
    prompt = f"""Generate SEO metadata for this Islamic book page.

Book Title (Arabic): {title}
Book Title (Hausa): {title_hausa}
Description: {description[:500] if description else "N/A"}

Respond in JSON format:
{{
    "seo_title": "An optimized page title (max 60 chars) in Hausa",
    "seo_description": "A meta description (max 155 chars) in Hausa for Google",
    "seo_slug": "url-friendly-slug-in-hausa"
}}"""

    return parse_json_response(call_ai(prompt))


LANGUAGE_GUIDELINES = {
    'ha': {
        'language_name': 'Hausa',
        'description_prompt': 'Write a detailed description for this Islamic book in Hausa language.',
        'description_requirement': 'A 3-5 sentence description in Hausa language about this book, its importance, and what readers will learn.',
        'chapters_instruction': 'Generate 5-15 realistic chapter titles in Hausa language. Use the prefix "Babi".',
        'chapter_example': 'Babi na 1: ...',
        'tags_prompt': 'Generate 8-15 SEO tags mixing Hausa, Arabic transliteration, and English terms.',
        'seo_title_note': 'SEO title in Hausa (max 60 chars)',
        'seo_description_note': 'Meta description in Hausa (max 155 chars)',
        'slug_note': 'Lowercase Hausa slug with hyphens only',
    },
    'ar': {
        'language_name': 'Arabic',
        'description_prompt': 'اكتب وصفًا تفصيليًا لهذا الكتاب الإسلامي باللغة العربية وبأسلوب جذاب.',
        'description_requirement': 'وصف من 3 إلى 5 جمل باللغة العربية يوضح أهمية الكتاب والفوائد التي سيحصل عليها القارئ.',
        'chapters_instruction': 'أنشئ فهرسًا يضم 5-15 عنوان فصل واقعي باللغة العربية. استخدم كلمة "الفصل" أو "الباب" في بداية كل عنوان.',
        'chapter_example': 'الفصل الأول: ...',
        'tags_prompt': 'أنشئ 8-15 وسمًا لمحركات البحث باللغة العربية ويمكن إضافة transliteration عند الحاجة.',
        'seo_title_note': 'عنوان SEO بالعربية (حد أقصى 60 حرفًا)',
        'seo_description_note': 'وصف ميتا بالعربية (حد أقصى 155 حرفًا)',
        'slug_note': 'مسار URL باللغة العربية مكتوبًا بحروف لاتينية مفصولة بشرطات',
    },
    'en': {
        'language_name': 'English',
        'description_prompt': 'Write a detailed description for this Islamic book in English.',
        'description_requirement': 'A 3-5 sentence description in English about the book, its importance, and benefits.',
        'chapters_instruction': 'Generate 5-15 realistic chapter titles in English.',
        'chapter_example': 'Chapter 1: ...',
        'tags_prompt': 'Generate 8-15 SEO tags/keywords in English.',
        'seo_title_note': 'SEO title in English (max 60 chars)',
        'seo_description_note': 'Meta description in English (max 155 chars)',
        'slug_note': 'URL-friendly slug in English using lowercase and hyphens',
    },
    'sw': {
        'language_name': 'Swahili',
        'description_prompt': 'Write a detailed description for this Islamic book in Swahili language.',
        'description_requirement': 'A 3-5 sentence description in Swahili language about this book, its importance, and what readers will learn.',
        'chapters_instruction': 'Generate 5-15 realistic chapter titles in Swahili language. Use the prefix "Sura".',
        'chapter_example': 'Sura ya 1: ...',
        'tags_prompt': 'Generate 8-15 SEO tags in Swahili.',
        'seo_title_note': 'SEO title in Swahili (max 60 chars)',
        'seo_description_note': 'Meta description in Swahili (max 155 chars)',
        'slug_note': 'Lowercase Swahili slug with hyphens only',
    },
    'am': {
        'language_name': 'Amharic',
        'description_prompt': 'Write a detailed description for this Islamic book in Amharic language.',
        'description_requirement': 'A 3-5 sentence description in Amharic language about this book, its importance, and what readers will learn.',
        'chapters_instruction': 'Generate 5-15 realistic chapter titles in Amharic language. Use the prefix "ምዕራፍ" (Mi\'iraf).',
        'chapter_example': 'ምዕራፍ 1: ...',
        'tags_prompt': 'Generate 8-15 SEO tags in Amharic. Include some English or Latin transliterations if helpful.',
        'seo_title_note': 'SEO title in Amharic (max 60 chars)',
        'seo_description_note': 'Meta description in Amharic (max 155 chars)',
        'slug_note': 'Transliterated Amharic slug using lowercase Latin letters and hyphens',
    }
}

def generate_all(title: str, title_hausa: str, author: str,
                  category: str = "", language_code: str = "ha", text_content: str = "") -> dict:
    """Generate ALL metadata in a single AI call following strict JSON rules."""
    
    # Use Hausa as default if the language code is missing or unsupported
    guidelines = LANGUAGE_GUIDELINES.get(language_code, LANGUAGE_GUIDELINES['ha'])
    
    prompt = f"""You are a professional SEO expert and metadata writer specializing in digital libraries and Islamic books.

Your task is to generate precise, high-quality metadata for a book based on its original language, following the instructions below with strict accuracy.

---
## Book Information
- Original Book Title: {title} (Hausa Title: {title_hausa})
- Author: {author}
- Category: {category}
- Target Metadata Language: {guidelines['language_name']}
{"- Sample text: " + text_content[:2000] if text_content else ""}

---
## Content Generation Instructions
Based on the requested language, you MUST follow these instructions literally and precisely:

### 1. General Description
- Instruction: {guidelines['description_prompt']}
- Requirements: {guidelines['description_requirement']}

### 2. Book Chapters
- Instruction: {guidelines['chapters_instruction']}
- Format Example: {guidelines['chapter_example']}

### 3. Keywords / Tags
- Instruction: {guidelines['tags_prompt']}

### 4. SEO Settings
- SEO Title: {guidelines['seo_title_note']}
- SEO Meta Description: {guidelines['seo_description_note']}
- URL Slug: {guidelines['slug_note']}

---
## Output Format Rules
Your response MUST be a valid JSON object ONLY.

Do NOT include any introductory text, explanations, commentary, or closing remarks — output the JSON and nothing else.

The JSON must contain exactly these keys:

{{
  "seo_title": "String",
  "seo_description": "String",
  "slug": "String",
  "description": "String",
  "tags": ["String", "String", ...],
  "chapters": ["String", "String", ...]
}}

---
## Critical Rules
- Output language must match {guidelines['language_name']} exactly — do NOT mix languages.
- All field values must be written natively in {guidelines['language_name']}.
- The slug must be URL-safe: lowercase Latin characters, hyphens only, no spaces or special characters, even if the book title is in Arabic or another non-Latin language.
- SEO title must stay under 60 characters.
- SEO meta description must stay between 140–160 characters.
- Tags must be relevant, search-optimized, and reflect the book's subject, author, genre, and Islamic classification where applicable.
- Chapters must follow the exact format shown in {guidelines['chapter_example']}.
- Do not hallucinate or fabricate content — base all output strictly on the book title and provided instructions.
- Return ONLY the raw JSON. No markdown code blocks, no backticks, no extra keys."""

    return parse_json_response(call_ai(prompt))


def extract_text_from_pdf(file_path: str, max_pages: int = 10) -> str:
    """Extract text from uploaded PDF"""
    try:
        import PyPDF2
        text = ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages[:max_pages]):
                text += page.extract_text() or ""
        return text
    except ImportError:
        logger.warning("PyPDF2 not installed. pip install PyPDF2")
        return ""
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""
