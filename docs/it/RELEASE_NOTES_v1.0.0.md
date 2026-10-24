# E5577 Control v1.0.0 — Note di rilascio

**Prima release Product autonoma** dedicata al modem Huawei E5577Cs-321, evoluzione dell'app WORKSHOP Pocket Radio Manager.

## Novità
- Repository pubblico indipendente con la cronologia di **124 commit** del precedente subtree preservata.
- Nome **E5577 Control** nell'interfaccia, nei binari e negli installer Linux/Windows.
- Versione sempre visibile, finestra **Informazioni** e **logo SVG canonico completo matt88.it** nel footer compatto, con link cliccabile e variante chiaro/scuro.
- Monitoraggio connessione e rete mobile, traffico e segnale indicativo, SMS in sola lettura, profili locali, impostazioni LTE con lettura di verifica e benchmark delle bande protetto.
- Percorsi dei profili e servizio del portachiavi OS storico invariati per conservare i dispositivi salvati.

## Pacchetti

Linux x86-64: `.deb` e portabile `.tar.gz`. Windows x86-64: Inno Setup `.exe` e portabile `.zip`. È disponibile il manifesto `SHA256SUMS.txt` per verificare tutti e quattro i pacchetti. **Le build non sono firmate.**

## Limiti e sicurezza

Compatibilità prioritaria Huawei E5577Cs-321, senza garanzia di supporto per tutti i firmware o altri modelli. Le bande consentite non identificano automaticamente la cella LTE agganciata; metriche RF mancanti non sono inventate. Il cambio bande e il benchmark possono interrompere Internet e consumare dati mobili. Usare una connessione alternativa e verificare il ripristino. CI e test simulati non equivalgono al collaudo hardware.

Guide: [Panoramica](OVERVIEW.md) · [Installazione](INSTALL.md) · [Utilizzo](USAGE.md) · [Rilascio](RELEASE.md).
