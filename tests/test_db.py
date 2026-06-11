import unittest
import os
import gc
from pathlib import Path
from wakeonpi import db, state

class TestDatabaseOperations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.original_db_file = db.DB_FILE
        cls.test_db_file = Path(__file__).parent / "test_wakeonpi.db"

    @classmethod
    def tearDownClass(cls):
        db.DB_FILE = cls.original_db_file
        gc.collect()
        if cls.test_db_file.exists():
            try:
                os.remove(cls.test_db_file)
            except Exception as e:
                raise AssertionError(f"Failed to remove test database file {cls.test_db_file}: {e}") from e

    def setUp(self):
        db.DB_FILE = self.test_db_file
        db.init_db()
        try:
            conn = db.get_db_connection()
            try:
                conn.execute("DELETE FROM settings")
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            self.fail(f"Failed to reset settings table during test setup: {e}")

    def tearDown(self):
        pass

    def test_init_db_and_connection(self):
        conn = db.get_db_connection()
        self.assertIsNotNone(conn)
        conn.close()

    def test_check_db_health(self):
        state.db_load_error = "some_error"
        db.check_db_health()
        self.assertIsNone(state.db_load_error)

    def test_hash_and_verify_password(self):
        password = "my_secure_password"
        hashed = db.hash_password(password)
        self.assertIn("$", hashed)
        self.assertTrue(db.verify_password(password, hashed))
        self.assertFalse(db.verify_password("wrong_password", hashed))
        self.assertFalse(db.verify_password(password, "invalid_hash"))
        self.assertFalse(db.verify_password(password, "invalid$hash$format"))

    def test_settings_get_set_all(self):
        db.set_setting("TEST_KEY", "TEST_VAL")
        val = db.get_setting("TEST_KEY")
        self.assertEqual(val, "TEST_VAL")

        # Test default
        self.assertEqual(db.get_setting("NON_EXISTENT_KEY", "default_val"), "default_val")

        # Test get_all_settings
        all_settings = db.get_all_settings()
        self.assertEqual(all_settings.get("TEST_KEY"), "TEST_VAL")

    @unittest.mock.patch("wakeonpi.db.os.remove")
    def test_reset_db(self, mock_remove):
        def fake_remove(path):
            conn = db.get_db_connection()
            try:
                conn.execute("DELETE FROM settings")
                conn.commit()
            finally:
                conn.close()
        mock_remove.side_effect = fake_remove

        db.set_setting("KEY_TO_RESET", "VALUE")
        self.assertEqual(db.get_setting("KEY_TO_RESET"), "VALUE")
        db.reset_db()
        self.assertIsNone(db.get_setting("KEY_TO_RESET"))
        mock_remove.assert_called_once()

    def test_exception_handling_in_connection(self):
        # Point to a directory to force database connection error
        db.DB_FILE = Path(__file__).parent
        with self.assertRaises(Exception):
            db.get_db_connection()
        self.assertIsNotNone(state.db_load_error)

    def test_exception_handling_in_verify_password(self):
        self.assertFalse(db.verify_password("pw", None))

if __name__ == '__main__':
    unittest.main()
