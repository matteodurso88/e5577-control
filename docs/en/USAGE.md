# User guide — EN

[Italiano](../it/USAGE.md) · [Installation](INSTALL.md)

## First start and connection

1. Launch **E5577 Control**; confirm the title shows `v1.0.1`, the persistent canonical **matt88.it** footer and **About** button.
2. Connect your computer to the Huawei E5577Cs-321 network (Wi-Fi or USB). The historical router address is `192.168.8.1`, but verify the real address and credentials through the official Huawei interface.
3. Use **Find device** (`Trova dispositivo`) or a saved profile, then **Connect** (`Connetti`). The app checks compatible Huawei API endpoints; finding a candidate is not proof of exact hardware identity.
4. Start with read-only connection, network, SIM, and signal checks. No band operation or cellular-data toggle is necessary for a smoke test.

The UI is currently in **Italian** even though documentation is bilingual.

## Tabs

| Italian UI tab | Purpose |
| --- | --- |
| `Stato connessione` | Cards for mobile network, approximate signal bars, LTE band status and SMS; includes data-connection switch |
| `Andamento` | Recent local telemetry samples and changes |
| `Messaggi` | Read-only inbox, paging, double-click for full plain-text SMS |
| `Confronta bande` | Explicit, potentially data-consuming bandwidth comparison with routing preflight |
| `Controllo manuale` | Advanced LTE-band mask/mode controls and restore |
| `Dettagli tecnici` | Advanced RF metrics, API diagnostics and sanitized export |

Use **Mostra strumenti avanzati** to reveal the technical tabs and device-address fields without clearing their state.

## Important restrictions

- **Signal bars** are the modem's rough icon scale, not a dBm reading. Allowed bands do not prove the serving band.
- **Mobile data switch:** requires explicit confirmation, with read-back; it changes cellular data, not the app's local login or the modem's Wi-Fi.
- **Band operations and benchmarks:** can cut connectivity. Use a backup connection; record the original mask; verify WAN route through the pocket before any benchmark. A failed restore is a critical error, never a success.
- **SMS:** no sending, deletion, read-status mutation, or persistent SMS archive.
- **Privacy:** never include passwords, tokens, IMEI, serial number, full SMS text or private API dumps in issues.

No cloud account or background service is needed for the desktop app. See [Security](SECURITY.md).
