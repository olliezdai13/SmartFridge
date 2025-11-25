import unittest

from smartfridge_backend.services.ingestion import (
    TRUNCATION_SUFFIX,
    truncate_raw_llm_output,
)


class TruncateRawLLMOutputTests(unittest.TestCase):
    def test_returns_none_for_absent_text(self):
        self.assertIsNone(truncate_raw_llm_output(None))
        self.assertIsNone(truncate_raw_llm_output(""))

    def test_does_not_truncate_when_under_limit(self):
        text = "short text"
        self.assertEqual(
            truncate_raw_llm_output(text, limit_bytes=100), text
        )

    def test_truncates_when_over_limit(self):
        text = "a" * 50
        limit = 20
        result = truncate_raw_llm_output(text, limit_bytes=limit)
        self.assertTrue(result.endswith(TRUNCATION_SUFFIX))
        self.assertLessEqual(len(result.encode("utf-8")), limit)


if __name__ == "__main__":
    unittest.main()
