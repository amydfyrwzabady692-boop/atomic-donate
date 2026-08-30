from django.db import migrations, models

import donations.models


class Migration(migrations.Migration):
    dependencies = [
        ("donations", "0008_ice_blue_palette"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="card_to_card_enabled",
            field=models.BooleanField(default=True, verbose_name="کارت به کارت فعال"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="card_number",
            field=models.CharField(default="6219861997831192", max_length=19, verbose_name="شماره کارت"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="card_bank",
            field=models.CharField(default="سامان", max_length=40, verbose_name="بانک"),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="card_holder",
            field=models.CharField(default="امید فیروزآبادی", max_length=80, verbose_name="صاحب کارت"),
        ),
        migrations.AddField(
            model_name="donation",
            name="method",
            field=models.CharField(
                choices=[("zarinpal", "زرین‌پال"), ("card", "کارت به کارت")],
                default="zarinpal",
                max_length=12,
                verbose_name="روش پرداخت",
            ),
        ),
        migrations.AddField(
            model_name="donation",
            name="receipt",
            field=models.ImageField(
                blank=True,
                upload_to=donations.models.receipt_upload_to,
                verbose_name="رسید کارت به کارت",
            ),
        ),
    ]
