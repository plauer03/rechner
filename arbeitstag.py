import datetime as dt
import re

import pyperclip
import streamlit as st

st.set_page_config(page_title="Arbeitszeitrechner", layout="centered")
st.title("Arbeitszeitrechner")

# ----------------------- Eingabe ---------------------------------
if st.button("Aus Zwischenablage einfügen"):
    st.session_state["data"] = pyperclip.paste()

raw = st.text_area(
    "Buchungen (B1 = Kommen, B2 = Gehen):",
    value=st.session_state.get("data", ""),
    height=200,
)

feierabend_str = st.text_input("Geplanter Feierabend (HH:MM)", "")

# ----------------------- Hilfsfunktionen -------------------------
def parse(text: str):
    """Liest HH:MM und B1/B2, Sekunden ignoriert"""
    pat = re.compile(r"(\d{2}):(\d{2})(?::\d{2})?.*?(B[12])")
    out = []
    for h, m, mark in pat.findall(text):
        ts = dt.datetime.combine(dt.date.today(), dt.time(int(h), int(m)))
        out.append((ts, mark))
    return sorted(out, key=lambda x: x[0])

def analyse(recs, leave_time=None):
    work = dt.timedelta()
    pauses = []
    last_in, last_out = None, None

    for ts, mark in recs:
        if mark == "B1":
            if last_out:
                pauses.append(ts - last_out)
                last_out = None
            last_in = ts
        elif mark == "B2":
            if last_in:
                work += ts - last_in
                last_out = ts
                last_in = None

    # letzter Kommen-Eintrag bis geplanten Feierabend
    if leave_time and last_in and leave_time > last_in:
        work += leave_time - last_in
        last_out = leave_time

    total_pause = sum(pauses, dt.timedelta())
    return work, total_pause, pauses

def gesetzliche_pause(arbeitsdauer: dt.timedelta) -> dt.timedelta:
    if arbeitsdauer > dt.timedelta(hours=9):
        return dt.timedelta(minutes=45)
    elif arbeitsdauer > dt.timedelta(hours=6):
        return dt.timedelta(minutes=30)
    else:
        return dt.timedelta()

def fmt(td: dt.timedelta) -> str:
    mins = int(td.total_seconds() // 60)
    sign = "-" if mins < 0 else "+"
    mins = abs(mins)
    return f"{sign}{mins // 60:02d}:{mins % 60:02d}"

# ----------------------- Berechnung ------------------------------
if raw:
    rec = parse(raw)
    if not rec:
        st.error("Keine gültigen Buchungen erkannt.")
        st.stop()

    # geplante Feierabend‑Zeit
    leave_dt = None
    if feierabend_str:
        h, m = map(int, feierabend_str.split(":"))
        leave_dt = dt.datetime.combine(dt.date.today(), dt.time(h, m))

    # Analysiere realen Tag
    arbeit, pause, pause_liste = analyse(rec, leave_dt)

    # gesetzliche Pause prüfen (nicht anwenden!)
    gesetzl = gesetzliche_pause(arbeit)
    fehl_pause = max(gesetzl - pause, dt.timedelta())

    # Zeitpunkt für 8 h Nettoarbeitszeit
    start = rec[0][0]
    null_zeitpunkt = start + dt.timedelta(hours=8) + pause

    st.subheader("Ergebnisse")
    st.write(f"Arbeitszeit (brutto): {arbeit}")
    st.write(f"Pausenzeit (real): {pause}")
    st.write(f"Gesetzliche Mindestpause: {gesetzl}")

    if fehl_pause > dt.timedelta():
        st.warning(f"Es fehlen {fehl_pause} gesetzliche Pause. Pluszeit zählt erst danach.")

    st.write(f"Zeitpunkt für 0 ± 0 h: {null_zeitpunkt.strftime('%H:%M')}")

    if leave_dt:
        # Rechne korrekt unter Berücksichtigung gesetzl. Pause
        diff = (leave_dt - null_zeitpunkt) - fehl_pause
        st.write(f"Geplanter Feierabend: {leave_dt.strftime('%H:%M')}")
        st.write(f"Plus/Minus: {fmt(diff)}")

    if pause_liste:
        st.write("Einzelne Pausen:")
        for i, p in enumerate(pause_liste, 1):
            st.write(f"- Pause {i}: {p}")
else:
    st.info("Buchungen eingeben oder einfügen und optional Feierabend‑Zeit angeben.")
