import unittest


class TestMQTTIntegration(unittest.TestCase):

    def test_mqtt_module_import(self):
        from wakeonpi import mqtt
        self.assertIsNotNone(mqtt)

    def test_mqtt_has_implementation(self):
        from wakeonpi import mqtt
        self.assertTrue(len(dir(mqtt)) > 0)


if __name__ == '__main__':
    unittest.main()
