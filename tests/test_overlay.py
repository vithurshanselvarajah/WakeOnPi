import unittest


class TestOverlayModule(unittest.TestCase):

    def test_overlay_module_import(self):
        from wakeonpi import overlay
        self.assertIsNotNone(overlay)

    def test_overlay_has_implementation(self):
        from wakeonpi import overlay
        self.assertTrue(len(dir(overlay)) > 0)


if __name__ == '__main__':
    unittest.main()
