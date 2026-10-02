from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ["TELEGRAM_ADMIN_USER_ID"] = "123456789"

import telegram_control


class TelegramControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        telegram_control.DB_PATH = Path(self.temp_dir.name) / "state.db"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_admin_authorization(self) -> None:
        self.assertTrue(telegram_control.verify_admin(123456789))
        self.assertFalse(telegram_control.verify_admin(987654321))

    def test_approval_lifecycle(self) -> None:
        approval_id = telegram_control.create_approval(
            "Connection Comment",
            "Specific observation followed by one real question.",
        )

        self.assertEqual(len(approval_id), 8)

        row = telegram_control.resolve_approval(approval_id, "approved")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["status"], "approved")

        second_attempt = telegram_control.resolve_approval(
            approval_id,
            "rejected",
        )
        self.assertIsNone(second_attempt)

    def test_invalid_approval_id_is_rejected(self) -> None:
        self.assertIsNone(
            telegram_control.resolve_approval("not-valid", "approved")
        )

    def test_help_contains_core_commands(self) -> None:
        help_text = telegram_control.help_text()
        for command in ("/trend india", "/comment", "/approve", "/reject"):
            self.assertIn(command, help_text)


if __name__ == "__main__":
    unittest.main()
