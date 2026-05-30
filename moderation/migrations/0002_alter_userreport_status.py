# Generated manually while translating UI labels to English.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moderation', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userreport',
            name='status',
            field=models.CharField(choices=[('new', 'New'), ('reviewed', 'Reviewed'), ('rejected', 'Rejected')], default='new', max_length=20),
        ),
    ]
