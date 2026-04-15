from django.core.management.base import BaseCommand
from books.models import SovereignGlossary


class Command(BaseCommand):
    help = 'Seed sovereign glossary with Islamic terms'

    def handle(self, *args, **options):
        terms = [
            ('التوحيد', 'Tauhidi', 'Monotheism', 'Akida'),
            ('الشرك', 'Shirka', 'Polytheism', 'Akida'),
            ('العقيدة', 'Akida', 'Creed/Belief', 'Akida'),
            ('الإيمان', 'Imani', 'Faith', 'Akida'),
            ('الإسلام', 'Musulunci', 'Islam', 'Akida'),
            ('الإحسان', 'Ihsani', 'Excellence', 'Akida'),
            ('الصلاة', 'Sallah', 'Prayer', 'Ibada'),
            ('الزكاة', 'Zakka', 'Alms', 'Ibada'),
            ('الصيام', 'Azumi', 'Fasting', 'Ibada'),
            ('الحج', 'Hajji', 'Pilgrimage', 'Ibada'),
            ('الوضوء', 'Alwala', 'Ablution', 'Ibada'),
            ('القرآن', 'Alkur\'ani', 'Quran', 'Littattafai'),
            ('الحديث', 'Hadisi', 'Hadith', 'Littattafai'),
            ('السنة', 'Sunnah', 'Prophetic Tradition', 'Littattafai'),
            ('الفقه', 'Fikhu', 'Jurisprudence', 'Ilimi'),
            ('التفسير', 'Tafsiri', 'Exegesis', 'Ilimi'),
            ('السيرة', 'Sira', 'Biography', 'Ilimi'),
            ('الجنة', 'Aljanna', 'Paradise', 'Akida'),
            ('النار', 'Wuta', 'Hellfire', 'Akida'),
            ('التوبة', 'Tuba', 'Repentance', 'Ibada'),
            ('الدعاء', 'Addu\'a', 'Supplication', 'Ibada'),
            ('الذكر', 'Zikiri', 'Remembrance', 'Ibada'),
            ('الجهاد', 'Jihadi', 'Striving', 'Fikhu'),
            ('الحلال', 'Halal', 'Permissible', 'Fikhu'),
            ('الحرام', 'Haram', 'Forbidden', 'Fikhu'),
            ('البدعة', 'Bid\'a', 'Innovation', 'Akida'),
            ('الشفاعة', 'Ceto', 'Intercession', 'Akida'),
            ('القدر', 'Ƙaddara', 'Divine Decree', 'Akida'),
            ('الملائكة', 'Mala\'iku', 'Angels', 'Akida'),
            ('الأنبياء', 'Annabawa', 'Prophets', 'Akida'),
        ]

        created = 0
        for ar, ha, en, cat in terms:
            _, is_new = SovereignGlossary.objects.get_or_create(
                term_arabic=ar, term_hausa=ha,
                defaults={'term_english': en, 'category': cat}
            )
            if is_new:
                created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} glossary terms (total: {len(terms)})'))
