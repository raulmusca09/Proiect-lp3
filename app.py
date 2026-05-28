

import streamlit as st
import pandas as pd
from datetime import date, datetime
import hashlib
import json
import os
import copy

# ─────────────────────────────────────────────
# CONFIG & STYLING
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="FinTrack",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg-dark:      #0d0f14;
    --bg-card:      #161921;
    --bg-input:     #1e2330;
    --accent-gold:  #c9a84c;
    --text-primary: #f0ede8;
    --text-muted:   #8a8fa8;
    --border:       #2a2f42;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg-dark);
    color: var(--text-primary);
}

section[data-testid="stSidebar"] {
    background: var(--bg-card);
    border-right: 1px solid var(--border);
}

.stButton > button {
    background: var(--accent-gold) !important;
    color: #0d0f14 !important;
    font-weight: 600;
    border: none !important;
    border-radius: 8px !important;
}

.login-card {
    max-width: 420px;
    margin: 5vh auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 2.5rem 2.8rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# JSON "DATABASE" LAYER
# ─────────────────────────────────────────────

DB_FILE = "fintrack_data_wip.json"
_EMPTY_DB: dict = {"users": [], "transactions": []}

def _load() -> dict:
    if not os.path.exists(DB_FILE):
        return copy.deepcopy(_EMPTY_DB)
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key in _EMPTY_DB:
            data.setdefault(key, [])
        return data
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(_EMPTY_DB)

def _save(data: dict) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _next_id(records: list) -> int:
    return max((r["id"] for r in records), default=0) + 1

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db() -> None:
    data = _load()
    if not any(u["username"] == "admin" for u in data["users"]):
        data["users"].append({
            "id": _next_id(data["users"]),
            "username": "admin",
            "password": hash_password("admin"),
            "full_name": "Administrator",
            "created_at": date.today().isoformat(),
        })
        _save(data)

# ─────────────────────────────────────────────
# AUTH & USER MANAGEMENT
# ─────────────────────────────────────────────

def authenticate(username: str, password: str) -> dict | None:
    data = _load()
    pw_hash = hash_password(password)
    for u in data["users"]:
        if u["username"] == username and u["password"] == pw_hash:
            return u
    return None

def create_user(username: str, password: str, full_name: str) -> tuple[bool, str]:
    data = _load()
    if any(u["username"] == username for u in data["users"]):
        return False, "Username-ul există deja."
    data["users"].append({
        "id": _next_id(data["users"]),
        "username": username,
        "password": hash_password(password),
        "full_name": full_name,
        "created_at": date.today().isoformat(),
    })
    _save(data)
    return True, "Cont creat cu succes!"

# ─────────────────────────────────────────────
# TRANZACTII
# ─────────────────────────────────────────────

EXPENSE_CATEGORIES = ["Mâncare", "Chirie/Locuință", "Transport", "Utilități", "Altele"]
INCOME_CATEGORIES = ["Salariu", "Freelance", "Cadou Primit", "Altele"]

def add_transaction(user_id: int, txn_type: str, amount: float,
                    category: str, txn_date: str, description: str) -> None:
    data = _load()
    data["transactions"].append({
        "id": _next_id(data["transactions"]),
        "user_id": user_id,
        "type": txn_type,
        "amount": round(amount, 2),
        "category": category,
        "txn_date": txn_date,
        "description": description,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    _save(data)

def get_transactions(user_id: int) -> pd.DataFrame:
    data = _load()
    rows = [t for t in data["transactions"] if t["user_id"] == user_id]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.sort_values(["txn_date", "id"], ascending=[False, False]).reset_index(drop=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────

def is_logged_in() -> bool:
    return st.session_state.get("user_id") is not None

def login_user(user: dict) -> None:
    st.session_state["user_id"] = user["id"]
    st.session_state["username"] = user["username"]
    st.session_state["full_name"] = user["full_name"]

def logout_user() -> None:
    for k in ["user_id", "username", "full_name"]:
        st.session_state.pop(k, None)

# ─────────────────────────────────────────────
# UI PAGES
# ─────────────────────────────────────────────

def page_login() -> None:
    st.markdown("<div class='login-card'><h3>FinTrack LOGIN</h3>", unsafe_allow_html=True)
    tab_login, tab_register = st.tabs(["Autentificare", "Cont nou"])

    with tab_login:
        username = st.text_input("Username", key="li_user", placeholder="admin")
        password = st.text_input("Parolă", type="password", key="li_pass")
        if st.button("Intră în cont", key="btn_login", use_container_width=True):
            user = authenticate(username, password)
            if user:
                login_user(user)
                st.rerun()
            else:
                st.error("Credențiale incorecte.")

    with tab_register:
        fn = st.text_input("Nume complet", key="reg_fn")
        un = st.text_input("Username", key="reg_un")
        pw1 = st.text_input("Parolă", type="password", key="reg_p1")
        if st.button("Creează cont", key="btn_register"):
            ok, msg = create_user(un, pw1, fn)
            st.success(msg) if ok else st.error(msg)
    st.markdown("</div>", unsafe_allow_html=True)

def render_sidebar() -> str:
    with st.sidebar:
        st.title("FinTrack")
        st.markdown(f"Salut, **{st.session_state.get('username')}**!")
        nav = st.radio("Meniu", ["Dashboard", "Adaugă Tranzacție", "Istoric", "Bugete", "Export", "Setări"])
        if st.button("Deconectare"):
            logout_user()
            st.rerun()
    return nav

def page_dashboard() -> None:
    st.title("Dashboard")
    uid = st.session_state["user_id"]
    df = get_transactions(uid)
    
    if df.empty:
        st.info("Nu ai tranzacții înregistrate.")
        return

    total_in = df[df["type"] == "Venit"]["amount"].sum()
    total_out = df[df["type"] == "Cheltuială"]["amount"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Venituri Totale", f"{total_in} RON")
    c2.metric("Cheltuieli Totale", f"{total_out} RON")
    c3.metric("Sold Curent", f"{total_in - total_out} RON")

def page_add_transaction() -> None:
    st.title("Tranzacție nouă")
    uid = st.session_state["user_id"]
    
    txn_type = st.selectbox("Tip", ["Cheltuială", "Venit"])
    cats = EXPENSE_CATEGORIES if txn_type == "Cheltuială" else INCOME_CATEGORIES
    
    with st.form("form_add"):
        category = st.selectbox("Categorie", cats)
        amount_str = st.text_input("Suma (RON)")
        description = st.text_area("Descriere")
        submitted = st.form_submit_button("Salvează")
        
        if submitted:
            try:
                amount = float(amount_str)
                add_transaction(uid, txn_type, amount, category, str(date.today()), description)
                st.success("Tranzacție salvată!")
            except ValueError:
                st.error("Suma trebuie să fie un număr valid.")

def page_history() -> None:
    st.title("Istoric Tranzacții")

def page_budgets() -> None:
    st.title("Bugete Lunare")

def page_export() -> None:
    st.title("Export Raport")

def page_settings() -> None:
    st.title("Setări")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main() -> None:
    init_db()
    if not is_logged_in():
        page_login()
        return

    nav = render_sidebar()

    if nav == "Dashboard":
        page_dashboard()
    elif nav == "Adaugă Tranzacție":
        page_add_transaction()
    elif nav == "Istoric":
        page_history()
    elif nav == "Bugete":
        page_budgets()
    elif nav == "Export":
        page_export()
    elif nav == "Setări":
        page_settings()

if __name__ == "__main__":
    main()