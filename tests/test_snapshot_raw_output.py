import unittest

from smartfridge_backend.api.snapshot import (
    _TRUNCATION_SUFFIX,
    _truncate_raw_llm_output,
)


class TruncateRawLLMOutputTests(unittest.TestCase):
    def test_returns_none_for_absent_text(self):
        self.assertIsNone(_truncate_raw_llm_output(None))
        self.assertIsNone(_truncate_raw_llm_output(""))

    def test_does_not_truncate_when_under_limit(self):
        text = "short text"
        self.assertEqual(
            _truncate_raw_llm_output(text, limit_bytes=100), text
        )

    def test_truncates_when_over_limit(self):
        text = "a" * 50
        limit = 20
        result = _truncate_raw_llm_output(text, limit_bytes=limit)
        self.assertTrue(result.endswith(_TRUNCATION_SUFFIX))
        self.assertLessEqual(len(result.encode("utf-8")), limit)


if __name__ == "__main__":
    unittest.main()
