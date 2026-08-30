from django.db import migrations, models


PURPLE = {
    "accent_color": {"#7c5cff", "#a78bfa", "#7c4dff", "#7c3aed", "#a855f7", "#8b5cf6"},
    "goal_fill": {"#a78bfa", "#7c4dff", "#7c5cff", "#7c3aed", "#a855f7", "#8b5cf6"},
    "goal_track": {"#2a2438", "#e9e1ff", "#1e1b4b", "#2a1848", "#12081f"},
}

CHROME = {
    "accent_color": "#c9a227",
    "goal_fill": "#c9a227",
    "goal_track": "#1c1c20",
}


def paint_chrome(apps, schema_editor):
    SiteSettings = apps.get_model("donations", "SiteSettings")
    for site in SiteSettings.objects.all():
        changed = []
        for field, olds in PURPLE.items():
            current = (getattr(site, field, "") or "").lower()
            if current in olds:
                setattr(site, field, CHROME[field])
                changed.append(field)
        if changed:
            site.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0006_atomic_dark_widgets"),
    ]

    operations = [
        migrations.RunPython(paint_chrome, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sitesettings",
            name="accent_color",
            field=models.CharField(default="#c9a227", max_length=9, verbose_name="رنگ اصلی"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="goal_fill",
            field=models.CharField(default="#c9a227", max_length=9, verbose_name="رنگ پرشدگی"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="goal_track",
            field=models.CharField(default="#1c1c20", max_length=9, verbose_name="رنگ پس‌زمینه نوار"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="gateway_theme",
            field=models.CharField(
                choices=[
                    ("midnight", "گرافیت طلایی"),
                    ("aurora", "شفق"),
                    ("royal", "طلایی سلطنتی"),
                    ("ember", "آتشی"),
                    ("ocean", "اقیانوسی"),
                ],
                default="midnight",
                max_length=20,
                verbose_name="تم درگاه",
            ),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="list_style",
            field=models.CharField(
                choices=[
                    ("stack", "لیست عمودی"),
                    ("cards", "کارت‌ها"),
                    ("ticker", "نوار افقی متحرک"),
                    ("pills", "قرص‌های اتمیک"),
                ],
                default="pills",
                max_length=20,
                verbose_name="ظاهر لیست",
            ),
        ),
    ]
