# FinTrack — monitorizare cheltuieli familiei / student
# Date salvate in fintrack_data.json (cu hashing)
# Rulare: streamlit run app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
import hashlib
import json
import io
import os
import copy

st.set_page_config(
    page_title="FinTrack",
    page_icon="💰",
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
    --accent-red:   #f87171;
    --accent-green: #4ade80;
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
section[data-testid="stSidebar"] .stRadio label {
    color: var(--text-primary) !important;
}

[data-testid="metric-container"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px 22px !important;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem !important;
    color: var(--accent-gold) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-muted) !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: .08em;
}
[data-testid="stMetricDelta"] svg { display: none; }

.stButton > button {
    background: var(--accent-gold) !important;
    color: #0d0f14 !important;
    font-weight: 600;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 1.4rem !important;
    transition: opacity .2s;
}
.stButton > button:hover { opacity: .85; }

.stTextInput input, .stNumberInput input,
.stSelectbox select, .stDateInput input, .stTextArea textarea {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}

.section-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.6rem;
    color: var(--text-primary);
    margin-bottom: .2rem;
}
.section-sub {
    color: var(--text-muted);
    font-size: .85rem;
    margin-bottom: 1.4rem;
}

.logo-wrap { text-align: center; padding: 1.6rem 0 1rem; }
.logo-text {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: var(--accent-gold);
    letter-spacing: .04em;
}
.logo-sub {
    color: var(--text-muted);
    font-size: .78rem;
    letter-spacing: .12em;
    text-transform: uppercase;
}

.login-card {
    max-width: 420px;
    margin: 5vh auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 2.5rem 2.8rem;
}

