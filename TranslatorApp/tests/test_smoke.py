"""Smoke tests — validate that the app is running and all pages load.

Usage:
    # Against local dev server (default):
    pytest tests/test_smoke.py -v

    # Against production:
    BASE_URL=https://kadeutsch.org pytest tests/test_smoke.py -v

Requires the target server to be running. These tests do NOT modify data —
they only issue GET requests and check for HTTP 200 responses.
"""

import os
import pytest
import requests

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5555').rstrip('/')

# Timeout for each request in seconds
TIMEOUT = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get(path):
    """GET a path and return the response, with a reasonable timeout."""
    return requests.get(f'{BASE_URL}{path}', timeout=TIMEOUT, allow_redirects=True)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealth:
    """Verify the /health endpoint works and reports healthy status."""

    def test_health_returns_200(self):
        r = get('/health')
        assert r.status_code == 200, f'Health check returned {r.status_code}'

    def test_health_json_status_ok(self):
        r = get('/health')
        data = r.json()
        assert data['status'] == 'ok', f"Health status: {data}"

    def test_health_db_ok(self):
        r = get('/health')
        data = r.json()
        assert data['db'] == 'ok', f"DB check failed: {data['db']}"

    def test_health_has_version(self):
        r = get('/health')
        data = r.json()
        assert data['version'] != 'unknown', 'Version not available'


# ---------------------------------------------------------------------------
# Page-load smoke tests — every GET route should return 200
# ---------------------------------------------------------------------------

class TestPageLoads:
    """Verify that all main pages load without errors."""

    def test_home(self):
        r = get('/')
        assert r.status_code == 200

    def test_about(self):
        r = get('/about')
        assert r.status_code == 200

    def test_subtitles(self):
        r = get('/subtitles/')
        assert r.status_code == 200

    def test_content(self):
        r = get('/content/')
        assert r.status_code == 200

    def test_glossary(self):
        r = get('/glossary/')
        assert r.status_code == 200

    def test_statistic(self):
        r = get('/statistic/')
        assert r.status_code == 200

    def test_pretranslate(self):
        r = get('/pretranslate/')
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Response content checks
# ---------------------------------------------------------------------------

class TestResponseContent:
    """Verify that pages return expected content (not error pages)."""

    def test_home_contains_html(self):
        r = get('/')
        assert '<html' in r.text.lower(), 'Home page missing <html> tag'

    def test_health_json_parseable(self):
        r = get('/health')
        data = r.json()  # Raises if not valid JSON
        assert 'status' in data

    def test_content_type_health(self):
        r = get('/health')
        assert 'application/json' in r.headers.get('Content-Type', '')

    def test_content_type_pages(self):
        r = get('/')
        assert 'text/html' in r.headers.get('Content-Type', '')
