from django.contrib import admin

from .models import AlertCondition, Donation, SiteSettings


@admin.register(AlertCondition)
class AlertConditionAdmin(admin.ModelAdmin):
    list_display = ("label", "min_toman", "max_toman", "duration")


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("درگاه", {"fields": ("display_name", "page_title", "bio", "avatar", "accent_color", "gateway_theme")}),
        ("کارت به کارت", {"fields": ("card_to_card_enabled", "card_number", "card_bank", "card_holder")}),
        ("آلارم", {"fields": ("alert_gif", "alert_sound", "alert_seconds", "alert_volume", "sound_enabled", "tts_enabled", "tts_volume", "alert_style", "alert_text", "alert_name_size")}),
        ("ابزارها", {"fields": ("list_style", "goal_style", "list_size", "goal_title", "goal_target_toman", "goal_start_toman", "goal_fill", "goal_track", "goal_text", "goal_bg")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("name", "amount_toman", "emoji", "method", "status", "is_test", "ref_id", "created_at")
    list_filter = ("status", "method", "is_test")
    search_fields = ("name", "message", "ref_id", "authority")
    readonly_fields = ("authority", "ref_id", "created_at", "paid_at")
