from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('tasks', '0016_discordmessage')]

    operations = [
        migrations.AddField(
            model_name='person', name='discord_verification_code',
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name='person', name='discord_verification_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='person', name='discord_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
