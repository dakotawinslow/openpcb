from django.conf import settings
from django.core.checks import Warning, register


@register()
def email_backend_check(app_configs, **kwargs):
    errors = []
    if (
        not settings.DEBUG
        and not settings.TESTING
        and settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend'
    ):
        errors.append(
            Warning(
                'EMAIL_BACKEND is the console backend in production.',
                hint=(
                    'Password reset and other account emails will be written to the '
                    'server log instead of being delivered to users. Set EMAIL_BACKEND '
                    'to a real backend (e.g. SMTP via Resend) in .env.'
                ),
                id='core.W001',
            )
        )
    return errors