.stDataFrame { border-radius: 10px; overflow: hidden; }
hr { border-color: var(--border) !important; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --- storage ---

DB_FILE = "fintrack_data.json"
_EMPTY_DB: dict = {"users": [], "transactions": [], "budgets": []}


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


# --- auth ---

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


def authenticate(username: str, password: str) -> dict | None:
    data = _load()
    pw_hash = hash_password(password)
    for u in data["users"]:
        if u["username"] == username and u["password"] == pw_hash:
            return u
    return None


def create_user(username: str, password: str, full_name: str) -> tuple[bool, str]:
    if len(username) < 3:
        return False, "Username-ul trebuie să aibă cel puțin 3 caractere."
    if len(password) < 4:
        return False, "Parola trebuie să aibă cel puțin 4 caractere."
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


def get_user_by_id(user_id: int) -> dict | None:
    data = _load()
    for u in data["users"]:
        if u["id"] == user_id:
            return u
    return None


def update_user_name(user_id: int, full_name: str) -> None:
    data = _load()
    for u in data["users"]:
        if u["id"] == user_id:
            u["full_name"] = full_name
            break
    _save(data)


def change_password(user_id: int, old_pw: str, new_pw: str) -> tuple[bool, str]:
    data = _load()
    user = next((u for u in data["users"] if u["id"] == user_id), None)
    if not user or user["password"] != hash_password(old_pw):
        return False, "Parola curentă este incorectă."
    if len(new_pw) < 4:
        return False, "Parola nouă trebuie să aibă cel puțin 4 caractere."
    user["password"] = hash_password(new_pw)
    _save(data)
    return True, "Parola a fost schimbată."


# --- categorii ---

EXPENSE_CATEGORIES = [
    "Mâncare", "Chirie/Locuință", "Transport", "Utilități",
    "Sănătate", "Educație", "Divertisment", "Îmbrăcăminte",
    "Electronice", "Sport & Fitness", "Călătorii", "Cadouri",
    "Economii/Investiții", "Altele",
]

INCOME_CATEGORIES = [
    "Salariu", "Freelance", "Bursă", "Dividende",
    "Chirie Primită", "Cadou Primit", "Rambursare", "Altele",
]


# --- tranzactii ---

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


def delete_transaction(txn_id: int, user_id: int) -> None:
    data = _load()
    data["transactions"] = [
        t for t in data["transactions"]
        if not (t["id"] == txn_id and t["user_id"] == user_id)
    ]
    _save(data)


def delete_all_transactions(user_id: int) -> None:
    data = _load()
    data["transactions"] = [t for t in data["transactions"] if t["user_id"] != user_id]
    _save(data)


def get_transactions(user_id: int) -> pd.DataFrame:
    data = _load()
    rows = [t for t in data["transactions"] if t["user_id"] == user_id]
    if not rows:
        return pd.DataFrame(columns=["id", "user_id", "type", "amount",
                                     "category", "txn_date", "description", "created_at"])
    df = pd.DataFrame(rows)
    return df.sort_values(["txn_date", "id"], ascending=[False, False]).reset_index(drop=True)


def get_transactions_month(user_id: int, month: str) -> pd.DataFrame:
    df = get_transactions(user_id)
    if df.empty:
        return df
    return df[df["txn_date"].str.startswith(month)].reset_index(drop=True)


# --- bugete ---

def set_budget(user_id: int, category: str, month: str, limit_amt: float) -> None:
    data = _load()
    existing = next(
        (b for b in data["budgets"]
         if b["user_id"] == user_id and b["category"] == category and b["month"] == month),
        None,
    )
    if existing:
        existing["limit_amt"] = round(limit_amt, 2)
    else:
        data["budgets"].append({
            "id": _next_id(data["budgets"]),
            "user_id": user_id,
            "category": category,
            "month": month,
            "limit_amt": round(limit_amt, 2),
        })
    _save(data)


def delete_budget(budget_id: int, user_id: int) -> None:
    data = _load()
    data["budgets"] = [
        b for b in data["budgets"]
        if not (b["id"] == budget_id and b["user_id"] == user_id)
    ]
    _save(data)


def delete_all_budgets(user_id: int) -> None:
    data = _load()
    data["budgets"] = [b for b in data["budgets"] if b["user_id"] != user_id]
    _save(data)


def get_budgets(user_id: int, month: str) -> pd.DataFrame:
    data = _load()
    rows = [b for b in data["budgets"] if b["user_id"] == user_id and b["month"] == month]
    if not rows:
        return pd.DataFrame(columns=["id", "user_id", "category", "month", "limit_amt"])
    return pd.DataFrame(rows)


def get_all_budgets(user_id: int) -> pd.DataFrame:
    data = _load()
    rows = [b for b in data["budgets"] if b["user_id"] == user_id]
    if not rows:
        return pd.DataFrame(columns=["id", "user_id", "category", "month", "limit_amt"])
    df = pd.DataFrame(rows)
    return df.sort_values(["month", "category"], ascending=[False, True]).reset_index(drop=True)


def compute_budget_status(user_id: int, month: str) -> pd.DataFrame:
    budgets = get_budgets(user_id, month)
    if budgets.empty:
        return pd.DataFrame()
    txns = get_transactions_month(user_id, month)
    expenses = txns[txns["type"] == "Cheltuială"] if not txns.empty else pd.DataFrame()
    rows = []
    for _, b in budgets.iterrows():
        spent = 0.0
        if not expenses.empty:
            spent = expenses.loc[expenses["category"] == b["category"], "amount"].sum()
        pct = (spent / b["limit_amt"] * 100) if b["limit_amt"] > 0 else 0
        rows.append({
            "id": b["id"],
            "Categorie": b["category"],
            "Buget (RON)": b["limit_amt"],
            "Cheltuit (RON)": round(spent, 2),
            "Rămas (RON)": round(b["limit_amt"] - spent, 2),
            "% utilizat": round(pct, 1),
            "Depășit": spent > b["limit_amt"],
        })
    return pd.DataFrame(rows)


# --- grafice ---

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#f0ede8"),
    margin=dict(t=40, b=20, l=20, r=20),
)

GOLD_PALETTE = [
    "#c9a84c", "#2dd4bf", "#f87171", "#4ade80",
    "#818cf8", "#fb923c", "#e879f9", "#38bdf8",
    "#a3e635", "#fbbf24", "#f472b6", "#34d399",
    "#60a5fa", "#c084fc",
]


