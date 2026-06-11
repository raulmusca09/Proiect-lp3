import streamlit as st
import pandas as pd
import json
import os
import hashlib
from datetime import date

DB_FILE = "fintrack_data.json"
st.set_page_config(page_title="FinTrack", layout="wide")

#TEMA & FONT
PREMIUM_THEME = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'Montserrat', sans-serif !important; }
.stApp { background-color: #0B1120; color: #F8FAFC; }
h1, h2, h3 { font-weight: 600 !important; letter-spacing: -0.5px; }
.stButton > button { background-color: #3B82F6; color: #FFFFFF; border: none; border-radius: 8px; font-weight: 600; width: 100%; transition: all 0.3s ease; }
.stButton > button:hover { background-color: #2563EB; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
[data-testid="metric-container"] { background-color: #1E293B; padding: 20px; border-radius: 12px; border: 1px solid #334155; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] { background-color: #0F172A !important; color: white !important; border-radius: 6px; }
</style>
"""
st.markdown(PREMIUM_THEME, unsafe_allow_html=True)

#  BAZA DE DATE 
def load_db():
    if not os.path.exists(DB_FILE): 
        return {"users": [{"id": 1, "username": "admin", "password": hash_pw("admin")}], "transactions": [], "budgets": []}
    return json.load(open(DB_FILE, "r"))

def save_db(data): json.dump(data, open(DB_FILE, "w"), indent=2)
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()
def get_id(lst): return max((x["id"] for x in lst), default=0) + 1

#  AUTENTIFICARE 
if "user_id" not in st.session_state:
    st.title("FinTrack - Autentificare")
    u = st.text_input("Username")
    p = st.text_input("Parola", type="password")
    if st.button("Intra in cont"):
        db = load_db()
        user = next((x for x in db["users"] if x["username"] == u and x["password"] == hash_pw(p)), None)
        if user:
            st.session_state["user_id"] = user["id"]
            st.rerun()
        else:
            st.error("Credentiale incorecte.")
    st.stop()

uid = st.session_state["user_id"]
db = load_db()

#  LISTE CATEGORII 
CAT_CHELTUIELI = ["Mancare", "Locuinta", "Transport", "Utilitati", "Sanatate", "Divertisment", "Altele"]
CAT_VENITURI = ["Salariu", "Freelance", "Dividende", "Cadouri", "Altele"]

# --- MENIU DE SUS ---
col_nav, col_btn = st.columns([4, 1])
with col_nav:
    nav = st.radio("Navigare", ["Dashboard & Istoric", "Adauga Tranzactie", "Bugete Lunare"], horizontal=True, label_visibility="collapsed")
with col_btn:
    if st.button("Deconectare"):
        del st.session_state["user_id"]
        st.rerun()

st.markdown("---")
txns = [t for t in db["transactions"] if t["user_id"] == uid]

#  DASHBOARD & ISTORIC 
if nav == "Dashboard & Istoric":
    st.title("Sumar Financiar")
    if not txns:
        st.info("Nu exista tranzactii inregistrate.")
    else:
        df = pd.DataFrame(txns)
        in_sum = df[df["type"] == "Venit"]["amount"].sum()
        out_sum = df[df["type"] == "Cheltuiala"]["amount"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Venituri", f"{in_sum} RON")
        c2.metric("Total Cheltuieli", f"{out_sum} RON")
        c3.metric("Sold Curent", f"{in_sum - out_sum} RON")
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_grafic1, col_grafic2 = st.columns(2)
        
        with col_grafic1:
            st.subheader("Cheltuieli pe categorii")
            exp = df[df["type"] == "Cheltuiala"].groupby("category")["amount"].sum()
            if not exp.empty:
                st.bar_chart(exp)
            else:
                st.write("Nu exista date pentru cheltuieli.")
                
        with col_grafic2:
            st.subheader("Evolutia soldului in timp")
            df_sorted = df.sort_values(["txn_date", "id"]).copy()
            df_sorted["signed_amount"] = df_sorted.apply(lambda r: r["amount"] if r["type"] == "Venit" else -r["amount"], axis=1)
            df_sorted["sold"] = df_sorted["signed_amount"].cumsum()
            df_chart = df_sorted.set_index("txn_date")["sold"]
            st.line_chart(df_chart)

        st.markdown("---")
        st.subheader("Istoric Tranzactii")
        df_display = df[["id", "txn_date", "type", "category", "amount", "description"]].sort_values("txn_date", ascending=False)
        st.dataframe(df_display, hide_index=True, use_container_width=True)
        
        # BUTON EXPORT CSV 
        csv_data = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(label="Descarca Istoric (CSV)", data=csv_data, file_name="istoric_fintrack.csv", mime="text/csv")
        
        st.markdown("<br>", unsafe_allow_html=True)
        del_id = st.number_input("ID-ul tranzactiei de sters", min_value=0, step=1)
        if st.button("Sterge Tranzactia") and del_id > 0:
            db["transactions"] = [t for t in db["transactions"] if t["id"] != del_id]
            save_db(db)
            st.rerun()

#  ADAUGA TRANZACTIE 
elif nav == "Adauga Tranzactie":
    st.title("Tranzactie Noua")
    
    
    tip = st.selectbox("Tip Tranzactie", ["Cheltuiala", "Venit"])
    categorii_curente = CAT_CHELTUIELI if tip == "Cheltuiala" else CAT_VENITURI
    
    with st.form("add_txn", clear_on_submit=True):
        cat = st.selectbox("Categorie", categorii_curente)
        suma = st.number_input("Suma (RON)", min_value=0.1, step=10.0)
        data_t = st.date_input("Data", date.today())
        desc = st.text_input("Descriere (Optional)")
        
        if st.form_submit_button("Salveaza Tranzactia"):
            db["transactions"].append({
                "id": get_id(db["transactions"]), "user_id": uid,
                "type": tip, "category": cat, "amount": suma,
                "txn_date": str(data_t), "description": desc
            })
            save_db(db)
            st.success(f"Salvat cu succes: {suma} RON ({cat})")

# BUGETE 
elif nav == "Bugete Lunare":
    st.title("Bugete Lunare")
    with st.form("b_form"):
        b_cat = st.selectbox("Categorie (Doar cheltuieli)", CAT_CHELTUIELI)
        b_luna = st.text_input("Luna (Format: YYYY-MM)", str(date.today())[:7])
        b_limita = st.number_input("Limita Buget (RON)", min_value=1.0, step=50.0)
        if st.form_submit_button("Seteaza Buget"):
            db["budgets"] = [b for b in db["budgets"] if not (b["user_id"] == uid and b["category"] == b_cat and b["month"] == b_luna)]
            db["budgets"].append({"id": get_id(db["budgets"]), "user_id": uid, "category": b_cat, "month": b_luna, "limit_amt": b_limita})
            save_db(db)
            st.success("Buget actualizat.")
            
    st.markdown("---")
    st.subheader("Status Bugete")
    my_b = [b for b in db["budgets"] if b["user_id"] == uid]
    df_txns = pd.DataFrame(txns)
    if not df_txns.empty: 
        df_txns["month"] = df_txns["txn_date"].str[:7]
    
    if not my_b:
        st.info("Nu ai setat niciun buget.")
        
    for b in my_b:
        spent = 0.0
        if not df_txns.empty:
            spent = df_txns[(df_txns["type"] == "Cheltuiala") & (df_txns["category"] == b["category"]) & (df_txns["month"] == b["month"])]["amount"].sum()
        
        st.write(f"Categorie: {b['category']} | Luna: {b['month']} | Cheltuit: {spent} / {b['limit_amt']} RON")
        st.progress(min(spent / b["limit_amt"], 1.0))
        if spent > b["limit_amt"]:
            st.warning("Buget depasit pentru aceasta categorie.")