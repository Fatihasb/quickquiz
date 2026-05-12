from django.db import migrations, models
import random
import string


def generate_codes(apps, schema_editor):
    """Générer un code unique pour chaque quiz existant."""
    Quiz = apps.get_model('quiz', 'Quiz')
    used = set()
    for quiz in Quiz.objects.all():
        while True:
            code = ''.join(random.choices(string.digits, k=6))
            if code not in used:
                used.add(code)
                quiz.access_code = code
                quiz.save(update_fields=['access_code'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='quiz',
            name='access_code',
            field=models.CharField(
                blank=True, default='', help_text="Code PIN d'accès au quiz",
                max_length=8,
            ),
        ),
        migrations.RunPython(generate_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='quiz',
            name='access_code',
            field=models.CharField(
                max_length=8, unique=True,
                help_text="Code PIN d'accès au quiz"
            ),
        ),
    ]
