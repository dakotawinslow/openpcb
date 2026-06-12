from django.test import SimpleTestCase
from django.test.utils import override_settings

from core.checks import email_backend_check


class EmailBackendCheckTests(SimpleTestCase):
    @override_settings(
        DEBUG=False,
        TESTING=False,
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
    )
    def test_console_backend_in_production_warns(self):
        errors = email_backend_check(None)
        self.assertEqual([e.id for e in errors], ['core.W001'])

    @override_settings(DEBUG=False, EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    def test_real_backend_in_production_is_fine(self):
        self.assertEqual(email_backend_check(None), [])

    @override_settings(DEBUG=True, EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_console_backend_in_debug_is_fine(self):
        self.assertEqual(email_backend_check(None), [])
