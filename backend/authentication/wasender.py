import json
import logging
import re
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class WasenderError(Exception):
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


def mask_sensitive_text(value):
    if not isinstance(value, str):
        return value

    def replace_digits(match):
        digits = match.group(0)
        if len(digits) <= 6:
            return '***'
        return mask_phone(digits)

    return re.sub(r'\d{4,}', replace_digits, value)


def sanitize_wasender_data(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if key_lower in {'authorization', 'apikey', 'api_key', 'token', 'text', 'message', 'mes'}:
                sanitized[key] = '***'
            elif key_lower in {'recipient', 'phone', 'to'}:
                sanitized[key] = sanitize_wasender_data(mask_sensitive_text(item))
            else:
                sanitized[key] = sanitize_wasender_data(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_wasender_data(item) for item in value]

    if isinstance(value, str):
        return mask_sensitive_text(value)

    return value


def normalize_whatsapp_recipient(recipient):
    value = str(recipient or '').strip()
    if not value:
        return value
    return value if value.startswith('+') else f'+{value}'


class WasenderClient:
    def __init__(self, base_url=None, api_key=None, timeout=None):
        self.base_url = (base_url or settings.WASENDER_API_BASE_URL).rstrip('/')
        self.api_key = api_key if api_key is not None else settings.WASENDER_API_KEY
        self.timeout = timeout or settings.WASENDER_TIMEOUT_SECONDS

    def send_message(self, recipient, text):
        if not self.api_key:
            raise WasenderError('WasenderAPI key is not configured.')

        whatsapp_recipient = normalize_whatsapp_recipient(recipient)
        payload = {
            'to': whatsapp_recipient,
            'text': text,
        }
        body = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            f'{self.base_url}/api/send-message',
            data=body,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
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
            logger.warning('WasenderAPI HTTP error for %s: status=%s', mask_phone(recipient), exc.code)
            raise WasenderError(
                'WasenderAPI request failed.',
                code=exc.code,
                data=self._parse_response(raw_response, allow_text=True),
            ) from exc
        except urllib.error.URLError as exc:
            logger.warning('WasenderAPI network error for %s: %s', mask_phone(recipient), exc.__class__.__name__)
            raise WasenderError('WasenderAPI request failed.') from exc
        except TimeoutError as exc:
            logger.warning('WasenderAPI timeout for %s', mask_phone(recipient))
            raise WasenderError('WasenderAPI request timed out.') from exc

        parsed = self._parse_response(raw_response)
        if status_code < 200 or status_code >= 300:
            logger.warning(
                'WasenderAPI rejected WhatsApp OTP for %s with status=%s data=%s',
                mask_phone(recipient),
                status_code,
                sanitize_wasender_data(parsed),
            )
            raise WasenderError('WasenderAPI rejected message.', code=status_code, data=parsed)

        if self._is_error_response(parsed):
            code = parsed.get('error_code') or parsed.get('code') or parsed.get('status')
            message = parsed.get('error') or parsed.get('message') or 'WasenderAPI rejected message.'
            logger.warning(
                'WasenderAPI rejected WhatsApp OTP for %s with code=%s data=%s',
                mask_phone(recipient),
                code,
                sanitize_wasender_data(parsed),
            )
            raise WasenderError(message, code=code, data=parsed)

        return parsed

    def _parse_response(self, raw_response, allow_text=False):
        try:
            return json.loads(raw_response or '{}')
        except json.JSONDecodeError as exc:
            if allow_text:
                return {'raw': mask_sensitive_text(raw_response)}
            logger.warning('WasenderAPI returned malformed JSON')
            raise WasenderError('WasenderAPI returned malformed response.') from exc

    def _is_error_response(self, parsed):
        if not isinstance(parsed, dict):
            return True
        if parsed.get('success') is False:
            return True
        if parsed.get('error') or parsed.get('errors'):
            return True
        return False