def pie_chart_expenses(df: pd.DataFrame) -> go.Figure:
    grp = (
        df[df["type"] == "Cheltuială"]
        .groupby("category")["amount"].sum()
        .reset_index()
    ) if not df.empty else pd.DataFrame()
    if grp is None or grp.empty:
        fig = go.Figure()
        fig.add_annotation(text="Nu există cheltuieli", x=0.5, y=0.5,
                           showarrow=False, font=dict(color="#8a8fa8", size=14))
        fig.update_layout(**PLOTLY_LAYOUT)
        return fig
    fig = px.pie(grp, values="amount", names="category",
                 color_discrete_sequence=GOLD_PALETTE, hole=0.45)
    fig.update_traces(textfont_size=12, textfont_color="#f0ede8")
    fig.update_layout(**PLOTLY_LAYOUT,
                      legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=11)))
    return fig


def bar_monthly(user_id: int, months: int = 6) -> go.Figure:
    df = get_transactions(user_id)
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Nu există date", x=0.5, y=0.5,
                           showarrow=False, font=dict(color="#8a8fa8", size=14))
        fig.update_layout(**PLOTLY_LAYOUT)
        return fig
    df["month"] = df["txn_date"].str[:7]
    grp = df.groupby(["month", "type"])["amount"].sum().reset_index()
    pivot = grp.pivot(index="month", columns="type", values="amount").fillna(0).tail(months).reset_index()
    fig = go.Figure()
    if "Venit" in pivot.columns:
        fig.add_trace(go.Bar(name="Venituri", x=pivot["month"],
                             y=pivot["Venit"], marker_color="#4ade80"))
    if "Cheltuială" in pivot.columns:
        fig.add_trace(go.Bar(name="Cheltuieli", x=pivot["month"],
                             y=pivot["Cheltuială"], marker_color="#f87171"))
    fig.update_layout(**PLOTLY_LAYOUT, barmode="group",
                      xaxis=dict(showgrid=False),
                      yaxis=dict(showgrid=True, gridcolor="#2a2f42"),
                      legend=dict(orientation="h", y=-0.15))
    return fig


def line_balance(user_id: int) -> go.Figure:
    df = get_transactions(user_id)
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Nu există date", x=0.5, y=0.5,
                           showarrow=False, font=dict(color="#8a8fa8", size=14))
        fig.update_layout(**PLOTLY_LAYOUT)
        return fig
    df = df.sort_values(["txn_date", "id"]).reset_index(drop=True)
    df["signed"] = df.apply(
        lambda r: r["amount"] if r["type"] == "Venit" else -r["amount"], axis=1
    )
    df["balance"] = df["signed"].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["txn_date"], y=df["balance"], mode="lines",
        line=dict(color="#c9a84c", width=2.5),
        fill="tozeroy", fillcolor="rgba(201,168,76,0.08)", name="Sold",
    ))
    fig.update_layout(**PLOTLY_LAYOUT,
                      xaxis=dict(showgrid=False),
                      yaxis=dict(showgrid=True, gridcolor="#2a2f42"))
    return fig


