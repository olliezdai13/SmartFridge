import unittest
from datetime import timedelta
from http.cookies import SimpleCookie

from flask import Flask, make_response

from smartfridge_backend.services.auth_tokens import (
    AuthSettings,
    apply_auth_cookies,
    clear_auth_cookies,
    decode_token,
    issue_token_pair,
)


class AuthTokenTests(unittest.TestCase):
    def setUp(self):
        self.settings = AuthSettings(
            secret="test-secret",
            access_token_ttl=timedelta(minutes=5),
            refresh_token_ttl=timedelta(days=7),
        )

    def test_issue_and_decode_tokens(self):
        tokens = issue_token_pair("user-123", settings=self.settings)

        access_payload = decode_token(
            tokens.access_token, self.settings, expected_type="access"
        )
        refresh_payload = decode_token(
            tokens.refresh_token, self.settings, expected_type="refresh"
        )

        self.assertEqual(access_payload["sub"], "user-123")
        self.assertEqual(access_payload["refresh"], tokens.refresh_token_id)
        self.assertEqual(refresh_payload["jti"], tokens.refresh_token_id)
        self.assertEqual(refresh_payload["sub"], "user-123")
        self.assertLess(tokens.access_expires_at, tokens.refresh_expires_at)

        expected_delta = (
            self.settings.refresh_token_ttl - self.settings.access_token_ttl
        )
        actual_delta = tokens.refresh_expires_at - tokens.access_expires_at
        self.assertAlmostEqual(
            actual_delta.total_seconds(),
            expected_delta.total_seconds(),
            delta=2,
        )
        self.assertAlmostEqual(
            access_payload["exp"] - access_payload["iat"],
            self.settings.access_token_ttl.total_seconds(),
            delta=2,
        )

    def test_apply_and_clear_cookies(self):
        tokens = issue_token_pair("user-123", settings=self.settings)

        app = Flask(__name__)
        with app.test_request_context():
            response = make_response("ok")
            apply_auth_cookies(response, tokens, settings=self.settings)

            cookies = SimpleCookie()
            for header in response.headers.getlist("Set-Cookie"):
                cookies.load(header)

            access_cookie = cookies[self.settings.access_cookie_name]
            refresh_cookie = cookies[self.settings.refresh_cookie_name]

            self.assertEqual(access_cookie["path"], "/")
            self.assertEqual(refresh_cookie["path"], "/")
            self.assertEqual(
                access_cookie["max-age"],
                str(int(self.settings.access_token_ttl.total_seconds())),
            )
            self.assertEqual(
                refresh_cookie["max-age"],
                str(int(self.settings.refresh_token_ttl.total_seconds())),
            )
            self.assertEqual(access_cookie["samesite"].lower(), "lax")
            self.assertEqual(refresh_cookie["samesite"].lower(), "lax")
            self.assertIn("httponly", access_cookie)
            self.assertIn("httponly", refresh_cookie)
            self.assertIn("secure", access_cookie)
            self.assertIn("secure", refresh_cookie)

            clear_response = make_response("cleared")
            clear_auth_cookies(clear_response, settings=self.settings)

            cleared = SimpleCookie()
            for header in clear_response.headers.getlist("Set-Cookie"):
                cleared.load(header)

            self.assertEqual(
                cleared[self.settings.access_cookie_name]["max-age"], "0"
            )
            self.assertEqual(
                cleared[self.settings.refresh_cookie_name]["max-age"], "0"
            )


if __name__ == "__main__":
    unittest.main()
