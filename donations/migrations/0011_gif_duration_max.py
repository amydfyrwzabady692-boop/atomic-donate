from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("donations", "0010_tts_off_by_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="alert_seconds",
            field=models.PositiveIntegerField(
                default=8,
                validators=[MinValueValidator(2), MaxValueValidator(120)],
                verbose_name="مدت گیف دونیت (ثانیه)",
            ),
        ),
        migrations.AlterField(
            model_name="alertcondition",
            name="duration",
            field=models.PositiveIntegerField(
                default=8,
                validators=[MinValueValidator(2), MaxValueValidator(120)],
                verbose_name="مدت (ثانیه)",
            ),
        ),
    ]
