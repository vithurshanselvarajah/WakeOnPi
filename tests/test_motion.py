import unittest


class TestMotionDetection(unittest.TestCase):

    def test_motion_module_import(self):
        from wakeonpi import motion
        self.assertIsNotNone(motion)

    def test_motion_has_implementation(self):
        from wakeonpi import motion
        self.assertTrue(len(dir(motion)) > 0)


if __name__ == '__main__':
    unittest.main()
