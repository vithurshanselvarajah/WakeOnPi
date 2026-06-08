import unittest


class TestAppIntegration(unittest.TestCase):

    def test_app_module_import(self):
        from wakeonpi import app
        self.assertIsNotNone(app)

    def test_app_has_implementation(self):
        from wakeonpi import app
        self.assertTrue(len(dir(app)) > 0)


if __name__ == '__main__':
    unittest.main()
