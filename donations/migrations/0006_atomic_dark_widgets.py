from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


LIGHT = {
    "list_bg": {"#ffffff", "#fff"},
    "list_text": {"#2e1065"},
    "goal_bg": {"#ffffff", "#fff"},
    "goal_text": {"#3b0764", "#2e1065"},
    "goal_track": {"#e9e1ff"},
    "goal_fill": {"#7c4dff"},
}

DARK = {
    "list_bg": "#121218",
    "list_text": "#f4f1ea",
    "goal_bg": "#121218",
    "goal_text": "#f4f1ea",
    "goal_track": "#2a2438",
    "goal_fill": "#a78bfa",
}


def paint_dark(apps, schema_editor):
    SiteSettings = apps.get_model("donations", "SiteSettings")
    for site in SiteSettings.objects.all():
        changed = []
        for field, olds in LIGHT.items():
            current = (getattr(site, field, "") or "").lower()
            if current in olds:
                setattr(site, field, DARK[field])
                changed.append(field)
        if changed:
            site.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0005_zarinpal_max_toman"),
    ]

    operations = [
        migrations.RunPython(paint_dark, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sitesettings",
            name="goal_bg",
            field=models.CharField(default="#121218", max_length=9, verbose_name="رنگ پشت ویجت"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="goal_fill",
            field=models.CharField(default="#a78bfa", max_length=9, verbose_name="رنگ پرشدگی"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="goal_text",
            field=models.CharField(default="#f4f1ea", max_length=9, verbose_name="رنگ نوشته هدف"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="goal_track",
            field=models.CharField(default="#2a2438", max_length=9, verbose_name="رنگ پس‌زمینه نوار"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="goal_radius",
            field=models.PositiveSmallIntegerField(
                default=20,
                validators=[MinValueValidator(0), MaxValueValidator(40)],
                verbose_name="گردی گوشه",
            ),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="list_bg",
            field=models.CharField(default="#121218", max_length=9, verbose_name="رنگ پشت لیست"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="list_text",
            field=models.CharField(default="#f4f1ea", max_length=9, verbose_name="رنگ متن لیست"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="alert_style",
            field=models.CharField(
                choices=[
                    ("classic", "کلاسیک"),
                    ("neon", "نئون"),
                    ("glass", "شیشه‌ای تیره"),
                    ("banner", "بنر پایین"),
                    ("comic", "حباب پیام"),
                ],
                default="glass",
                max_length=20,
                verbose_name="ظاهر آلارم",
            ),
        ),
    ]
