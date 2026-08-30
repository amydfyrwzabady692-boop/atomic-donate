from django.db import migrations, models


OLD = {
    "accent_color": {
        "#c9a227",
        "#7c5cff",
        "#a78bfa",
        "#7c4dff",
        "#7c3aed",
        "#a855f7",
        "#8b5cf6",
        "#e8c547",
        "#e8b86d",
    },
    "goal_fill": {
        "#c9a227",
        "#a78bfa",
        "#7c4dff",
        "#7c5cff",
        "#7c3aed",
        "#a855f7",
        "#8b5cf6",
        "#e8c547",
        "#fde68a",
        "#fbbf24",
    },
}

ICE = {
    "accent_color": "#7dd3fc",
    "goal_fill": "#7dd3fc",
}


def paint_ice(apps, schema_editor):
    SiteSettings = apps.get_model("donations", "SiteSettings")
    for site in SiteSettings.objects.all():
        changed = []
        for field, olds in OLD.items():
            current = (getattr(site, field, "") or "").lower()
            if current in olds:
                setattr(site, field, ICE[field])
                changed.append(field)
        if changed:
            site.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0007_chrome_gold_palette"),
    ]

    operations = [
        migrations.RunPython(paint_ice, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sitesettings",
            name="accent_color",
            field=models.CharField(default="#7dd3fc", max_length=9, verbose_name="رنگ اصلی"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="goal_fill",
            field=models.CharField(default="#7dd3fc", max_length=9, verbose_name="رنگ پرشدگی"),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="gateway_theme",
            field=models.CharField(
                choices=[
                    ("midnight", "آبی یخی"),
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
    ]
