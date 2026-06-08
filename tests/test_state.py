import unittest


class TestStateManagement(unittest.TestCase):

    def test_state_module_import(self):
        from wakeonpi import state
        self.assertIsNotNone(state)

    def test_state_has_implementation(self):
        from wakeonpi import state
        self.assertTrue(len(dir(state)) > 0)


if __name__ == '__main__':
    unittest.main()
