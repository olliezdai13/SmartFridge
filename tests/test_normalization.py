import unittest

from smartfridge_backend.services.normalization import normalize_product_name


class NormalizeProductNameTests(unittest.TestCase):
    def test_required_examples(self):
        cases = {
            "Oranges": "orange",
            "orange": "orange",
            "red_pepper": "red pepper",
            "red-bell-peppers": "red bell pepper",
            "Bell Pepper!": "bell pepper",
            " Green-PEPPERS ": "green pepper",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_product_name(raw), expected)


if __name__ == "__main__":
    unittest.main()
