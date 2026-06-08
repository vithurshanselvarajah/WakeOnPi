import unittest


class TestConfiguration(unittest.TestCase):

    def test_config_module_import(self):
        from wakeonpi import config
        self.assertIsNotNone(config)

    def test_config_has_implementation(self):
        from wakeonpi import config
        self.assertTrue(len(dir(config)) > 0)


if __name__ == '__main__':
    unittest.main()
