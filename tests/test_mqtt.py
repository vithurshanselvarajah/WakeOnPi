import wakeonpi.mqtt as mqtt


def test_publish_no_client(monkeypatch):
    monkeypatch.setattr(mqtt, "_client", None)
    mqtt.publish("motion", "ON")


def test_publish_motion_and_display(monkeypatch):
    calls = []

    class DummyClient:
        def publish(self, topic, payload, retain=False):
            calls.append((topic, payload, retain))

    monkeypatch.setattr(mqtt, "_client", DummyClient())
    mqtt.publish_motion(True)
    mqtt.publish_display(False)
    assert any(c[1] == 'ON' for c in calls)
    assert any(c[1] == 'OFF' for c in calls)
