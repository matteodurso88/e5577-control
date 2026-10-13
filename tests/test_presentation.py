"""UI copy/semantics tests. No Qt or modem required."""

from dataclasses import dataclass
import unittest

from pocket_manager.presentation import (
    friendly_band_status, friendly_benchmark_result, friendly_changes,
    friendly_connection, friendly_error, friendly_rf, friendly_route,
    friendly_signal,
)


@dataclass
class Result:
    band: int
    med_mbps: float
    med_ttfb_ms: float


class PresentationTests(unittest.TestCase):
    def test_connected_state_is_readable_without_erasing_firmware_precision(self):
        self.assertEqual(friendly_connection("Connessa (secondo firmware)"), "Connessa")
        self.assertEqual(friendly_connection("Disconnessa"), "Non connessa")
        self.assertEqual(friendly_connection("Non disponibile"), "Stato non disponibile")

    def test_coarse_signal_does_not_become_dbm(self):
        self.assertEqual(friendly_signal("1/5 tacche (indicatore firmware)"), "1 su 5 tacche")
        self.assertEqual(friendly_signal("0/5 tacche (indicatore firmware)"), "0 su 5 tacche")
        self.assertEqual(friendly_signal("Non disponibile"), "Non disponibile")
        self.assertEqual(friendly_rf("Misure RSRP/RSRQ/SINR/RSSI indisponibili"),
                         "Non fornite dal dispositivo")

    def test_route_gate_is_understandable_but_blocks_wrong_wan(self):
        error = "Route NON attraverso il pocket: gateway=192.168.100.1; richiesto gateway=192.168.8.1"
        self.assertIn("un'altra rete", friendly_route(False, error))
        self.assertIn("collegalo direttamente", friendly_route(False, error))
        self.assertIn("puoi procedere", friendly_route(True, "Uscita verificata").lower())

    def test_ttfb_is_explained_as_response_time(self):
        text = friendly_benchmark_result(Result(3, 25.0, 45))
        self.assertIn("tempo di risposta 45 ms", text)
        self.assertNotIn("TTFB", text)
        self.assertIn("può cambiare", text)

    def test_status_translation_preserves_failed_and_unavailable_states(self):
        self.assertEqual(friendly_band_status("OK"), "Completata")
        self.assertEqual(friendly_band_status("Errore"), "Non riuscita")
        self.assertEqual(friendly_band_status("Nessuna connessione LTE"), "Senza connessione 4G")
        self.assertEqual(friendly_band_status("Nessuna misura"), "Dati non disponibili")

    def test_changes_are_human_readable(self):
        self.assertEqual(friendly_changes("bars"), "Segnale")
        self.assertEqual(friendly_changes("bars, connection"), "Segnale, Connessione")
        self.assertEqual(friendly_changes("Inizio osservazione"), "Inizio registrazione")
        self.assertEqual(friendly_changes(""), "Nessuna variazione")

    def test_friendly_auth_error_and_critical_rollback(self):
        self.assertIn("Password", friendly_error("108006: Username and Password wrong"))
        self.assertIn("ATTENZIONE", friendly_error("baseline NON ripristinata"))
        self.assertIn("supportata", friendly_error("100002: No support"))


if __name__ == "__main__":
    unittest.main()
