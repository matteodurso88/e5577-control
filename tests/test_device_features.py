"""SMS privacy and WAN switch tests; fully offline and no hardware writes."""

import unittest
from unittest.mock import patch

from pocket_manager.backend import HuaweiRadioBackend, RadioError
from pocket_manager.device_features import (
    mobile_data_state, sms_messages, sms_summary, UnsupportedFeature,
)
from pocket_manager.radio import safe_json_data


class SmsModelsTests(unittest.TestCase):
    def test_home_count_unread_and_inbox(self):
        summary = sms_summary({"LocalInbox": "14", "LocalUnread": "3",
                               "LocalOutbox": "7"})
        self.assertEqual((summary.inbox, summary.unread), (14, 3))

    def test_unsupported_sms_count_does_not_show_zero(self):
        summary = sms_summary({"__error__": "100002"})
        self.assertIsNone(summary.unread)
        self.assertIsNone(summary.inbox)

    def test_sms_inbox_normalizes_one_or_many_messages(self):
        payload = {"Count": "1", "Messages": {"Message": {
            "Index": "21", "Phone": "+3912345", "Date": "2026-10-13 10:30:00",
            "Smstat": "0", "Content": "<b>Non eseguire HTML</b>"
        }}}
        messages = sms_messages(payload)
        self.assertEqual(len(messages), 1)
        self.assertTrue(messages[0].unread)
        self.assertEqual(messages[0].content, "<b>Non eseguire HTML</b>")
        self.assertEqual(sms_messages({"Count": "0", "Messages": {}}), [])

    def test_sms_failure_and_bad_shapes(self):
        with self.assertRaises(UnsupportedFeature):
            sms_messages({"__error__": "100002"})
        with self.assertRaises(UnsupportedFeature):
            sms_messages({"Messages": {"Message": "malformed"}})

    def test_mobile_data_state_does_not_guess_from_connection_status(self):
        self.assertIsNone(mobile_data_state({"ConnectionStatus": "901"}))
        self.assertIsNone(mobile_data_state({"dataswitch": "invalid"}))
        self.assertIsNone(mobile_data_state({"__error__": "100002"}))
        self.assertIs(mobile_data_state({"dataswitch": "1"}), True)
        self.assertIs(mobile_data_state({"dataswitch": "0"}), False)


class FakeSms:
    def __init__(self):
        self.requests = []

    def sms_count(self):
        return {"LocalInbox": "2", "LocalUnread": "1"}

    def get_sms_list(self, *, page, read_count):
        self.requests.append((page, read_count))
        return {"Count": "1", "Messages": {"Message": [
            {"Phone": "+391234567", "Content": "Codice riservato 123456",
             "Index": "1", "Date": "2026-10-13 10:30:00", "Smstat": "0"}
        ]}}


class FakeDialUp:
    def __init__(self, state="1", confirm=True):
        self.state = state
        self.confirm = confirm
        self.writes = []

    def mobile_dataswitch(self):
        return {"dataswitch": self.state}

    def set_mobile_dataswitch(self, *, dataswitch):
        self.writes.append(dataswitch)
        if self.confirm:
            self.state = str(dataswitch)
        return "OK"


class FeatureBackendTests(unittest.TestCase):
    def setUp(self):
        self.backend = HuaweiRadioBackend("192.168.8.1", "admin", "never-log")
        self.sms = FakeSms()
        self.dial = FakeDialUp()
        self.backend.client = type("Client", (), {
            "sms": self.sms, "dial_up": self.dial,
        })()

    def test_sms_are_only_returned_on_explicit_request(self):
        self.assertEqual(self.backend.sms_counts()["LocalUnread"], "1")
        messages = self.backend.sms_inbox()
        self.assertEqual(self.sms.requests, [(1, 20)])
        self.assertIn("Codice riservato", messages[0].content)
        self.assertNotIn("Codice riservato", str(self.backend.sms_counts()))
        self.assertNotIn("Codice riservato", str(safe_json_data(self.backend.sms_counts())))

    def test_no_messages_if_endpoint_unsupported(self):
        self.backend.client.sms = None
        with self.assertRaises(UnsupportedFeature):
            self.backend.sms_inbox()

    @patch("pocket_manager.backend.time.sleep", lambda _: None)
    def test_disconnect_and_reconnect_are_verified(self):
        self.assertIs(self.backend.set_mobile_data(False), False)
        self.assertEqual(self.dial.writes, [0])
        self.assertIs(self.backend.set_mobile_data(True), True)
        self.assertEqual(self.dial.writes, [0, 1])

    def test_repeated_switch_to_same_state_does_not_write(self):
        self.assertIs(self.backend.set_mobile_data(True), True)
        self.assertEqual(self.dial.writes, [])

    def test_unknown_mobile_state_is_fail_closed(self):
        self.dial.state = "unknown"
        with self.assertRaisesRegex(RadioError, "sconosciuto"):
            self.backend.set_mobile_data(False)
        self.assertEqual(self.dial.writes, [])

    @patch("pocket_manager.backend.time.sleep", lambda _: None)
    def test_unconfirmed_switch_never_reports_success(self):
        self.dial.confirm = False
        with self.assertRaisesRegex(RadioError, "non è confermato"):
            self.backend.set_mobile_data(False)
        self.assertEqual(self.dial.writes, [0])

    def test_reject_non_bool_toggle(self):
        with self.assertRaises(ValueError):
            self.backend.set_mobile_data(0)
        self.assertEqual(self.dial.writes, [])


if __name__ == "__main__":
    unittest.main()
