import unittest
from datetime import date
from decimal import Decimal

import app
import dashboard


class AppTests(unittest.TestCase):
    def test_normalize_decimal_uses_brazilian_format(self):
        self.assertEqual(app.normalize_value(Decimal("123456.78")), "123.456,78")

    def test_normalize_float_uses_brazilian_currency_format(self):
        self.assertEqual(app.normalize_value(434422.8399999999), "434.422,84")

    def test_normalize_date(self):
        self.assertEqual(app.normalize_value(date(2026, 8, 24)), "24/08/2026")

    def test_invalid_enabled_phone_is_rejected(self):
        config = {
            "database": {},
            "preview_message": "teste",
            "whatsapp": {
                "graph_api_version": "v23.0",
                "template_name": "teste",
                "template_language": "pt_BR",
                "template_parameters": ["valor"],
            },
            "recipients": [{"name": "Teste", "phone": "+55 11", "enabled": True}],
        }
        self.assertTrue(any("Telefone inválido" in error for error in app.validate_config(config)))

    def test_dashboard_normalizes_brazilian_phone(self):
        self.assertEqual(dashboard.normalize_phone("(11) 90000-0000"), "5511900000000")

    def test_dashboard_rejects_mutating_sql(self):
        with self.assertRaises(ValueError):
            dashboard.validate_select("DELETE FROM CM_ORDENSVENDA")


if __name__ == "__main__":
    unittest.main()
