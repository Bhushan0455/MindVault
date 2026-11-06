import os
import unittest
from unittest.mock import patch

from app.services.llm import safe_provider_message


class ProviderDiagnostics(unittest.TestCase):
    def test_key_redacted_before_truncation(self):
        key = "fictional-secret-for-test"
        message = safe_provider_message(ValueError("Invalid key " + key + " for request"), key)
        self.assertNotIn(key, message)
        self.assertIn("[REDACTED_KEY]", message)

    def test_url_and_bearer_removed(self):
        message = safe_provider_message(ValueError("URL https://example.invalid/?key=hidden Bearer hidden-token"))
        self.assertNotIn("hidden-token", message)
        self.assertNotIn("key=hidden", message)

    def test_provider_message_preserves_diagnostic(self):
        class ProviderError(Exception):
            message = "Invalid JSON schema: too many states for serving."
        self.assertIn("too many states", safe_provider_message(ProviderError()))

    def test_environment_keys_and_email_removed(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY":"another-private-test-key"}):
            message = safe_provider_message(ValueError("another-private-test-key demo@example.com"))
        self.assertNotIn("another-private-test-key", message)
        self.assertNotIn("demo@example.com", message)

    def test_diagnostic_output_is_bounded(self):
        self.assertLessEqual(len(safe_provider_message(ValueError("word "*1000))), 500)


if __name__ == "__main__": unittest.main()
