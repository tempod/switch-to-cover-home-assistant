# switch-to-cover-home-assistant
Crea entità "cover" partendo da 2 "switch" o 2 "button"

# Funzioni principali
- crezione di una entità "cover" partendo da due entità "button" o due "switch"
- possibilità di impostare:
  - tempo di apertura
  - tempo di chiusura
  - ritardo di attivazione in apertura
  - ritardo di disattivazione in chiusura
- calcolo della percentuale di apertura in base al tempo impostato
- calcolo della posizione sia tramite interfaccia sia tramite comandi fisici
- 
# Installazione
Tramite HACS
- aggiungere il mio repository su hacs, tipo integrazione
- cercare dual_switch_cover
- installare e riavviare home assistant
- andare su impostazioni --> dispositivi e servizi --> aggiungi integrazione --> cercare "dual_switch_cover"
- impostare tutti i valori richiesti
- al termine avrete una nuova entità di tipo cover
