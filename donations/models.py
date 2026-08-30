from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum


class SiteSettings(models.Model):
    class GatewayTheme(models.TextChoices):
        MIDNIGHT = "midnight", "آبی یخی"
        AURORA = "aurora", "شفق"
        ROYAL = "royal", "طلایی سلطنتی"
        EMBER = "ember", "آتشی"
        OCEAN = "ocean", "اقیانوسی"

    class AlertStyle(models.TextChoices):
        CLASSIC = "classic", "کلاسیک"
        NEON = "neon", "نئون"
        GLASS = "glass", "شیشه‌ای تیره"
        BANNER = "banner", "بنر پایین"
        COMIC = "comic", "حباب پیام"

    class ListStyle(models.TextChoices):
        STACK = "stack", "لیست عمودی"
        CARDS = "cards", "کارت‌ها"
        TICKER = "ticker", "نوار افقی متحرک"
        PILLS = "pills", "قرص‌های اتمیک"

    class GoalStyle(models.TextChoices):
        BAR = "bar", "نوار افقی"
        RING = "ring", "حلقه"
        CRYSTAL = "crystal", "کریستالی"
        SPLIT = "split", "اعداد جدا"

    class CensorMode(models.TextChoices):
        STAR = "star", "ستاره‌گذاری کلمه"
        SKIP = "skip", "عدم نمایش روی استریم"

    display_name = models.CharField("نام نمایشی", max_length=80, default="Omid_Atomic")
    page_title = models.CharField("عنوان صفحه", max_length=120, default="حمایت از استریم")
    bio = models.CharField("توضیح کوتاه درگاه", max_length=220, blank=True, default="اگر از استریم لذت می‌بری، حمایت کن تا ادامه بدم.")
    avatar = models.ImageField("آواتار", upload_to="avatar/", blank=True)
    accent_color = models.CharField("رنگ اصلی", max_length=9, default="#7dd3fc")
    gateway_theme = models.CharField("تم درگاه", max_length=20, choices=GatewayTheme.choices, default=GatewayTheme.MIDNIGHT)
    show_goal_on_gateway = models.BooleanField("نمایش هدف روی درگاه", default=True)
    show_recent_on_gateway = models.BooleanField("نمایش حامیان روی درگاه", default=True)
    require_terms = models.BooleanField("تیک قوانین روی درگاه", default=True)
    instagram = models.CharField("اینستاگرام", max_length=160, blank=True)
    telegram = models.CharField("تلگرام", max_length=160, blank=True)
    youtube = models.CharField("یوتیوب", max_length=160, blank=True)
    preset_amounts = models.CharField("مبالغ پیشنهادی", max_length=120, default="10000,20000,50000,100000,200000,500000")

    goal_title = models.CharField("عنوان هدف", max_length=120, default="هدف استریم")
    goal_target_toman = models.PositiveIntegerField("هدف (تومان)", default=20_000_000)
    goal_start_toman = models.PositiveIntegerField("شروع نوار (تومان)", default=0)
    goal_baseline_toman = models.PositiveIntegerField("پایه ریست", default=0)
    goal_active = models.BooleanField("هدف فعال", default=True)
    goal_show_title = models.BooleanField("نمایش عنوان هدف", default=True)
    goal_show_details = models.BooleanField("نمایش جزئیات هدف", default=True)
    goal_fill = models.CharField("رنگ پرشدگی", max_length=9, default="#7dd3fc")
    goal_track = models.CharField("رنگ پس‌زمینه نوار", max_length=9, default="#1c1c20")
    goal_text = models.CharField("رنگ نوشته هدف", max_length=9, default="#f4f1ea")
    goal_bg = models.CharField("رنگ پشت ویجت", max_length=9, default="#121218")
    goal_radius = models.PositiveSmallIntegerField("گردی گوشه", default=20, validators=[MinValueValidator(0), MaxValueValidator(40)])
    goal_font_size = models.PositiveSmallIntegerField("اندازه نوشته", default=18, validators=[MinValueValidator(10), MaxValueValidator(40)])
    goal_bar_height = models.PositiveSmallIntegerField("ارتفاع نوار", default=22, validators=[MinValueValidator(8), MaxValueValidator(48)])
    goal_title_tpl = models.CharField("قالب عنوان", max_length=80, default="هدف: <NAME>")
    goal_details_tpl = models.CharField("قالب جزئیات", max_length=80, default="<CURRENT> از <GOAL> تومان")

    alert_text = models.CharField("رنگ متن آلارم", max_length=9, default="#ffffff")
    alert_name_size = models.PositiveSmallIntegerField("اندازه نام آلارم", default=22, validators=[MinValueValidator(12), MaxValueValidator(48)])
    list_bg = models.CharField("رنگ پشت لیست", max_length=9, default="#121218")
    list_text = models.CharField("رنگ متن لیست", max_length=9, default="#f4f1ea")
    min_amount_toman = models.PositiveIntegerField("حداقل دونیت (تومان)", default=10_000)
    max_amount_toman = models.PositiveIntegerField("حداکثر دونیت (تومان)", default=100_000_000)

    alert_seconds = models.PositiveIntegerField("مدت آلارم (ثانیه)", default=8, validators=[MinValueValidator(2), MaxValueValidator(30)])
    alert_volume = models.PositiveSmallIntegerField("صدای دونیت", default=80, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tts_enabled = models.BooleanField("خواندن پیام", default=True)
    tts_volume = models.PositiveSmallIntegerField("صدای خواندن", default=85, validators=[MinValueValidator(0), MaxValueValidator(100)])
    tts_rate = models.FloatField("سرعت خواندن", default=1.0)
    tts_pitch = models.FloatField("زیر و بمی صدا", default=1.0)
    sound_enabled = models.BooleanField("پخش صدای دونیت", default=True)
    list_size = models.PositiveSmallIntegerField(
        "تعداد لیست حامیان",
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
    )
    emoji_pack = models.CharField("شکلک‌ها", max_length=80, default="🔥,❤️,💎,👑,⚡,🎮,💜,🌟,🙌,💯")
    censor_enabled = models.BooleanField("سانسور فعال", default=False)
    censor_mode = models.CharField("نوع سانسور", max_length=8, choices=CensorMode.choices, default=CensorMode.STAR)
    censor_words = models.TextField("کلمات سانسور (با کاما یا خط جدید)", blank=True)

    alert_style = models.CharField("ظاهر آلارم", max_length=20, choices=AlertStyle.choices, default=AlertStyle.GLASS)
    list_style = models.CharField("ظاهر لیست", max_length=20, choices=ListStyle.choices, default=ListStyle.PILLS)
    goal_style = models.CharField("ظاهر هدف", max_length=20, choices=GoalStyle.choices, default=GoalStyle.BAR)

    alert_gif = models.FileField("گیف آلارم", upload_to="alerts/", blank=True)
    alert_sound = models.FileField("صدای دونیت", upload_to="sounds/", blank=True)

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def emojis(self):
        items = [e.strip() for e in (self.emoji_pack or "").split(",") if e.strip()]
        return items or ["🔥", "❤️", "💎"]

    def presets(self):
        values = []
        for part in (self.preset_amounts or "").split(","):
            part = part.strip().replace("،", "")
            if part.isdigit():
                values.append(int(part))
        return values or [10_000, 50_000, 100_000]

    def goal_current(self) -> int:
        total = (
            Donation.objects.filter(status=Donation.Status.PAID, is_test=False)
            .aggregate(total=Sum("amount_toman"))
            .get("total")
        )
        return max(0, int(total or 0) + int(self.goal_start_toman) - int(self.goal_baseline_toman))

    def goal_percent(self) -> int:
        if not self.goal_target_toman:
            return 0
        return min(100, round(self.goal_current() * 100 / self.goal_target_toman))

    def __str__(self):
        return self.display_name


class AlertCondition(models.Model):
    min_toman = models.PositiveIntegerField("از مبلغ")
    max_toman = models.PositiveIntegerField("تا مبلغ (۰ یعنی بی‌نهایت)", default=0)
    label = models.CharField("نام شرط", max_length=40, blank=True)
    duration = models.PositiveIntegerField("مدت (ثانیه)", default=8)
    style = models.CharField("ظاهر", max_length=20, blank=True)
    gif = models.FileField("گیف این بازه", upload_to="alerts/", blank=True)
    sound = models.FileField("صدای این بازه", upload_to="sounds/", blank=True)

    class Meta:
        ordering = ["min_toman"]
        verbose_name = "شرط آلارم"
        verbose_name_plural = "شرط‌های آلارم"

    def __str__(self):
        hi = self.max_toman or "∞"
        return f"{self.min_toman:,}–{hi} {self.label}"


class Donation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار"
        PAID = "paid", "پرداخت شده"
        FAILED = "failed", "ناموفق"
        TEST = "test", "تست"

    name = models.CharField("نام", max_length=64)
    amount_toman = models.PositiveIntegerField("مبلغ (تومان)")
    message = models.CharField("پیام", max_length=280, blank=True)
    emoji = models.CharField("شکلک", max_length=16, blank=True)
    show_name = models.BooleanField("نمایش نام", default=True)
    show_message = models.BooleanField("نمایش پیام", default=True)
    show_in_list = models.BooleanField("نمایش در لیست", default=True)
    mobile = models.CharField("موبایل", max_length=15, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    status = models.CharField("وضعیت", max_length=12, choices=Status.choices, default=Status.PENDING)
    authority = models.CharField("Authority", max_length=64, unique=True, null=True, blank=True)
    ref_id = models.CharField("کد پیگیری", max_length=64, blank=True)
    is_test = models.BooleanField("تست", default=False)
    created_at = models.DateTimeField("زمان", auto_now_add=True)
    paid_at = models.DateTimeField("زمان پرداخت", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "حمایت"
        verbose_name_plural = "حمایت‌ها"

    def list_tier(self):
        n = int(self.amount_toman or 0)
        if n >= 1_000_000:
            return "tier-hot"
        if n >= 200_000:
            return "tier-ice"
        return "tier-ash"

    def __str__(self):
        return f"{self.name} — {self.amount_toman:,}"
