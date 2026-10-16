from pathlib import Path
import re
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
COURSES_FILE = BASE_DIR / "corsi_list.xlsx"
RULES_FILE = BASE_DIR / "requisiti_ministero.xlsx"

st.set_page_config(page_title="Verifica requisiti classi di concorso", page_icon="📚", layout="wide")

@st.cache_data
def load_courses():
    df = pd.read_excel(COURSES_FILE, sheet_name="Corsi")
    required = {"Codice_insegnamento", "Nome_corso", "CFU", "SSD"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Nel foglio Corsi mancano le colonne: {', '.join(sorted(missing))}")
    df["CFU"] = pd.to_numeric(df["CFU"], errors="coerce").fillna(0)
    for col in ["Codice_insegnamento", "Nome_corso", "SSD"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    if "Corso_di_laurea" not in df:
        df["Corso_di_laurea"] = ""
    return df

@st.cache_data
def load_rules():
    classes = pd.read_excel(RULES_FILE, sheet_name="Classi").fillna("")
    rules = pd.read_excel(RULES_FILE, sheet_name="Requisiti").fillna("")
    rules["CFU_richiesti"] = pd.to_numeric(rules["CFU_richiesti"], errors="coerce").fillna(0)
    rules["Attiva"] = rules["Attiva"].astype(str).str.strip().str.upper()
    return classes, rules

def split_ssd(value):
    return [x.strip().upper() for x in str(value).split(";") if x.strip()]

def course_matches_ssd(ssd, allowed):
    ssd = str(ssd).strip().upper()
    # exact match for specific SSD; prefix match for group/prefix rules like L-FIL-LET
    return any(ssd == a or ("/" not in a and ssd.startswith(a + "/")) for a in allowed)

def total_cfu_for_rule(selected_courses, allowed):
    # Each course row is counted once in this total, even if several prefixes overlap.
    return sum(float(c["CFU"]) for c in selected_courses if course_matches_ssd(c["SSD"], allowed))

def assess(selected_courses, rules_for_class):
    results = []
    for _, rule in rules_for_class.iterrows():
        allowed = split_ssd(rule["SSD_ammessi"])
        got = total_cfu_for_rule(selected_courses, allowed)
        need = float(rule["CFU_richiesti"])
        missing = max(0.0, need - got)
        results.append({
            "ID_regola": str(rule["ID_regola"]),
            "Tipo_regola": str(rule["Tipo_regola"]).upper(),
            "Descrizione": str(rule["Descrizione"]),
            "CFU richiesti": need,
            "CFU nel piano": got,
            "CFU mancanti": missing,
            "Esito": "Soddisfatto" if missing <= 0 else "Da completare",
            "SSD_ammessi": str(rule["SSD_ammessi"]),
            "Note": str(rule.get("Note_ambito", "")),
        })
    return pd.DataFrame(results)

def suggestions(courses, results, selected_codes):
    # Simple suggestions only: list courses whose SSD can contribute to at least one unmet rule.
    # This is not a combinatorial/optimal plan solver.
    unmet = results[results["CFU mancanti"] > 0]
    rows = []
    for _, course in courses.iterrows():
        code = str(course["Codice_insegnamento"])
        if code in selected_codes:
            continue
        matched = []
        for _, req in unmet.iterrows():
            if course_matches_ssd(course["SSD"], split_ssd(req["SSD_ammessi"])):
                matched.append(str(req["Descrizione"]))
        if matched:
            rows.append({
                "Nome corso": course["Nome_corso"],
                "CFU": int(course["CFU"]) if float(course["CFU"]).is_integer() else course["CFU"],
                "SSD": course["SSD"],
                "Corso di laurea": course.get("Corso_di_laurea", ""),
                "Può contribuire a": "; ".join(matched[:3]),
                "Codice": code,
            })
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    return out.sort_values(["CFU", "Nome corso"], ascending=[True, True])

st.title("Verifica requisiti delle classi di concorso")
st.caption("Prima versione dimostrativa · dati temporanei nella sessione · non sostituisce una verifica ufficiale")

if not COURSES_FILE.exists() or not RULES_FILE.exists():
    st.error("Non trovo i file Excel richiesti. Metti corsi_list.xlsx e requisiti_ministero.xlsx nella stessa cartella di app.py.")
    st.stop()

try:
    courses = load_courses()
    classes, rules = load_rules()
except Exception as exc:
    st.error(f"Errore nella lettura dei file Excel: {exc}")
    st.stop()

if "selected_courses" not in st.session_state:
    st.session_state.selected_courses = []
if "verified_result" not in st.session_state:
    st.session_state.verified_result = None
if "verified_class" not in st.session_state:
    st.session_state.verified_class = None
if "dirty" not in st.session_state:
    st.session_state.dirty = True

class_rows = classes[classes["Codice_classe"].astype(str).str.strip() != ""]
class_options = {
    f'{row["Codice_classe"]} — {row["Denominazione"]}': str(row["Codice_classe"])
    for _, row in class_rows.iterrows()
}
if not class_options:
    st.warning("Il foglio Classi del file requisiti_ministero.xlsx non contiene classi.")
    st.stop()

labels = list(class_options.keys())
default_label = st.selectbox("Classe di concorso", labels, key="class_label")
class_code = class_options[default_label]
if st.session_state.verified_class != class_code:
    st.session_state.verified_result = None
    st.session_state.dirty = True

st.subheader("Aggiungi esami al piano")
query = st.text_input("Cerca un insegnamento", placeholder="Digita il nome del corso, il codice o l'SSD…")
if query.strip():
    q = query.strip().casefold()
    mask = (
        courses["Nome_corso"].str.casefold().str.contains(q, na=False)
        | courses["Codice_insegnamento"].str.casefold().str.contains(q, na=False)
        | courses["SSD"].str.casefold().str.contains(q, na=False)
        | courses["Corso_di_laurea"].astype(str).str.casefold().str.contains(q, na=False)
    )
    matches = courses[mask]
else:
    matches = courses.iloc[0:0]

if not matches.empty:
    match_labels = {
        f'{r["Nome_corso"]} · {int(r["CFU"]) if float(r["CFU"]).is_integer() else r["CFU"]} CFU · {r["SSD"]} · {r.get("Corso_di_laurea", "")}': str(r["Codice_insegnamento"])
        for _, r in matches.iterrows()
    }
    selected_label = st.selectbox("Suggerimenti", list(match_labels.keys()), key="course_suggestion")
    if st.button("Aggiungi corso selezionato", type="primary"):
        code = match_labels[selected_label]
        existing = {x["Codice_insegnamento"] for x in st.session_state.selected_courses}
        if code in existing:
            st.info("Questo insegnamento è già nella lista.")
        else:
            row = courses[courses["Codice_insegnamento"].astype(str) == code].iloc[0]
            st.session_state.selected_courses.append({
                "Codice_insegnamento": code,
                "Nome_corso": str(row["Nome_corso"]),
                "CFU": float(row["CFU"]),
                "SSD": str(row["SSD"]),
                "Corso_di_laurea": str(row.get("Corso_di_laurea", "")),
                "Sostenuto": False,
            })
            st.session_state.verified_result = None
            st.session_state.dirty = True
            st.rerun()
elif query.strip():
    st.caption("Nessun insegnamento trovato.")

if st.session_state.selected_courses:
    st.subheader("Esami inseriti")
    for i, course in enumerate(list(st.session_state.selected_courses)):
        c1, c2, c3, c4 = st.columns([5, 1, 2, 1])
        c1.write(f'**{course["Nome_corso"]}**')
        c1.caption(f'{course["CFU"]:g} CFU · {course["SSD"]} · {course["Corso_di_laurea"]}')
        status_label = "🟢 Sostenuto" if course["Sostenuto"] else "Pianificato"
        c2.write(status_label)
        if c3.button("🟢 Già sostenuto" if not course["Sostenuto"] else "↩ Pianificato", key=f'toggle_{course["Codice_insegnamento"]}'):
            for item in st.session_state.selected_courses:
                if item["Codice_insegnamento"] == course["Codice_insegnamento"]:
                    item["Sostenuto"] = not item["Sostenuto"]
            st.session_state.verified_result = None
            st.session_state.dirty = True
            st.rerun()
        if c4.button("Rimuovi", key=f'remove_{course["Codice_insegnamento"]}'):
            st.session_state.selected_courses = [x for x in st.session_state.selected_courses if x["Codice_insegnamento"] != course["Codice_insegnamento"]]
            st.session_state.verified_result = None
            st.session_state.dirty = True
            st.rerun()
else:
    st.info("Aggiungi gli esami che vuoi includere nel piano. Possono essere tutti pianificati: la verifica considera sostenuti + pianificati.")

st.divider()
if st.button("Verifica requisiti", type="primary", use_container_width=True):
    active_rules = rules[
        (rules["Codice_classe"].astype(str).str.strip() == class_code)
        & (rules["Attiva"] == "SI")
    ]
    if active_rules.empty:
        st.error("Non ci sono regole attive per questa classe nel foglio Requisiti.")
        st.session_state.verified_result = None
    else:
        st.session_state.verified_result = assess(st.session_state.selected_courses, active_rules)
        st.session_state.verified_class = class_code
        st.session_state.dirty = False

if st.session_state.dirty and st.session_state.verified_result is not None:
    st.warning("Il piano è cambiato dopo l'ultima verifica. Premi di nuovo «Verifica requisiti» per aggiornare i risultati.")

if st.session_state.verified_result is not None and not st.session_state.dirty:
    result = st.session_state.verified_result
    st.subheader(f"Risultato — {class_code}")
    total_rules = len(result)
    satisfied = int((result["CFU mancanti"] <= 0).sum())
    r1, r2 = st.columns(2)
    r1.metric("Vincoli soddisfatti", f"{satisfied}/{total_rules}")
    r2.metric("Vincoli da completare", str(total_rules - satisfied))
    for _, req in result.iterrows():
        need = float(req["CFU richiesti"])
        got = float(req["CFU nel piano"])
        missing = float(req["CFU mancanti"])
        st.write(f'**{req["Descrizione"]}**')
        st.progress(1.0 if need <= 0 else min(1.0, got / need))
        st.caption(f'{got:g}/{need:g} CFU · ' + ("Soddisfatto" if missing <= 0 else f"Mancano {missing:g} CFU"))
    st.subheader("Corsi del catalogo che possono contribuire")
    selected_codes = {x["Codice_insegnamento"] for x in st.session_state.selected_courses}
    suggested = suggestions(courses, result, selected_codes)
    if suggested.empty:
        st.write("Non sono stati trovati corsi non selezionati che corrispondano ai vincoli ancora scoperti.")
    else:
        st.dataframe(suggested.drop(columns=["Codice"]), use_container_width=True, hide_index=True)
    with st.expander("Dettaglio regole e SSD ammessi"):
        st.dataframe(result[["ID_regola", "Tipo_regola", "Descrizione", "CFU richiesti", "CFU nel piano", "CFU mancanti", "SSD_ammessi", "Note"]], use_container_width=True, hide_index=True)

with st.expander("Avvertenza normativa"):
    st.warning(
        "Questa versione verifica la copertura CFU/SSD secondo le righe attive in requisiti_ministero.xlsx. "
        "Non verifica se il titolo di laurea è valido per l'accesso, le eccezioni per specifici titoli o le disposizioni transitorie. "
        "I dati Excel sono una bozza dimostrativa da controllare prima di qualsiasi uso decisionale."
    )
    st.markdown(
        "- DM 255/2023, Tabella A (A-12): https://www.gazzettaufficiale.it/eli/id/2024/02/10/24A00733/SG\n"
        "- DM 259/2017 e DPR 19/2016: consultare le tabelle e le note applicabili al titolo di studio."
    )
