from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Removed: scraped books feature has been permanently deleted.'

    def handle(self, *args, **options):
        raise CommandError('The scrape_books command was removed permanently because ScrapedBook was deleted.')
