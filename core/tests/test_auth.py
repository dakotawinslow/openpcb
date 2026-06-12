from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class LoginRateLimitTests(TestCase):
    """django-allauth rate-limits login_failed by default (ACCOUNT_RATE_LIMITS,
    5 attempts / 5 min per username) — this just confirms it's active."""

    def setUp(self):
        self.user = User.objects.create_user('ratelimituser', password='correct-password')
        self.url = reverse('account_login')

    def _attempt(self):
        return self.client.post(self.url, {'login': 'ratelimituser', 'password': 'wrong-password'})

    def test_repeated_failed_logins_are_rate_limited(self):
        for _ in range(5):
            resp = self._attempt()
            self.assertContains(resp, 'username and/or password')

        resp = self._attempt()
        self.assertContains(resp, 'Too many failed login attempts')
