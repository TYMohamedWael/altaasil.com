from django.core.management.base import BaseCommand
from books.models import Category


class Command(BaseCommand):
    help = 'Seed default categories'

    def handle(self, *args, **options):
        categories = [
            ('Aqeedah', 'Akida', 'العقيدة', 'aqeedah'),
            ('Fiqh', 'Fikhu', 'الفقه', 'fiqh'),
            ('Hadith', 'Hadisi', 'الحديث', 'hadith'),
            ('Tafsir', 'Tafsiri', 'التفسير', 'tafsir'),
            ('Seerah', 'Sira', 'السيرة', 'seerah'),
            ('Arabic Language', 'Harshen Larabci', 'اللغة العربية', 'arabic'),
            ('Tazkiyah', 'Tarbiyya', 'التزكية', 'tazkiyah'),
            ('Usul al-Fiqh', 'Usulul Fikhu', 'أصول الفقه', 'usul-al-fiqh'),
        ]
        for name, name_hausa, name_arabic, slug in categories:
            Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'name_hausa': name_hausa, 'name_arabic': name_arabic}
            )
        self.stdout.write(self.style.SUCCESS(f'Created {len(categories)} categories'))
