import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class MobizonError(Exception):
    def __init__(self, message, code=None, data=None):
        super().__init__(message)
        self.code = code
        self.data = data


def mask_phone(phone):
    if not phone:
        return ''
    if len(phone) <= 6:
        return '***'
    return f'{phone[:4]}***{phone[-4:]}'


def sanitize_mobizon_data(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if str(key).lower() in {'apikey', 'recipient', 'phone', 'to', 'text'}:
                sanitized[key] = '***'
            else:
                sanitized[key] = sanitize_mobizon_data(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_mobizon_data(item) for item in value]

    return value


class MobizonClient:
    def __init__(
        self,
        base_url=None,
        api_key=None,
        sender=None,
        output=None,
        api_version=None,
        timeout=None,
    ):
        self.base_url = (base_url or settings.MOBIZON_API_BASE_URL).rstrip('/')
        self.api_key = api_key if api_key is not None else settings.MOBIZON_API_KEY
        self.sender = sender if sender is not None else settings.MOBIZON_SENDER
        self.output = output or settings.MOBIZON_API_OUTPUT
        self.api_version = api_version or settings.MOBIZON_API_VERSION
        self.timeout = timeout or settings.MOBIZON_TIMEOUT_SECONDS

    def send_sms(self, recipient, text):
        if not self.api_key:
            raise MobizonError('Mobizon API key is not configured.')

        url = f'{self.base_url}/Message/SendSmsMessage'
        payload = {
            'apiKey': self.api_key,
            'output': self.output,
            'api': self.api_version,
            'recipient': recipient,
            'text': text,
        }
        if self.sender:
            payload['from'] = self.sender

        body = urllib.parse.urlencode(payload).encode('utf-8')
        request = urllib.request.Request(
            url,
            data=body,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            method='POST',
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw_response = response.read().decode('utf-8')
        except urllib.error.URLError as exc:
            logger.warning('Mobizon network error for %s: %s', mask_phone(recipient), exc.__class__.__name__)
            raise MobizonError('Mobizon request failed.') from exc
        except TimeoutError as exc:
            logger.warning('Mobizon timeout for %s', mask_phone(recipient))
            raise MobizonError('Mobizon request timed out.') from exc

        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            logger.warning('Mobizon returned malformed JSON for %s', mask_phone(recipient))
            raise MobizonError('Mobizon returned malformed response.') from exc

        code = parsed.get('code')
        data = parsed.get('data')
        message = parsed.get('message') or ''

        if code != 0:
            logger.warning(
                'Mobizon rejected SMS for %s with code=%s data=%s',
                mask_phone(recipient),
                code,
                sanitize_mobizon_data(data),
            )
            raise MobizonError(message or 'Mobizon rejected SMS.', code=code, data=data)

        return data or {}
