import unittest


class TestAuthentication(unittest.TestCase):

    def test_auth_module_import(self):
        from wakeonpi import auth
        self.assertIsNotNone(auth)

    def test_auth_has_implementation(self):
        from wakeonpi import auth
        self.assertTrue(len(dir(auth)) > 0)


if __name__ == '__main__':
    unittest.main()
