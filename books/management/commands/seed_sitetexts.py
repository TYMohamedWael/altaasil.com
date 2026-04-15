from django.core.management.base import BaseCommand
from books.models import SiteText, Language

SITE_TEXT_DEFAULTS = [
    # Base layout & meta
    {"key": "meta_title_default", "content": "Littattafan Hausa - Dakin Karatu na Ilimi na Musulunci", "description": "Default <title> tag for pages."},
    {"key": "meta_description_default", "content": "Manhajar littattafan Musulunci na Hausa.", "description": "Default meta description."},
    {"key": "meta_og_title", "content": "Littattafan Hausa", "description": "Default OpenGraph title."},
    {"key": "meta_og_description", "content": "Dakin Karatu na Ilimi na Musulunci", "description": "Default OpenGraph description."},
    {"key": "header_logo_title", "content": "Littattafan Hausa", "description": "Main logo text."},
    {"key": "header_logo_subtitle", "content": "DAKIN KARATU NA ILIMI", "description": "Logo subtitle."},
    {"key": "search_placeholder_desktop", "content": "Nemo littafi, marubuci, ko maudu'i...", "description": "Desktop search placeholder."},
    {"key": "search_placeholder_mobile", "content": "Nemo littafi...", "description": "Mobile search placeholder."},
    {"key": "notif_button_title", "content": "Sanarwa", "description": "Notifications button tooltip."},
    {"key": "notif_dropdown_title", "content": "Sanarwa", "description": "Notifications dropdown heading."},
    {"key": "notif_dropdown_view_all", "content": "Duba duka", "description": "View all notifications link."},
    {"key": "notif_loading", "content": "Ana loda...", "description": "Notification list loading state."},
    {"key": "notif_empty", "content": "Babu sanarwa", "description": "Notifications empty message."},
    {"key": "notif_error", "content": "Ba a iya loda sanarwa", "description": "Notifications error message."},
    {"key": "nav_link_home", "content": "Gida", "description": "Navigation link"},
    {"key": "nav_link_books", "content": "Littattafai", "description": "Navigation link"},
    {"key": "nav_link_categories", "content": "Rukunoni", "description": "Navigation link"},
    {"key": "nav_link_profile", "content": "Ni", "description": "Navigation profile link"},
    {"key": "nav_link_login", "content": "Shiga", "description": "Navigation login"},
    {"key": "nav_link_register", "content": "Yi Rajista", "description": "Navigation register"},
    {"key": "nav_link_logout", "content": "Fita", "description": "Navigation logout"},
    {"key": "nav_link_notifications", "content": "Sanarwa", "description": "Navigation notifications"},
    {"key": "footer_brand_title", "content": "Littattafan Hausa", "description": "Footer brand heading"},
    {"key": "footer_brand_subtitle", "content": "Dakin Karatu na Ilimi na Musulunci", "description": "Footer brand subheading"},
    {"key": "footer_brand_description", "content": "Manhajar littattafan Musulunci ta harshen Hausa. Muna tattara, fassara, da yada ilimin Musulunci cikin harshen Hausa zuwa duniya baki daya.", "description": "Footer brand description"},
    {"key": "footer_links_heading", "content": "Hanyoyi", "description": "Footer links heading"},
    {"key": "footer_link_books", "content": "Littattafai", "description": "Footer link"},
    {"key": "footer_link_categories", "content": "Rukunoni", "description": "Footer link"},
    {"key": "footer_link_about", "content": "Game da mu", "description": "Footer link"},
    {"key": "footer_categories_heading", "content": "Rukunoni", "description": "Footer categories heading"},
    {"key": "footer_category_aqeedah", "content": "Akida", "description": "Footer quick category"},
    {"key": "footer_category_fiqh", "content": "Fikhu", "description": "Footer quick category"},
    {"key": "footer_category_hadith", "content": "Hadisi", "description": "Footer quick category"},
    {"key": "footer_category_tafsir", "content": "Tafsiri", "description": "Footer quick category"},
    {"key": "footer_copyright", "content": "© 2026 Littattafan Hausa. Duk haƙƙoƙin an kiyaye su.", "description": "Footer copyright"},
    {"key": "footer_made_with_love", "content": "An gina da ❤️ don al'ummar Hausa", "description": "Footer love note"},
    # Home hero & CTA
    {"key": "home_hero_badge", "content": "Littattafai 1,780+ na Musulunci", "description": "Hero badge"},
    {"key": "home_hero_title_line1", "content": "Dakin Karatu na Ilimi", "description": "Hero title"},
    {"key": "home_hero_title_line2", "content": "na Musulunci", "description": "Hero title"},
    {"key": "home_hero_description", "content": "Mafi girman tarin littattafan Musulunci a cikin harshen Hausa. An tattara, an fassara, kuma an shirya su ta hanyar fasaha ta zamani.", "description": "Hero description"},
    {"key": "home_hero_cta_primary", "content": "Bincika Littattafai", "description": "Hero CTA"},
    {"key": "home_hero_cta_secondary", "content": "Nemo Maudu'i", "description": "Hero CTA"},
    {"key": "home_stats_books_label", "content": "Littattafai", "description": "Stats label"},
    {"key": "home_stats_authors_label", "content": "Marubuta", "description": "Stats label"},
    {"key": "home_stats_languages_label", "content": "Harsuna", "description": "Stats label"},
    {"key": "home_stats_readers_label", "content": "Masu Karatu", "description": "Stats label"},
    {"key": "home_categories_heading", "content": "Rukunoni", "description": "Categories heading"},
    {"key": "home_categories_subheading", "content": "Zaɓi rukunin da kake so", "description": "Categories subheading"},
    {"key": "home_categories_view_all", "content": "Duba duka", "description": "Categories link"},
    {"key": "home_categories_count", "content": "{count} littattafai", "description": "Categories count label"},
    {"key": "home_latest_heading", "content": "Sababbin Littattafai", "description": "Latest heading"},
    {"key": "home_latest_subheading", "content": "An ƙara su kwanan nan", "description": "Latest subheading"},
    {"key": "home_latest_view_all", "content": "Duba duka", "description": "Latest view all"},
    {"key": "home_latest_empty", "content": "Ba a sami littattafai ba tukuna. Ƙara littafi ta hanyar lohajar admin.", "description": "Latest empty message"},
    {"key": "home_cta_heading", "content": "Taimaka wajen yada ilimi", "description": "CTA heading"},
    {"key": "home_cta_description", "content": "Idan kana da littattafan Musulunci na Hausa, ka taimaka wajen ƙara su a cikin dakin karatu na mu.", "description": "CTA description"},
    # Book list
    {"key": "book_list_page_title", "content": "Littattafai - Littattafan Hausa", "description": "Book list <title>"},
    {"key": "book_list_intro_heading", "content": "Littattafai", "description": "Page heading"},
    {"key": "book_list_intro_subheading", "content": "Duk littattafan da ke cikin dakin karatu na mu", "description": "Subheading"},
    {"key": "book_list_sort_label", "content": "Tsara:", "description": "Sort label"},
    {"key": "book_list_sort_newest", "content": "Sabbin", "description": "Sort option"},
    {"key": "book_list_sort_most_viewed", "content": "Mafi kallo", "description": "Sort option"},
    {"key": "book_list_sort_highest_rated", "content": "Mafi ƙima", "description": "Sort option"},
    {"key": "book_list_sort_most_downloaded", "content": "Mafi saukewa", "description": "Sort option"},
    {"key": "book_list_language_label", "content": "Harshe:", "description": "Language filter label"},
    {"key": "book_list_language_all", "content": "Duka", "description": "Show all languages"},
    {"key": "book_list_sidebar_heading", "content": "Rukunoni", "description": "Sidebar heading"},
    {"key": "book_list_sidebar_all", "content": "Duka", "description": "Sidebar link"},
    {"key": "book_list_search_results", "content": 'Sakamakon bincike: "{query}"', "description": "Search results text"},
    {"key": "book_list_empty_list_view", "content": "Ba a sami littattafai ba.", "description": "List view empty message"},
    {"key": "book_list_empty_grid_view", "content": "Ba a sami littattafai ba.", "description": "Grid view empty message"},
    {"key": "book_list_load_more", "content": "Ƙara nuna", "description": "Load more button"},
    {"key": "book_list_pagination_prev", "content": "Baya", "description": "Pagination prev"},
    {"key": "book_list_pagination_next", "content": "Gaba", "description": "Pagination next"},
    # Book detail (sections used so far)
    {"key": "book_detail_page_title", "content": "{title} - Littattafan Hausa", "description": "Title format"},
    {"key": "book_detail_breadcrumb_home", "content": "Gida", "description": "Breadcrumb"},
    {"key": "book_detail_breadcrumb_books", "content": "Littattafai", "description": "Breadcrumb"},
    {"key": "book_detail_avg_rating_suffix", "content": "({count} bita'i)", "description": "Average rating suffix"},
    {"key": "book_detail_verified_badge", "content": "An tabbatar da wannan littafi ta hanyar ilimi", "description": "Verified badge"},
    {"key": "book_detail_read_now", "content": "Karanta Yanzu", "description": "Read button"},
    {"key": "book_detail_download_pdf", "content": "Sauke PDF", "description": "Download button"},
    {"key": "book_detail_no_pdf", "content": "PDF ba a samu ba tukuna", "description": "No PDF message"},
    {"key": "book_detail_add_to_list", "content": "Ƙara zuwa Jeri", "description": "Add to list button"},
    {"key": "book_detail_list_picker_title", "content": "Zaɓi jerin karatu", "description": "Reading list modal"},
    {"key": "book_detail_list_loading", "content": "Ana loda...", "description": "Reading list loading"},
    {"key": "book_detail_share_button", "content": "Raba", "description": "Share button"},
    {"key": "book_detail_stat_views", "content": "Kallon", "description": "Stats label"},
    {"key": "book_detail_stat_downloads", "content": "Saukewa", "description": "Stats label"},
    {"key": "book_detail_stat_favorites", "content": "Favorites", "description": "Stats label"},
    {"key": "book_detail_stat_reviews", "content": "Bita'i", "description": "Stats label"},
    {"key": "book_detail_description_heading", "content": "Bayani game da Littafi", "description": "Section heading"},
    {"key": "book_detail_toc_heading", "content": "Abubuwan da ke ciki", "description": "Section heading"},
    {"key": "book_detail_audio_heading", "content": "Saurara", "description": "Section heading"},
    {"key": "book_detail_language_unknown", "content": "Harshen da bai bayyana ba", "description": "Fallback language label"},
    {"key": "book_detail_sidebar_language_label", "content": "Harshe", "description": "Sidebar label"},
    {"key": "book_detail_audio_speed", "content": "Gudun sauti", "description": "Audio speed label"},
    {"key": "book_detail_tags_heading", "content": "Kalmomin Bincike", "description": "Tags heading"},
    {"key": "book_detail_reviews_heading", "content": "⭐ Bita'i da Ra'ayoyi", "description": "Reviews heading"},
    {"key": "book_detail_reviews_count", "content": "{count} bita'i", "description": "Reviews count label"},
    {"key": "book_detail_review_form_heading", "content": "Rubuta bita'i", "description": "Review form heading"},
    {"key": "book_detail_review_form_rating_label", "content": "Ƙima", "description": "Review form label"},
    {"key": "book_detail_review_form_title_placeholder", "content": "Taken bita'i", "description": "Placeholder"},
    {"key": "book_detail_review_form_content_placeholder", "content": "Rubuta ra'ayin ka...", "description": "Placeholder"},
    {"key": "book_detail_review_form_submit", "content": "Aika Bita'i", "description": "Submit label"},
    {"key": "book_detail_login", "content": "Shiga", "description": "Login label"},
    {"key": "book_detail_login_to_review", "content": "don rubuta bita'i", "description": "Login prompt"},
    {"key": "book_detail_time_ago", "content": "da suka wuce", "description": "Timesince suffix"},
    {"key": "book_detail_reviews_empty", "content": "Babu bita'i tukuna. Ka zama na farko!", "description": "Reviews empty message"},
    {"key": "book_detail_comments_heading", "content": "Tattaunawa", "description": "Comments heading"},
    {"key": "book_detail_comment_placeholder", "content": "Rubuta sharhi...", "description": "Comment placeholder"},
    {"key": "book_detail_comment_submit", "content": "Aika", "description": "Comment submit"},
    {"key": "book_detail_login_to_comment", "content": "don rubuta sharhi", "description": "Login prompt"},
    {"key": "book_detail_comment_reply", "content": "↩ Amsa", "description": "Reply button"},
    {"key": "book_detail_reply_placeholder", "content": "Rubuta amsa...", "description": "Reply placeholder"},
    {"key": "book_detail_comment_cancel", "content": "Soke", "description": "Cancel button"},
    {"key": "book_detail_comments_empty", "content": "Babu sharhi tukuna. Ka fara tattaunawa!", "description": "Comments empty"},
    {"key": "book_detail_sidebar_heading", "content": "Bayanan Littafi", "description": "Sidebar heading"},
    {"key": "book_detail_sidebar_category", "content": "Rukuni", "description": "Sidebar label"},
    {"key": "book_detail_sidebar_subcategory", "content": "Ƙaramin Rukuni", "description": "Sidebar label"},
    {"key": "book_detail_sidebar_year", "content": "Shekara", "description": "Sidebar label"},
    {"key": "book_detail_sidebar_status", "content": "Hali", "description": "Sidebar label"},
    {"key": "book_detail_pdf_available", "content": "PDF Akwai", "description": "Sidebar badge"},
    {"key": "book_detail_pdf_missing", "content": "Babu PDF", "description": "Sidebar badge"},
    {"key": "book_detail_related_heading", "content": "Littattafai masu alaƙa", "description": "Related section heading"},
]


class Command(BaseCommand):
    help = "Seed the SiteText table with default keys/content so they can be edited from the admin."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing entries with the defaults defined here."
        )

    def handle(self, *args, **options):
        overwrite = options["overwrite"]
        created = updated = skipped = 0

        language_cache = {}

        for row in SITE_TEXT_DEFAULTS:
            language = None
            lang_code = row.get("language")
            if lang_code:
                if lang_code not in language_cache:
                    language_cache[lang_code] = Language.objects.filter(code=lang_code).first()
                    if not language_cache[lang_code]:
                        self.stdout.write(self.style.WARNING(
                            f"Language '{lang_code}' not found; skipping key {row['key']}"
                        ))
                        continue
                language = language_cache[lang_code]

            defaults = {
                "content": row["content"],
                "description": row.get("description", "")
            }

            obj, was_created = SiteText.objects.get_or_create(
                key=row["key"],
                language=language,
                defaults=defaults
            )

            if was_created:
                created += 1
            else:
                if overwrite:
                    obj.content = row["content"]
                    obj.description = row.get("description", "")
                    obj.save(update_fields=["content", "description", "updated_at"])
                    updated += 1
                else:
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created}, Updated: {updated}, Skipped: {skipped}."
        ))
