from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("books", "0009_ensure_scrapedbook_table"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ScrapedBook",
        ),
    ]
