"""
Attach downloaded PDF files to existing books or create new ones.
Usage: python manage.py attach_pdfs
"""
from django.core.management.base import BaseCommand
from books.models import Book, Category


class Command(BaseCommand):
    help = 'Attach PDF files to books in the database'

    def handle(self, *args, **options):
        # Map PDF files to existing books or create new entries
        pdf_mappings = [
            # Attach to existing seeded books
            {
                'seo_slug': 'rahiqul-makhtum',
                'file': 'books/files/rahiqul-makhtum-en.pdf',
            },
            {
                'seo_slug': 'tushe-uku-da-dalillansu',
                'file': 'books/files/taisir-al-wusul-hausa.pdf',
            },
            {
                'seo_slug': 'tafsirin-ibn-kathir',
                'file': 'books/files/tafsirin-ushurin-karshe.pdf',
            },

            # New books with PDFs
            {
                'seo_slug': 'bayanai-game-da-tsafi',
                'file': 'books/files/bayanai-game-da-tsafi.pdf',
                'create': {
                    'title': 'بيانات حول السحر والشعوذة',
                    'title_hausa': 'Bayanai Game da Tsafi, Bokanci da Maita',
                    'author': 'Engr. Baba Magaji',
                    'description': 'Wannan littafi yana bayyana game da tsafi, bokanci da maita a cikin Musulunci. Ya nuna haramcin wadannan abubuwa da dalilai daga Alkur\'ani da Sunnah, da kuma yadda za a kare kai daga sharrinsu.',
                    'table_of_contents': ['Gabatarwa', 'Ma\'anar Tsafi', 'Ma\'anar Bokanci', 'Ma\'anar Maita', 'Hukuncin Tsafi a Musulunci', 'Hukuncin Bokanci', 'Hukuncin Maita', 'Kariya daga Tsafi', 'Warkar da Tsafi', 'Azkar da Addu\'oi na Kariya'],
                    'tags': ['tsafi', 'bokanci', 'maita', 'sihiri', 'kariya', 'ruqya', 'haram'],
                    'language': 'ha',
                    'status': 'published',
                    'approved': True,
                    'seo_title': 'Bayanai Game da Tsafi, Bokanci da Maita - Hausa',
                    'seo_description': 'Bayyanin tsafi, bokanci da maita a Musulunci. Dalilai da hanyar kariya.',
                    'view_count': 116190,
                    'download_count': 45000,
                },
            },
            {
                'seo_slug': 'mutuwa-da-alamomin-tashin-duniya',
                'file': 'books/files/mutuwa-da-alamomin.pdf',
                'create': {
                    'title': 'الموت وعلامات الساعة',
                    'title_hausa': 'Mutuwa da Alamomin Tashin Duniya',
                    'author': 'Engr. Baba Magaji',
                    'description': 'Littafin da ke bayyana game da mutuwa, abin da ke faruwa a kabari, da alamomin tashin duniya karami da babba kamar yadda aka bayyana a cikin Alkur\'ani da Sunnah. Ya kunshi bayanai game da Dajjal, saukar Annabi Isa, fitowa ta Ya\'juj da Ma\'juj.',
                    'table_of_contents': ['Mutuwa da Sakamakon ta', 'Fitinar Kabari', 'Alamomin Tashin Duniya Kanana', 'Fitowa ta Dajjal', 'Saukar Annabi Isa (AS)', 'Ya\'juj da Ma\'juj', 'Tashin Rana', 'Alamomin Tashin Duniya Manya', 'Fitowar Dabbar Kasa', 'Tashin Rana da Hisabi'],
                    'tags': ['mutuwa', 'alamomi', 'tashin duniya', 'kiyama', 'dajjal', 'isa', 'kabari', 'akhira'],
                    'language': 'ha',
                    'status': 'published',
                    'approved': True,
                    'seo_title': 'Mutuwa da Alamomin Tashin Duniya - Hausa',
                    'seo_description': 'Bayyanin mutuwa da alamomin tashin duniya daga Alkur\'ani da Sunnah a harshen Hausa.',
                    'view_count': 23534,
                    'download_count': 8500,
                },
            },
            {
                'seo_slug': 'alkurani-mai-girma-hausa',
                'file': 'books/files/quran-hausa-translation.pdf',
                'create': {
                    'title': 'ترجمة معاني القرآن الكريم إلى الهوسا',
                    'title_hausa': 'Fassarar Ma\'anonin Alkur\'ani Mai Girma zuwa Hausa',
                    'author': 'لجنة مجمع الملك فهد',
                    'description': 'Fassarar ma\'anonin Alkur\'ani mai girma zuwa harshen Hausa. Wannan fassara ce ta ma\'anoni ba fassarar kalma-kalma ba. An buga ta a Madina Munawwara.',
                    'table_of_contents': ['Suratul Fatiha', 'Suratul Baqara', 'Suratu Ali Imran', 'Suratun Nisa\'i', 'Suratul Ma\'ida', 'Suratul An\'am', 'Suratul A\'raf', 'Suratul Anfal', 'Suratut Tawba', 'Suratu Yunus'],
                    'tags': ['alkurani', 'fassara', 'quran', 'hausa', 'translation', 'ma\'anoni'],
                    'language': 'ha',
                    'status': 'published',
                    'approved': True,
                    'seo_title': 'Fassarar Alkur\'ani zuwa Hausa - Ma\'anonin Alkur\'ani',
                    'seo_description': 'Fassarar ma\'anonin Alkur\'ani mai girma zuwa harshen Hausa daga Madina.',
                    'view_count': 28852,
                    'download_count': 12000,
                },
            },
            {
                'seo_slug': 'tafsirin-ushurin-karshe',
                'file': 'books/files/tafsirin-ushurin-karshe.pdf',
                'create': {
                    'title': 'تفسير الأجزاء العشرين الأخيرة من القرآن',
                    'title_hausa': 'Tafsirin Ushurin Karshe Na Alkur\'ani Mai Girma',
                    'author': 'tafseer.info',
                    'description': 'Tafsirin juz\'i ashirin na karshe na Alkur\'ani mai girma (daga Juz\' 21 zuwa Juz\' 30). Ya kunshi tafsiri mai sauki da fili da ya dace da kowa. An rubuta shi a harshen Hausa don amfanin al\'ummar Hausa.',
                    'table_of_contents': ['Juz\' na 21', 'Juz\' na 22', 'Juz\' na 23', 'Juz\' na 24', 'Juz\' na 25', 'Juz\' na 26', 'Juz\' na 27', 'Juz\' na 28', 'Juz\' na 29: Tabarak', 'Juz\' na 30: Amma'],
                    'tags': ['tafsiri', 'alkurani', 'ushurin karshe', 'juz amma', 'tabarak', 'quran'],
                    'language': 'ha',
                    'status': 'published',
                    'approved': True,
                    'seo_title': 'Tafsirin Ushurin Karshe Na Alkur\'ani - Hausa',
                    'seo_description': 'Tafsirin juz\'i 20 na karshe na Alkur\'ani a harshen Hausa mai sauki.',
                    'view_count': 11357,
                    'download_count': 4200,
                },
            },
            {
                'seo_slug': 'fan-altajweed',
                'file': 'books/files/fan-altajweed.pdf',
                'create': {
                    'title': 'فن التجويد',
                    'title_hausa': 'Fasahar Tajwidi - Yadda ake Karatun Alkur\'ani',
                    'author': 'عزة عبيد دعاس',
                    'description': 'Littafin da ke koyar da ka\'idojin tajwidi don karanta Alkur\'ani yadda ya kamata. Ya bayyana wuraren fitarwa na haruffa, siffofinsu, da hukunce-hukuncen karatun Alkur\'ani.',
                    'table_of_contents': ['Gabatarwa ga Tajwidi', 'Wuraren Fitarwa na Haruffa', 'Siffofin Haruffa', 'Hukunce-hukuncen Nun Sakinah da Tanwin', 'Hukunce-hukuncen Mim Sakinah', 'Idgham da Ikhfa', 'Madd: Mika Sauti', 'Waqf da Ibtida\'i'],
                    'tags': ['tajwidi', 'karatun alkurani', 'haruffa', 'quran', 'recitation', 'tilawa'],
                    'language': 'ar',
                    'status': 'published',
                    'approved': True,
                    'seo_title': 'Fasahar Tajwidi - Koyon Karatun Alkur\'ani',
                    'seo_description': 'Ka\'idojin tajwidi don karanta Alkur\'ani yadda ya kamata.',
                    'view_count': 3500,
                    'download_count': 1200,
                },
            },
            {
                'seo_slug': 'dabarun-nazarin-adabin-hausa',
                'file': 'books/files/dabarun-nazarin-adabin-hausa.pdf',
                'create': {
                    'title': 'أساليب دراسة الأدب الهوساوي',
                    'title_hausa': 'Dabarun Nazarin Adabin Hausa',
                    'author': 'Said Muhammad Gusau',
                    'description': 'Littafin bincike ne game da hanyoyin nazarin adabin Hausa. Ya tattauna kan adabin baka da rubutaccen adabi da yadda ake nazarinsu cikin tsari na ilimi.',
                    'table_of_contents': ['Gabatarwa', 'Ma\'anar Adabi', 'Adabin Baka na Hausa', 'Rubutaccen Adabi', 'Hanyoyin Nazari', 'Waqo\'in Hausa', 'Labarin Hausa', 'Kammalawa'],
                    'tags': ['adabi', 'hausa', 'nazari', 'bincike', 'literature', 'waka'],
                    'language': 'ha',
                    'status': 'published',
                    'approved': True,
                    'seo_title': 'Dabarun Nazarin Adabin Hausa',
                    'seo_description': 'Hanyoyin nazarin adabin Hausa: adabin baka da rubutaccen adabi.',
                    'view_count': 450,
                    'download_count': 120,
                },
            },
        ]

        attached = 0
        created = 0
        cat_tafsir = Category.objects.filter(slug='tafsir').first()
        cat_aqeedah = Category.objects.filter(slug='aqeedah').first()
        cat_arabic = Category.objects.filter(slug='arabic').first()

        for mapping in pdf_mappings:
            slug = mapping['seo_slug']
            file_path = mapping['file']

            # Try to find existing book
            book = Book.objects.filter(seo_slug=slug).first()

            if book:
                # Attach PDF to existing book
                book.file = file_path
                book.save(update_fields=['file', 'updated_at'])
                attached += 1
                self.stdout.write(f'  📎 Attached: {file_path} → {book.title_hausa}')
            elif 'create' in mapping:
                # Create new book with PDF
                data = mapping['create']
                data['seo_slug'] = slug
                data['file'] = file_path

                # Assign category
                if 'tafsir' in slug or 'quran' in slug or 'alkurani' in slug or 'ushurin' in slug:
                    data['category'] = cat_tafsir
                elif 'tajweed' in slug:
                    data['category'] = cat_arabic
                else:
                    data['category'] = cat_aqeedah

                book = Book.objects.create(**data)
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  ✅ Created: {book.title_hausa} + PDF'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Book not found: {slug}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Done! Attached: {attached} | Created: {created}'
        ))