def bar_budget_status(status_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Cheltuit", x=status_df["Categorie"], y=status_df["Cheltuit (RON)"],
        marker_color=["#f87171" if d else "#4ade80" for d in status_df["Depășit"]],
    ))
    fig.add_trace(go.Bar(
        name="Buget", x=status_df["Categorie"], y=status_df["Buget (RON)"],
        marker_color="rgba(201,168,76,0.35)",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, barmode="overlay",
                      xaxis=dict(showgrid=False),
                      yaxis=dict(showgrid=True, gridcolor="#2a2f42"),
                      legend=dict(orientation="h", y=-0.2))
    return fig


# --- session state ---

def is_logged_in() -> bool:
    return st.session_state.get("user_id") is not None


def login_user(user: dict) -> None:
    st.session_state["user_id"] = user["id"]
    st.session_state["username"] = user["username"]
    st.session_state["full_name"] = user["full_name"]


def logout_user() -> None:
    for k in ["user_id", "username", "full_name"]:
        st.session_state.pop(k, None)


# --- pagini UI ---

def page_login() -> None:
    st.markdown(
        "<div class='login-card'>"
        "<div style='text-align:center;margin-bottom:1.8rem'>"
        "<div class='logo-text'>💰 FinTrack</div>"
        "<div class='logo-sub'>Monitorizare cheltuieli</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["🔑 Autentificare", "📝 Cont nou"])

    with tab_login:
        st.write("")
        username = st.text_input("Username", key="li_user", placeholder="admin")
        password = st.text_input("Parolă", type="password", key="li_pass", placeholder="••••")
        if st.button("Intră în cont", key="btn_login", use_container_width=True):
            if not username or not password:
                st.error("Completează toate câmpurile.")
            else:
                user = authenticate(username, password)
                if user:
                    login_user(user)
                    st.success(f"Bun venit, {user['full_name'] or user['username']}!")
                    st.rerun()
                else:
                    st.error("Username sau parolă incorectă.")
        st.caption("Cont implicit: **admin** / **admin**")

    with tab_register:
        st.write("")
        fn = st.text_input("Nume complet", key="reg_fn", placeholder="Ana Popescu")
        un = st.text_input("Username", key="reg_un", placeholder="ana_popescu")
        pw1 = st.text_input("Parolă", type="password", key="reg_p1")
        pw2 = st.text_input("Confirmă parola", type="password", key="reg_p2")
        if st.button("Creează cont", key="btn_register", use_container_width=True):
            if not fn or not un or not pw1 or not pw2:
                st.error("Completează toate câmpurile.")
            elif pw1 != pw2:
                st.error("Parolele nu coincid.")
            else:
                ok, msg = create_user(un, pw1, fn)
                if ok:
                    st.success(msg + " Autentifică-te.")
                else:
                    st.error(msg)

    st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            "<div class='logo-wrap'>"
            "<div class='logo-text'>💰 FinTrack</div>"
            "<div class='logo-sub'>Monitorizare cheltuieli</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        fn = st.session_state.get("full_name") or st.session_state.get("username", "")
        st.markdown(
            f"<div style='color:#8a8fa8;font-size:.8rem;text-align:center;margin-bottom:1rem'>"
            f"Conectat ca<br><b style='color:#f0ede8'>{fn}</b></div>",
            unsafe_allow_html=True,
        )
        nav = st.radio(
            "Navigare",
            ["📊 Dashboard", "➕ Tranzacție nouă", "📋 Istoricul tranzacțiilor",
             "🎯 Bugete", "📤 Export Raport", "⚙️ Setări cont"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        if st.button("🚪 Deconectare", use_container_width=True):
            logout_user()
            st.rerun()
    return nav


def page_dashboard() -> None:
    uid = st.session_state["user_id"]
    today = date.today()
    cur_month = today.strftime("%Y-%m")

    st.markdown("<div class='section-title'>📊 Dashboard</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='section-sub'>Rezumat financiar — {today.strftime('%B %Y')}</div>",
        unsafe_allow_html=True,
    )

    all_df = get_transactions(uid)
    month_df = get_transactions_month(uid, cur_month)

    total_in  = all_df.loc[all_df["type"] == "Venit", "amount"].sum() if not all_df.empty else 0.0
    total_out = all_df.loc[all_df["type"] == "Cheltuială", "amount"].sum() if not all_df.empty else 0.0
    month_in  = month_df.loc[month_df["type"] == "Venit", "amount"].sum() if not month_df.empty else 0.0
    month_out = month_df.loc[month_df["type"] == "Cheltuială", "amount"].sum() if not month_df.empty else 0.0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💼 Sold total (RON)", f"{total_in - total_out:,.2f}")
    k2.metric("📅 Venituri luna curentă (RON)", f"{month_in:,.2f}")
    k3.metric("📅 Cheltuieli luna curentă (RON)", f"{month_out:,.2f}")
    k4.metric("📅 Sold lunar (RON)", f"{month_in - month_out:,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    status_df = compute_budget_status(uid, cur_month)
    if not status_df.empty:
        for _, row in status_df[status_df["Depășit"]].iterrows():
            st.error(
                f"⚠️ **{row['Categorie']}**: buget depășit! "
                f"Cheltuit {row['Cheltuit (RON)']:,.2f} RON din {row['Buget (RON)']:,.2f} RON "
                f"({row['% utilizat']}%)"
            )
        near = status_df[(status_df["% utilizat"] >= 80) & (~status_df["Depășit"])]
        for _, row in near.iterrows():
            st.warning(
                f"🔔 **{row['Categorie']}**: aproape de limită — "
                f"{row['% utilizat']}% utilizat "
                f"({row['Cheltuit (RON)']:,.2f} / {row['Buget (RON)']:,.2f} RON)"
            )

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Distribuția cheltuielilor (luna curentă)")
        st.plotly_chart(pie_chart_expenses(month_df), use_container_width=True, key="pie")
    with c2:
        st.subheader("Venituri vs Cheltuieli (ultimele 6 luni)")
        st.plotly_chart(bar_monthly(uid), use_container_width=True, key="bar_monthly")

    st.subheader("Evoluția soldului în timp")
    st.plotly_chart(line_balance(uid), use_container_width=True, key="line_bal")

    if not status_df.empty:
        st.subheader("Status bugete — luna curentă")
        st.plotly_chart(bar_budget_status(status_df), use_container_width=True, key="bar_budget")

    st.subheader("Ultimele 10 tranzacții")
    if all_df.empty:
        st.info("Nu există tranzacții înregistrate încă.")
    else:
        disp = all_df.head(10)[["txn_date", "type", "category", "amount", "description"]].copy()
        disp.columns = ["Data", "Tip", "Categorie", "Sumă (RON)", "Descriere"]
        disp["Sumă (RON)"] = disp["Sumă (RON)"].apply(lambda x: f"{x:.2f}")
        st.dataframe(
            disp.style.map(
                lambda v: "color:#4ade80" if v == "Venit" else ("color:#f87171" if v == "Cheltuială" else ""),
                subset=["Tip"],
            ),
            use_container_width=True, hide_index=True,
        )


def page_add_transaction() -> None:
    uid = st.session_state["user_id"]
    st.markdown("<div class='section-title'>➕ Tranzacție nouă</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Adaugă un venit sau o cheltuială</div>", unsafe_allow_html=True)

    # selectbox-ul de tip trebuie sa fie in afara formului ca sa
    # actualizeze lista de categorii inainte de submit
    col_pre, _ = st.columns([1, 1])
    with col_pre:
        txn_type = st.selectbox("Tip tranzacție *", ["Cheltuială", "Venit"], key="txn_type_selector")

    cats = EXPENSE_CATEGORIES if txn_type == "Cheltuială" else INCOME_CATEGORIES

    with st.form("form_add_txn", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Categorie *", cats)
        with col2:
            txn_date = st.date_input("Data *", value=date.today(), max_value=date.today())

        col3, _ = st.columns([1, 1])
        with col3:
            amount_str = st.text_input("Sumă (RON) *", placeholder="ex: 250.50")

        description = st.text_area("Descriere (opțional)",
                                   placeholder="ex: Cumpărături Kaufland", height=80)
        submitted = st.form_submit_button("💾 Salvează tranzacția", use_container_width=True)

    if submitted:
        try:
            amount = float(amount_str.replace(",", ".").strip())
            if amount <= 0:
                raise ValueError
        except (ValueError, AttributeError):
            st.error("❌ Suma introdusă nu este validă. Introdu un număr pozitiv (ex: 150 sau 89.99).")
            return
        add_transaction(uid, txn_type, amount, category,
                        txn_date.strftime("%Y-%m-%d"), description.strip())
        st.success(f"✅ Tranzacție salvată: {txn_type} — {amount:.2f} RON — {category}")
        st.balloons()


def page_history() -> None:
    uid = st.session_state["user_id"]
    st.markdown("<div class='section-title'>📋 Istoricul tranzacțiilor</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Vizualizează, filtrează și șterge tranzacții</div>",
                unsafe_allow_html=True)

    df = get_transactions(uid)
    if df.empty:
        st.info("Nu există tranzacții înregistrate.")
        return

    f1, f2, f3 = st.columns(3)
    with f1:
        ftype = st.selectbox("Tip", ["Toate", "Venit", "Cheltuială"], key="flt_type")
    with f2:
        months_avail = sorted(df["txn_date"].str[:7].unique().tolist(), reverse=True)
        fmonth = st.selectbox("Luna", ["Toate"] + months_avail, key="flt_month")
    with f3:
        all_cats = sorted(df["category"].unique().tolist())
        fcat = st.selectbox("Categorie", ["Toate"] + all_cats, key="flt_cat")

    filtered = df.copy()
    if ftype != "Toate":
        filtered = filtered[filtered["type"] == ftype]
    if fmonth != "Toate":
        filtered = filtered[filtered["txn_date"].str.startswith(fmonth)]
    if fcat != "Toate":
        filtered = filtered[filtered["category"] == fcat]

    st.markdown(
        f"<div style='color:#8a8fa8;font-size:.85rem;margin-bottom:.5rem'>"
        f"{len(filtered)} tranzacții afișate</div>",
        unsafe_allow_html=True,
    )

    disp = filtered[["id", "txn_date", "type", "category", "amount", "description"]].copy()
    disp.columns = ["ID", "Data", "Tip", "Categorie", "Sumă (RON)", "Descriere"]
    disp["Sumă (RON)"] = disp["Sumă (RON)"].apply(lambda x: f"{x:.2f}")

    st.dataframe(
        disp.style.map(
            lambda v: "color:#4ade80" if v == "Venit" else ("color:#f87171" if v == "Cheltuială" else ""),
            subset=["Tip"],
        ),
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    st.subheader("Șterge o tranzacție")
    ids_available = filtered["id"].tolist()
    if ids_available:
        del_id = st.number_input(
            "Introdu ID-ul tranzacției de șters",
            min_value=1, step=1, value=int(ids_available[0]),
            key="del_id_inp",
        )
        if st.button("🗑️ Șterge tranzacția", key="btn_del_txn"):
            if int(del_id) in ids_available:
                delete_transaction(int(del_id), uid)
                st.success(f"Tranzacția #{int(del_id)} a fost ștearsă.")
                st.rerun()
            else:
                st.error("ID-ul nu corespunde niciunei tranzacții afișate.")
    else:
        st.info("Nu există tranzacții de șters cu filtrele selectate.")


def page_budgets() -> None:
    uid = st.session_state["user_id"]
    st.markdown("<div class='section-title'>🎯 Bugete lunare</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Setează limite de cheltuieli pe categorie</div>",
                unsafe_allow_html=True)

    today = date.today()
    with st.form("form_budget", clear_on_submit=True):
        b1, b2, b3 = st.columns(3)
        with b1:
            b_cat = st.selectbox("Categorie", EXPENSE_CATEGORIES, key="bcat")
        with b2:
            b_month = st.text_input("Luna (YYYY-MM)", value=today.strftime("%Y-%m"), key="bmonth")
        with b3:
            b_limit_str = st.text_input("Limită (RON)", placeholder="ex: 500", key="blimit")
        b_submit = st.form_submit_button("💾 Salvează buget", use_container_width=True)

    if b_submit:
        try:
            datetime.strptime(b_month.strip(), "%Y-%m")
        except ValueError:
            st.error("❌ Format lună invalid. Folosește YYYY-MM (ex: 2024-03).")
            return
        try:
            b_limit = float(b_limit_str.replace(",", ".").strip())
            if b_limit <= 0:
                raise ValueError
        except (ValueError, AttributeError):
            st.error("❌ Limita nu este validă. Introdu un număr pozitiv.")
            return
        set_budget(uid, b_cat, b_month.strip(), b_limit)
        st.success(f"✅ Buget setat: {b_cat} — {b_month.strip()} — {b_limit:.2f} RON")
        st.rerun()

    st.markdown("---")

    cur_month = today.strftime("%Y-%m")
    st.subheader(f"Status bugete — {cur_month}")
    status_df = compute_budget_status(uid, cur_month)
    if status_df.empty:
        st.info("Nu există bugete setate pentru luna curentă.")
    else:
        for _, row in status_df.iterrows():
            color = "#f87171" if row["Depășit"] else ("#c9a84c" if row["% utilizat"] >= 80 else "#4ade80")
            pct_clamped = min(row["% utilizat"], 100)
            st.markdown(
                f"""
                <div style='background:#161921;border:1px solid #2a2f42;border-radius:12px;
                            padding:14px 18px;margin-bottom:10px'>
                  <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>
                    <b style='font-size:1rem'>{row['Categorie']}</b>
                    <span style='color:{color};font-weight:600'>{row['% utilizat']}%</span>
                  </div>
                  <div style='background:#2a2f42;border-radius:6px;height:8px;margin-bottom:8px'>
                    <div style='background:{color};width:{pct_clamped}%;height:8px;border-radius:6px'></div>
                  </div>
                  <div style='display:flex;justify-content:space-between;font-size:.82rem;color:#8a8fa8'>
                    <span>Cheltuit: <b style='color:#f0ede8'>{row['Cheltuit (RON)']:,.2f} RON</b></span>
                    <span>Buget: <b style='color:#f0ede8'>{row['Buget (RON)']:,.2f} RON</b></span>
                    <span>Rămas: <b style='color:{color}'>{row['Rămas (RON)']:,.2f} RON</b></span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.subheader("Toate bugetele")
    all_budgets = get_all_budgets(uid)
    if all_budgets.empty:
        st.info("Nu există bugete înregistrate.")
    else:
        disp = all_budgets[["id", "category", "month", "limit_amt"]].copy()
        disp.columns = ["ID", "Categorie", "Luna", "Limită (RON)"]
        disp["Limită (RON)"] = disp["Limită (RON)"].apply(lambda x: f"{x:.2f}")
        st.dataframe(disp, use_container_width=True, hide_index=True)

        del_bid = st.number_input(
            "ID buget de șters", min_value=1, step=1,
            value=int(all_budgets["id"].iloc[0]), key="del_bid",
        )
        if st.button("🗑️ Șterge buget", key="btn_del_budget"):
            ids = all_budgets["id"].tolist()
            if int(del_bid) in ids:
                delete_budget(int(del_bid), uid)
                st.success(f"Bugetul #{int(del_bid)} a fost șters.")
                st.rerun()
            else:
                st.error("ID invalid.")


def page_export() -> None:
    uid = st.session_state["user_id"]
    st.markdown("<div class='section-title'>📤 Export Raport</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Descarcă tranzacțiile în format CSV</div>",
                unsafe_allow_html=True)

    today = date.today()
    exp_month = st.text_input("Luna de exportat (YYYY-MM)", value=today.strftime("%Y-%m"),
                               key="exp_month")

    try:
        datetime.strptime(exp_month.strip(), "%Y-%m")
        valid_month = True
    except ValueError:
        valid_month = False
        st.error("❌ Format invalid. Folosește YYYY-MM.")

    if valid_month:
        df = get_transactions_month(uid, exp_month.strip())
        if df.empty:
            st.warning(f"Nu există tranzacții pentru luna {exp_month}.")
        else:
            st.success(f"✅ {len(df)} tranzacții găsite pentru {exp_month}")
            disp = df[["txn_date", "type", "category", "amount", "description"]].copy()
            disp.columns = ["Data", "Tip", "Categorie", "Suma (RON)", "Descriere"]
            disp["Suma (RON)"] = disp["Suma (RON)"].apply(lambda x: f"{x:.2f}")
            st.dataframe(disp, use_container_width=True, hide_index=True)

            csv_buf = io.StringIO()
            disp.to_csv(csv_buf, index=False, encoding="utf-8-sig")
            st.download_button(
                label="⬇️ Descarcă CSV",
                data=csv_buf.getvalue().encode("utf-8-sig"),
                file_name=f"fintrack_{exp_month}_{st.session_state['username']}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.markdown("---")
            st.subheader("Sumar luna exportată")
            c1, c2, c3 = st.columns(3)
            t_in  = df[df["type"] == "Venit"]["amount"].sum()
            t_out = df[df["type"] == "Cheltuială"]["amount"].sum()
            c1.metric("Venituri (RON)", f"{t_in:,.2f}")
            c2.metric("Cheltuieli (RON)", f"{t_out:,.2f}")
            c3.metric("Sold net (RON)", f"{t_in - t_out:,.2f}")


def page_settings() -> None:
    uid = st.session_state["user_id"]
    st.markdown("<div class='section-title'>⚙️ Setări cont</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Gestionează profilul și securitatea</div>",
                unsafe_allow_html=True)

    user = get_user_by_id(uid)
    if not user:
        st.error("Utilizatorul nu a fost găsit.")
        return

    st.subheader("Informații cont")
    st.markdown(
        f"""
        <div style='background:#161921;border:1px solid #2a2f42;border-radius:12px;
                    padding:20px;margin-bottom:1rem'>
          <div><span style='color:#8a8fa8;font-size:.82rem'>USERNAME</span><br>
               <b>{user['username']}</b></div>
          <hr style='border-color:#2a2f42;margin:12px 0'>
          <div><span style='color:#8a8fa8;font-size:.82rem'>NUME COMPLET</span><br>
               <b>{user['full_name'] or '—'}</b></div>
          <hr style='border-color:#2a2f42;margin:12px 0'>
          <div><span style='color:#8a8fa8;font-size:.82rem'>CONT CREAT LA</span><br>
               <b>{user['created_at'][:10]}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Actualizează numele")
    new_name = st.text_input("Nume complet nou", value=user["full_name"] or "", key="new_name")
    if st.button("💾 Salvează numele", key="btn_save_name"):
        if new_name.strip():
            update_user_name(uid, new_name.strip())
            st.session_state["full_name"] = new_name.strip()
            st.success("✅ Numele a fost actualizat.")
            st.rerun()
        else:
            st.error("Introdu un nume valid.")

    st.markdown("---")

    st.subheader("Schimbă parola")
    old_pw  = st.text_input("Parola curentă",      type="password", key="s_old_pw")
    new_pw  = st.text_input("Parola nouă",          type="password", key="s_new_pw")
    conf_pw = st.text_input("Confirmă parola nouă", type="password", key="s_conf_pw")
    if st.button("🔐 Schimbă parola", key="btn_change_pw"):
        if not old_pw or not new_pw or not conf_pw:
            st.error("Completează toate câmpurile.")
        elif new_pw != conf_pw:
            st.error("Parolele noi nu coincid.")
        else:
            ok, msg = change_password(uid, old_pw, new_pw)
            st.success(msg) if ok else st.error(msg)

    st.markdown("---")

    with st.expander("⚠️ Zona periculoasă"):
        st.warning("Atenție: acțiunile de mai jos sunt ireversibile!")
        if st.button("🗑️ Șterge TOATE tranzacțiile mele", key="btn_del_all"):
            delete_all_transactions(uid)
            st.success("Toate tranzacțiile au fost șterse.")
        if st.button("🗑️ Șterge TOATE bugetele mele", key="btn_del_all_budg"):
            delete_all_budgets(uid)
            st.success("Toate bugetele au fost șterse.")


def main() -> None:
    init_db()

    if not is_logged_in():
        page_login()
        return

    nav = render_sidebar()

    if nav == "📊 Dashboard":
        page_dashboard()
    elif nav == "➕ Tranzacție nouă":
        page_add_transaction()
    elif nav == "📋 Istoricul tranzacțiilor":
        page_history()
    elif nav == "🎯 Bugete":
        page_budgets()
    elif nav == "📤 Export Raport":
        page_export()
    elif nav == "⚙️ Setări cont":
        page_settings()


if __name__ == "__main__":
    main()
