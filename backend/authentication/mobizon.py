import json
import logging
import re
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
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) <= 6:
        return '***'
    return f'{digits[:4]}***{digits[-4:]}'


def mask_sensitive_text(value):
    if not isinstance(value, str):
        return value

    def replace_digits(match):
        digits = match.group(0)
        if len(digits) <= 6:
            return '***'
        return mask_phone(digits)

    return re.sub(r'\d{4,}', replace_digits, value)


def sanitize_mobizon_data(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if key_lower in {'apikey', 'api_key', 'token', 'text', 'message'}:
                sanitized[key] = '***'
            elif key_lower in {'recipient', 'phone', 'to'}:
                sanitized[key] = sanitize_mobizon_data(mask_sensitive_text(item))
            else:
                sanitized[key] = sanitize_mobizon_data(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_mobizon_data(item) for item in value]

    if isinstance(value, str):
        return mask_sensitive_text(value)

    return value


class MobizonClient:
    def __init__(self, base_url=None, api_key=None, sender=None, timeout=None):
        self.base_url = (base_url or settings.MOBIZON_API_BASE_URL).rstrip('/')
        if self.base_url.lower().endswith('/service'):
            self.base_url = self.base_url[:-8]
        self.api_key = api_key if api_key is not None else settings.MOBIZON_API_KEY
        self.sender = sender if sender is not None else settings.MOBIZON_SENDER
        self.timeout = timeout or settings.MOBIZON_TIMEOUT_SECONDS

    def send_message(self, recipient, text):
        if not self.api_key:
            raise MobizonError('Mobizon API key is not configured.')

        query = urllib.parse.urlencode(
            {
                'output': getattr(settings, 'MOBIZON_API_OUTPUT', 'json'),
                'api': getattr(settings, 'MOBIZON_API_VERSION', 'v1'),
                'apiKey': self.api_key,
            }
        )
        payload = {
            'recipient': re.sub(r'\D', '', str(recipient)),
            'text': text,
        }
        if self.sender:
            payload['from'] = self.sender

        body = urllib.parse.urlencode(payload).encode('utf-8')
        request = urllib.request.Request(
            f'{self.base_url}/service/Message/SendSmsMessage?{query}',
            data=body,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cache-Control': 'no-cache',
                'User-Agent': 'Baiqymyz/1.0 (+https://baiqymyz.kz)',
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw_response = response.read().decode('utf-8')
                status_code = response.status
        except urllib.error.HTTPError as exc:
            raw_response = exc.read().decode('utf-8', errors='replace')
            logger.warning('Mobizon HTTP error for %s: status=%s', mask_phone(recipient), exc.code)
            raise MobizonError(
                'Mobizon request failed.',
                code=exc.code,
                data=self._parse_response(raw_response, allow_text=True),
            ) from exc
        except urllib.error.URLError as exc:
            logger.warning('Mobizon network error for %s: %s', mask_phone(recipient), exc.__class__.__name__)
            raise MobizonError('Mobizon request failed.') from exc
        except TimeoutError as exc:
            logger.warning('Mobizon timeout for %s', mask_phone(recipient))
            raise MobizonError('Mobizon request timed out.') from exc

        parsed = self._parse_response(raw_response)
        if status_code < 200 or status_code >= 300:
            logger.warning(
                'Mobizon rejected SMS OTP for %s with status=%s data=%s',
                mask_phone(recipient),
                status_code,
                sanitize_mobizon_data(parsed),
            )
            raise MobizonError('Mobizon rejected message.', code=status_code, data=parsed)

        code = parsed.get('code') if isinstance(parsed, dict) else None
        if code not in (None, 0, '0'):
            logger.warning(
                'Mobizon rejected SMS OTP for %s with code=%s data=%s',
                mask_phone(recipient),
                code,
                sanitize_mobizon_data(parsed),
            )
            raise MobizonError(parsed.get('message') or 'Mobizon rejected message.', code=code, data=parsed)

        return parsed

    def _parse_response(self, raw_response, allow_text=False):
        try:
            return json.loads(raw_response or '{}')
        except json.JSONDecodeError as exc:
            if allow_text:
                return {'raw': mask_sensitive_text(raw_response)}
            logger.warning('Mobizon returned malformed JSON')
            raise MobizonError('Mobizon returned malformed response.') from exc
