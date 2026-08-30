from django.test import Client, TestCase

from donations.engine import match_condition
from donations.models import AlertCondition, SiteSettings


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
