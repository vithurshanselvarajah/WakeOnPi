import unittest


class TestSystemInfo(unittest.TestCase):

    def test_system_module_import(self):
        from wakeonpi import system
        self.assertIsNotNone(system)

    def test_system_has_implementation(self):
        from wakeonpi import system
        self.assertTrue(len(dir(system)) > 0)


if __name__ == '__main__':
    unittest.main()
