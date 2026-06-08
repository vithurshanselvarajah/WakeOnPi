import unittest


class TestDisplayControl(unittest.TestCase):

    def test_display_module_import(self):
        from wakeonpi import display
        self.assertIsNotNone(display)

    def test_display_has_implementation(self):
        from wakeonpi import display
        self.assertTrue(len(dir(display)) > 0)


if __name__ == '__main__':
    unittest.main()
