# Dual Switch Cover

[![Release](https://img.shields.io/github/v/release/tempod/switch-to-cover-home-assistant)](https://github.com/tempod/switch-to-cover-home-assistant/releases)
[![Validate](https://github.com/tempod/switch-to-cover-home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/tempod/switch-to-cover-home-assistant/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![License](https://img.shields.io/github/license/tempod/switch-to-cover-home-assistant)](LICENSE)

Integrazione personalizzata per Home Assistant che crea un'entità `cover`
completa a partire da due entità `switch` o `input_boolean`: una per la
salita e una per la discesa.

È pensata per i motori comandati da due relè indipendenti — schede relè,
moduli ESPHome, Shelly in profilo interruttore — che da soli non saprebbero
nulla della propria posizione. L'integrazione ci aggiunge il calcolo della
percentuale di apertura, l'interblocco e il tracciamento dei comandi fisici.

## Funzionalità

- Crea un'entità `cover` da due `switch` o `input_boolean`
- Calcolo della posizione in percentuale a partire dai tempi di corsa
- Apertura, chiusura, arresto e posizionamento a percentuale
- **La posizione viene mantenuta al riavvio** di Home Assistant
- **Riconoscimento dei comandi fisici**: se un relè viene attivato da un
  pulsante a parete o da uno script sul dispositivo, l'integrazione se ne
  accorge, aggiorna la posizione e spegne il relè a fine corsa
- **Interblocco**: i due relè non vengono mai attivati contemporaneamente
- **Ricalibrazione automatica**: in apertura o chiusura totale il motore
  compie la corsa piena, azzerando la deriva accumulata dalle corse parziali
- Tipo di cover selezionabile (tapparella, veneziana, tenda da sole,
  cancello, porta garage e altri), con icone e comandi coerenti
- Tempi e opzioni modificabili in qualsiasi momento, senza dover ricreare
  l'entità e senza riavviare Home Assistant
- Interfaccia disponibile in italiano e inglese

## Requisiti

- Home Assistant 2025.2.4 o successivo
- Due entità `switch` o `input_boolean` già funzionanti, una per la salita
  e una per la discesa

> [!IMPORTANT]
> Le entità di tipo `button` non sono utilizzabili: sono prive di stato e
> non possono restare attive per tutta la durata della corsa.

## Installazione

### Tramite HACS (consigliato)

1. In HACS, dal menu con i tre puntini, scegliere **Repository personalizzati**
2. Incollare `https://github.com/tempod/switch-to-cover-home-assistant`
   e selezionare la categoria **Integration**
3. Cercare **Dual Switch Cover** e scaricarla
4. Riavviare Home Assistant

### Manuale

1. Copiare la cartella `custom_components/dual_switch_cover` dentro la
   cartella `custom_components` della propria configurazione
2. Riavviare Home Assistant

## Configurazione

Andare su **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**
e cercare **Dual Switch Cover**.

| Parametro | Descrizione | Default |
|---|---|---|
| Nome | Nome della cover | Tenda |
| Entità per aprire | `switch` o `input_boolean` che comanda la salita | — |
| Entità per chiudere | `switch` o `input_boolean` che comanda la discesa | — |
| Tempo di apertura | Secondi per una corsa completa in salita | 25 |
| Tempo di chiusura | Secondi per una corsa completa in discesa | 25 |
| Ritardo in partenza | Pausa tra lo spegnimento del relè opposto e l'accensione di quello attivo | 0 |
| Ritardo in arresto | Attesa prima di diseccitare il relè a fine corsa | 0 |
| Tipo di cover | Determina icone e terminologia | Tapparella |
| Corsa piena | Corsa completa in apertura e chiusura totale | Attivo |

Tutti i valori sono modificabili in seguito dal pulsante **Configura** nella
scheda dell'integrazione. Le modifiche vengono applicate subito.

### Come misurare i tempi

Cronometrare il motore da fine corsa a fine corsa, separatamente per salita
e discesa: sui motori tubolari i due tempi differiscono spesso di qualche
secondo, perché la discesa è aiutata dal peso.

### Ritardo in partenza

Serve a proteggere il motore dall'inversione istantanea del senso di marcia.
Se i relè non sono interbloccati meccanicamente, impostare almeno 0,3
secondi è una buona precauzione.

### Corsa piena

Con questa opzione attiva, un comando di apertura o chiusura totale fa
girare il motore per l'intero tempo configurato, anche partendo da metà
corsa. Il motore si ferma quindi contro il proprio fine corsa e la posizione
stimata torna esatta, eliminando la deriva che si accumula inevitabilmente
con un calcolo a tempo.

> [!WARNING]
> Disattivare l'opzione se il motore **non** dispone di fine corsa
> meccanici o elettronici, altrimenti continuerebbe a spingere contro
> l'arresto.

## Comandi fisici

L'integrazione distingue i comandi che ha impartito lei da quelli arrivati
da altre fonti. Quando un relè si attiva senza che sia stata lei a
comandarlo — un pulsante a parete, uno script sul dispositivo, l'app del
produttore — la cover avvia il tracciamento della corsa, spegne il relè
opposto per sicurezza e diseccita quello attivo al termine del percorso.

Se il relè viene spento dall'esterno prima della fine, la posizione viene
congelata al punto raggiunto.

## Note e limiti

- La posizione è **stimata sul tempo**, non misurata. Un ostacolo, una
  variazione di tensione o un motore che rallenta con il freddo introducono
  un errore. La ricalibrazione a fine corsa lo corregge a ogni apertura o
  chiusura totale.
- Se Home Assistant viene riavviato durante una corsa, i relè vengono
  spenti all'avvio e viene registrato un avviso nel log: la posizione
  potrebbe essere imprecisa finché non si esegue una corsa completa.
- L'interblocco è **funzionale, non di sicurezza**. Su impianti dove
  l'attivazione simultanea dei due relè può danneggiare il motore, va
  previsto anche un interblocco meccanico o a relè.
- Le icone dell'integrazione richiedono Home Assistant 2026.3 o successivo.
  Sulle versioni precedenti l'integrazione funziona ugualmente, con l'icona
  generica.

## Segnalazioni

Problemi e proposte: [issue tracker](https://github.com/tempod/switch-to-cover-home-assistant/issues).

## Licenza

Distribuito con licenza MIT. Vedere il file [LICENSE](LICENSE).
