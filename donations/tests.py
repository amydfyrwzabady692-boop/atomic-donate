from django.test import Client, TestCase

from donations.engine import list_tier, match_condition
from donations.models import AlertCondition, Donation, SiteSettings


class MatchConditionTests(TestCase):
    def test_default_when_empty(self):
        self.assertIsNone(match_condition(50_000))

    def test_open_ended_range(self):
        AlertCondition.objects.create(min_toman=10_000, max_toman=0, label="base")
        hit = match_condition(250_000)
        self.assertEqual(hit.label, "base")

    def test_tightest_range_wins(self):
        AlertCondition.objects.create(min_toman=10_000, max_toman=0, label="all")
        AlertCondition.objects.create(min_toman=100_000, max_toman=500_000, label="gold")
        self.assertEqual(match_condition(50_000).label, "all")
        self.assertEqual(match_condition(200_000).label, "gold")
        self.assertEqual(match_condition(600_000).label, "all")

    def test_outside_range_ignored(self):
        AlertCondition.objects.create(min_toman=20_000, max_toman=30_000, label="mid")
        self.assertIsNone(match_condition(10_000))
        self.assertEqual(match_condition(20_000).label, "mid")
        self.assertEqual(match_condition(30_000).label, "mid")
        self.assertIsNone(match_condition(30_001))

    def test_three_amount_stages(self):
        AlertCondition.objects.create(min_toman=0, max_toman=199_999, label="ash")
        AlertCondition.objects.create(min_toman=200_000, max_toman=999_999, label="ice")
        AlertCondition.objects.create(min_toman=1_000_000, max_toman=0, label="hot")
        self.assertEqual(match_condition(10_000).label, "ash")
        self.assertEqual(match_condition(200_000).label, "ice")
        self.assertEqual(match_condition(999_999).label, "ice")
        self.assertEqual(match_condition(1_000_000).label, "hot")
        self.assertEqual(list_tier(10_000), "tier-ash")
        self.assertEqual(list_tier(200_000), "tier-ice")
        self.assertEqual(list_tier(1_000_000), "tier-hot")


class DonatePageTests(TestCase):
    def setUp(self):
        SiteSettings.load()

    def test_gateway_hides_email_and_phone(self):
        client = Client(HTTP_HOST="127.0.0.1")
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertNotIn('name="email"', body)
        self.assertNotIn('name="mobile"', body)
        self.assertNotIn("ایمیل", body)
        self.assertNotIn("موبایل", body)
        self.assertNotIn("شماره همراه", body)
        self.assertIn("/static/img/omid-atomic.png", body)
        self.assertIn("پرداخت امن", body)
        self.assertIn("کارت به کارت", body)
        self.assertIn("6219 8619 9783 1192", body)
        self.assertIn("امید فیروزآبادی", body)
        self.assertIn("سامان", body)
        self.assertIn("ارسال رسید", body)
        self.assertIn('name="method"', body)
        self.assertIn('value="zarinpal"', body)
        self.assertIn("checked", body)


class CardToCardTests(TestCase):
    TINY_PNG = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    def setUp(self):
        SiteSettings.load()
        self.client = Client(HTTP_HOST="127.0.0.1")

    def _form(self, **extra):
        data = {
            "name": "حامی کارت",
            "amount": "10000",
            "message": "سلام",
            "emoji": "🔥",
            "show_name": "on",
            "show_message": "on",
            "show_in_list": "on",
            "terms": "on",
            "method": "card",
        }
        data.update(extra)
        return data

    def test_card_without_receipt_stays_off_the_list(self):
        response = self.client.post("/pay/", self._form())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Donation.objects.count(), 0)
        body = response.content.decode("utf-8")
        self.assertIn("عکس رسید", body)

    def test_card_with_receipt_waits_for_confirm(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        receipt = SimpleUploadedFile("slip.png", self.TINY_PNG, content_type="image/png")
        response = self.client.post("/pay/", self._form(receipt=receipt))
        self.assertEqual(response.status_code, 200)
        donation = Donation.objects.get()
        self.assertEqual(donation.status, Donation.Status.PENDING)
        self.assertEqual(donation.method, Donation.Method.CARD)
        self.assertTrue(donation.receipt)
        self.assertIn("در انتظار تأیید", response.content.decode("utf-8"))

    def test_confirm_marks_paid(self):
        from django.contrib.auth.models import User
        from django.core.files.uploadedfile import SimpleUploadedFile

        receipt = SimpleUploadedFile("slip.png", self.TINY_PNG, content_type="image/png")
        self.client.post("/pay/", self._form(receipt=receipt))
        donation = Donation.objects.get()
        User.objects.create_user("omid", password="secret", is_staff=True)
        self.client.login(username="omid", password="secret")
        response = self.client.post(f"/panel/donations/{donation.pk}/confirm/", {"next": "panel_donations"})
        self.assertEqual(response.status_code, 302)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.Status.PAID)
        self.assertTrue(donation.paid_at)
        self.assertTrue(donation.ref_id.startswith("card-"))


class OverlayTests(TestCase):
    def setUp(self):
        SiteSettings.load()

    def test_alert_list_goal_need_key_when_set(self):
        from django.test import override_settings

        client = Client(HTTP_HOST="127.0.0.1")
        with override_settings(OVERLAY_TOKEN="obs-secret"):
            self.assertEqual(client.get("/overlay/alert/").status_code, 404)
            for path in (
                "/overlay/alert/?key=obs-secret",
                "/overlay/list/?key=obs-secret&mode=last",
                "/overlay/goal/?key=obs-secret",
                "/overlay/label/?key=obs-secret&mode=latest",
                "/overlay/total/?key=obs-secret&period=all",
                "/overlay/queue/?key=obs-secret",
                "/overlay/timer/?key=obs-secret&mode=stopwatch",
            ):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, path)
            snap = client.get("/overlay/snapshot/?key=obs-secret")
            self.assertEqual(snap.status_code, 200)
            self.assertEqual(snap.json().get("type"), "snapshot")
