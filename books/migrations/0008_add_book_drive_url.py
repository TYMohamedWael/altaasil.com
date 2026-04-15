from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0007_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='drive_url',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='رابط Google Drive (PDF)'),
        ),
    ]
