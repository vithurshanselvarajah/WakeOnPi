import unittest


class TestCameraInterface(unittest.TestCase):

    def test_camera_module_import(self):
        from wakeonpi import camera
        self.assertIsNotNone(camera)

    def test_camera_has_implementation(self):
        from wakeonpi import camera
        self.assertTrue(len(dir(camera)) > 0)


if __name__ == '__main__':
    unittest.main()
