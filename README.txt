# Verifica requisiti classi di concorso — prima versione

## Contenuto
- `app.py`: applicazione web Streamlit.
- `corsi_list.xlsx`: catalogo dimostrativo di corsi fittizi, con codici SSD reali.
- `requisiti_ministero.xlsx`: classi A-11 e A-12, regole CFU/SSD e note/fonti.
- `requirements.txt`: dipendenze Python.

## Avvio
1. Installa Python 3.10 o successivo.
2. Metti tutti e quattro i file nella stessa cartella.
3. Apri un terminale in quella cartella e installa le dipendenze:
   `python -m pip install -r requirements.txt`
4. Avvia:
   `streamlit run app.py`
5. Il browser si aprirà automaticamente. Se non succede, segui l'indirizzo mostrato nel terminale.

## Uso
- Seleziona A-11 o A-12.
- Cerca un corso; seleziona il suggerimento e premi `Aggiungi corso selezionato`.
- Ogni corso è inizialmente pianificato. Il pulsante verde permette di contrassegnarlo come sostenuto.
- Premi `Verifica requisiti` per eseguire il controllo del piano complessivo (sostenuti + pianificati).
- Le selezioni restano nello stato temporaneo della sessione Streamlit; non c'è un database utente nel codice.

## File Excel
`corsi_list.xlsx`, foglio `Corsi`:
- `Codice_insegnamento` deve essere univoco.
- `Nome_corso`, `CFU`, `SSD` sono obbligatori.
- `Corso_di_laurea` è opzionale.
- Per questa versione, ogni riga ha un solo SSD. Se un insegnamento ha più SSD, non ripartire arbitrariamente i CFU: va progettata una struttura dedicata.

`requisiti_ministero.xlsx`:
- `Classi`: voci del menu a tendina.
- `Requisiti`: regole attive per ciascuna classe.
- `Note_e_fonti`: avvertenze e riferimenti.
- `SSD_ammessi` usa valori separati da punto e virgola.
- `Tipo_regola`: `TOTALE`, `MINIMO_SSD` o `MINIMO_GRUPPO`.
- `Attiva`: `SI` oppure `NO`.

## Limiti importanti
I dati di corso sono inventati per test; gli SSD sono codici reali. Le regole A-11/A-12 sono un modello preliminare basato su specifiche condizioni di accesso per titoli LS/LM e non coprono ogni possibile laurea, coorte o disposizione transitoria. Il software controlla la copertura dei CFU/SSD configurati, non certifica l'accesso alla classe di concorso. Verifica e correggi il file `requisiti_ministero.xlsx` prima di usarlo per decisioni reali.

Riferimenti principali:
- DM 255/2023, Tabella A e nota 7 (A-12): https://www.gazzettaufficiale.it/eli/id/2024/02/10/24A00733/SG
- DPR 19/2016 e DM 259/2017 (A-11 e quadro delle classi di concorso): consultare i testi ufficiali e le tabelle aggiornate.
