from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('tasks', '0017_person_discord_verification')]

    operations = [
        migrations.AddField(
            model_name='project',
            name='last_unverified_discord_reminder_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
