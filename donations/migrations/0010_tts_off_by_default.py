from django.db import migrations, models


def silence_tts(apps, schema_editor):
    SiteSettings = apps.get_model("donations", "SiteSettings")
    SiteSettings.objects.filter(pk=1).update(tts_enabled=False)


class Migration(migrations.Migration):
    dependencies = [
        ("donations", "0009_card_to_card"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="tts_enabled",
            field=models.BooleanField("خواندن پیام", default=False),
        ),
        migrations.RunPython(silence_tts, migrations.RunPython.noop),
    ]
