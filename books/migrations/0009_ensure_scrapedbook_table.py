from django.db import migrations


def ensure_scrapedbook_table(apps, schema_editor):
    ScrapedBook = apps.get_model("books", "ScrapedBook")
    table_name = ScrapedBook._meta.db_table
    existing_tables = schema_editor.connection.introspection.table_names()

    if table_name not in existing_tables:
        schema_editor.create_model(ScrapedBook)


def noop_reverse(apps, schema_editor):
    # Intentionally keep table on reverse to avoid accidental data loss.
    pass


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("books", "0008_add_book_drive_url"),
    ]

    operations = [
        migrations.RunPython(ensure_scrapedbook_table, noop_reverse),
    ]
