import unittest


class TestBrowserModule(unittest.TestCase):

    def test_browser_module_import(self):
        from wakeonpi import browser
        self.assertIsNotNone(browser)

    def test_browser_has_implementation(self):
        from wakeonpi import browser
        self.assertTrue(len(dir(browser)) > 0)


if __name__ == '__main__':
    unittest.main()
