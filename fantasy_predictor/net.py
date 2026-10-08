"""Shared HTTP helper with the retry behaviour the scrapers rely on."""
import time

import requests

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36"
}


def get_with_retry(url, headers=None, timeout=None, retry_on=(Exception,), max_attempts=None, delay=2):
    """GET ``url``, retrying on ``retry_on`` exceptions.

    ``max_attempts=None`` keeps retrying until the request succeeds, which is
    how the original scrapers behaved. Non-200 responses are returned to the
    caller rather than retried.
    """
    attempt = 0
    while max_attempts is None or attempt < max_attempts:
        try:
            return requests.get(url, headers=headers, timeout=timeout)
        except retry_on:
            attempt += 1
        time.sleep(delay)
    raise ConnectionError(f"GET {url} failed after {max_attempts} attempts")
