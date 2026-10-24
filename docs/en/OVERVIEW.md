# E5577 Control — Overview

[Italiano](../it/OVERVIEW.md) · [Home](../../README.md)

E5577 Control is a local-first, cross-platform **PySide6 / Qt 6** desktop manager aimed at the **Huawei E5577Cs-321** LTE mobile hotspot. It complements rather than replaces the Huawei web interface. Other modem models and firmware versions have not been certified.

## Supported operations

- **Connection dashboard:** mobile network, operator and access technology, modem-reported signal bars, current data-switch state and traffic rate (when reported). Traffic rate is not an Internet speed test.
- **SMS:** display message count, page through the inbox and open a full plain-text reader with a double-click. Messages are read-only; no sending, deleting or read-state mutations.
- **Device discovery and profiles:** find compatible local API endpoints, save local device aliases/addresses and optionally store passwords in the operating system's protected keyring.
- **Monitoring:** recent live samples and friendly status changes; advanced API diagnostic/export view with sensitive data minimization.
- **LTE controls:** inspect supported/allowed bands, apply a selected LTE mask with read-back, and attempt to restore the previous configuration. These can interrupt WAN connectivity; firmware may reject or ignore operations.
- **Band comparison:** guarded benchmark after routing checks verify that Internet traffic really goes via the pocket router. Tests may consume cellular data.

## Important radio semantics

An LTE-band **permission mask** is not a measurement of the serving-cell band. The UI labels a band **detected**, **inferred**, or **unavailable** with different certainty. The tested Huawei firmware can return no RSRP/RSRQ/SINR, PCI, cell ID or serving-band data; the interface must not make up these values. A single allowed LTE band may support a qualified inference, not an RF observation.

## Scope and support

Linux x86-64 (native Debian package and portable tarball) and Windows x86-64 (Inno Setup installer and portable ZIP). Native builds are unsigned. macOS packaging and generic Huawei-router compatibility are outside this release's validated targets.

Desktop credits: **matt88.it**, shown through the complete canonical SVG wordmark in the footer. The **About** dialog displays product/version and a text credit.

See [Usage](USAGE.md), [Security](SECURITY.md), [Architecture](ARCHITECTURE.md) and [Release](RELEASE.md).
