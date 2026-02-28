import io
import os
import time
import types
import requests
import logging
from unittest import mock

from cracker import crack_router


class DummyResponse:
    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def test_success_by_status(tmp_path, monkeypatch):
    pwfile = tmp_path / "pw.txt"
    pwfile.write_text("pass1\npass2\n")

    called = {'count': 0}

    def fake_post(url, data=None, headers=None, timeout=10):
        called['count'] += 1
        if called['count'] == 2:
            return DummyResponse(status_code=302, text="redirect", headers={'Location': '/index.htm'})
        return DummyResponse(status_code=200, text="failed")

    monkeypatch.setattr(requests, 'post', fake_post)

    found = crack_router('http://localhost', 'admin', str(pwfile), timeout=5, delay=0, success_indicators=['index.htm'], success_status_codes=[302])
    assert found is not None


def test_success_by_body_and_header(tmp_path, monkeypatch):
    pwfile = tmp_path / "pw.txt"
    pwfile.write_text("one\ntwo\n")

    def fake_post(url, data=None, headers=None, timeout=10):
        return DummyResponse(status_code=200, text="Welcome, admin", headers={'Set-Cookie': 'session=abc'})

    monkeypatch.setattr(requests, 'post', fake_post)

    found = crack_router('http://localhost', 'admin', str(pwfile), timeout=5, delay=0,
                         success_indicators=['welcome'], success_headers={'Set-Cookie': 'session='})
    assert found is not None


def test_failed_log_and_delay(tmp_path, monkeypatch):
    pwfile = tmp_path / "pw.txt"
    pwfile.write_text("pw1\npw2\n")
    failed_log = tmp_path / "failed.txt"

    def fake_post(url, data=None, headers=None, timeout=10):
        return DummyResponse(status_code=200, text="nope")

    monkeypatch.setattr(requests, 'post', fake_post)

    sleep_calls = []

    def fake_sleep(s):
        sleep_calls.append(s)

    monkeypatch.setattr(time, 'sleep', fake_sleep)

    crack_router('http://localhost', 'admin', str(pwfile), timeout=5, delay=0.1, success_indicators=['admin'], failed_log_file=str(failed_log))

    # failed log should contain two lines
    assert failed_log.exists()
    assert failed_log.read_text().count('\n') >= 2
    assert sleep_calls, "sleep should have been called"