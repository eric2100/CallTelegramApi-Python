"""Telegram CLI with configurable Bot API and streaming file uploads."""
from __future__ import annotations

import argparse
import configparser
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
import sys
from urllib.parse import urlsplit

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder


@dataclass(frozen=True)
class Settings:
    token: str
    chat_id: str
    api_base_url: str
    connect_timeout: float
    read_timeout: float
    proxy: str | None

    @classmethod
    def load(cls, path: Path) -> Settings:
        parser = configparser.ConfigParser(interpolation=None)
        with path.open(encoding='utf-8-sig') as stream:
            parser.read_file(stream)
        main = parser['MAIN']
        token = main.get('Token', '').strip()
        chat_id = main.get('SendChatId', '').strip()
        if not token or not chat_id:
            raise ValueError('Token and SendChatId must be configured')
        if any(c.isspace() or c in '/?#' for c in token):
            raise ValueError('Invalid Token format')
        base = (main.get('ApiBaseUrl', '').strip() or 'https://api.telegram.org').rstrip('/')
        url = urlsplit(base)
        if (url.scheme not in ('http', 'https') or not url.hostname
                or url.username is not None or url.password is not None
                or url.query or url.fragment):
            raise ValueError('ApiBaseUrl must be an HTTP(S) root URL without credentials, query or fragment')
        # Accessing port also validates malformed and out-of-range port numbers.
        url.port
        connect_ms = main.getint('ConnectTimeout', 30000)
        read_ms = main.getint('ReadTimeout', 3600000)
        if connect_ms <= 0 or read_ms <= 0:
            raise ValueError('Timeouts must be positive milliseconds')
        proxy_host = main.get('ProxyServer', '').strip()
        proxy = None
        if proxy_host:
            port = int(main.get('ProxyPort', '').strip() or '0')
            if not 1 <= port <= 65535:
                raise ValueError('ProxyPort must be between 1 and 65535')
            if any(c in proxy_host for c in '/@?#'):
                raise ValueError('ProxyServer must be a hostname or IP address')
            host = f'[{proxy_host}]' if ':' in proxy_host and not proxy_host.startswith('[') else proxy_host
            proxy = f'http://{host}:{port}'
        return cls(token, chat_id, base, connect_ms / 1000, read_ms / 1000, proxy)


class BotAPIError(Exception):
    """A request failed; callers should not automatically replay it."""


def post(session: requests.Session, settings: Settings, method: str,
         fields: dict) -> None:
    encoder = MultipartEncoder(fields=fields, encoding='utf-8')
    url = f'{settings.api_base_url}/bot{settings.token}/{method}'
    with session.post(url, data=encoder,
                      headers={'Content-Type': encoder.content_type},
                      timeout=(settings.connect_timeout, settings.read_timeout),
                      allow_redirects=False) as response:
        if not 200 <= response.status_code < 300:
            # Never use raise_for_status(): its message includes the token URL.
            raise BotAPIError(f'{method}: HTTP {response.status_code}')
        try:
            payload = response.json()
        except ValueError:
            raise BotAPIError(f'{method}: invalid JSON response') from None
        if not isinstance(payload, dict) or not isinstance(payload.get('ok'), bool):
            raise BotAPIError(f'{method}: invalid Bot API response')
        if not payload['ok']:
            description = str(payload.get('description', 'request failed'))
            raise BotAPIError(f'{method}: {description}')


def send(settings: Settings, message: str, attachment: Path | None = None) -> None:
    with ExitStack() as stack:
        # Open before sending text so a missing/unreadable file sends nothing.
        file = None
        if attachment is not None:
            if not attachment.is_file():
                raise ValueError('Attachment must be an existing regular file')
            file = stack.enter_context(attachment.open('rb'))
        session = stack.enter_context(requests.Session())
        # Only the explicit INI proxy is used, matching the original application.
        session.trust_env = False
        if settings.proxy:
            session.proxies.update({'http': settings.proxy, 'https': settings.proxy})
        post(session, settings, 'sendMessage', {'chat_id': settings.chat_id, 'text': message})
        if file is not None:
            post(session, settings, 'sendDocument', {
                'chat_id': settings.chat_id,
                'document': (attachment.name, file, 'application/octet-stream'),
            })


def default_config() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent / 'CallTelegram.ini'
    return Path(__file__).resolve().parent / 'CallTelegram.ini'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('message', help='message text')
    parser.add_argument('file', nargs='?', type=Path, help='optional attachment path')
    parser.add_argument('--config', type=Path, default=default_config(), help='INI configuration path')
    args = parser.parse_args(argv)
    settings = None
    try:
        settings = Settings.load(args.config)
        send(settings, args.message, args.file)
    except requests.RequestException:
        # Request exceptions may include token URLs, headers or proxy credentials.
        print('Error: network request failed; check API address, TLS certificate, proxy and timeouts', file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, configparser.Error, BotAPIError) as error:
        detail = str(error)
        if settings is not None:
            detail = detail.replace(settings.token, '<REDACTED>')
        elif isinstance(error, configparser.Error):
            detail = 'Invalid INI configuration'
        print(f'Error: {detail}', file=sys.stderr)
        return 1
    print('OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
