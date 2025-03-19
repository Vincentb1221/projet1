import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.express as px
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Gestion Financière", layout="wide")

# Fonction pour récupérer le symbole boursier à partir du nom de l'entreprise
def get_ticker(company_name):
    try:
        search_result = yf.Ticker(company_name)
        return search_result.ticker if search_result else None
    except:
        return None

# Fonction pour calculer les intérêts composés
def calculer_capital(montant, taux, duree, type_invest="Actions"):
    capital = 0
    evolution = []
    for annee in range(1, duree + 1):
        taux_ajuste = taux / 100 * (1.2 if type_invest == "Actions" else 0.8)
        capital = (capital + montant) * (1 + taux_ajuste)
        evolution.append((annee, round(capital, 2)))
    return pd.DataFrame(evolution, columns=["Année", "Capital accumulé"])

# Fonction pour calculer la volatilité et la VaR
def calculer_risque(historique):
    try:
        rendements = historique.pct_change().dropna()
        if len(rendements) < 2:
            return "N/A", "N/A"
        volatilite = rendements.std() * np.sqrt(252)  # Annualisée
        var = np.percentile(rendements, 5)  # VaR à 95%
        return volatilite, var
    except:
        return "N/A", "N/A"

# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.selectbox("Choisir une section", 
                           ["Calculateur d'Intérêts", "Portefeuille", "Watchlist", "Informations Financières"])

# Section 1 : Calculateur d'Intérêts Composés
if page == "Calculateur d'Intérêts":
    st.title("💰 Calculateur de Placement et Intérêts Composés")
    montant_annuel = st.number_input("Montant investi par an ($)", min_value=0.0, value=1000.0, step=100.0)
    taux_interet = st.number_input("Taux d'intérêt annuel (%)", min_value=0.0, value=5.0, step=0.1)
    annees = st.number_input("Nombre d'années", min_value=1, value=10, step=1)
    type_invest = st.selectbox("Type d'investissement", ["Actions", "Obligations"])
    
    if st.button("Calculer"):
        df = calculer_capital(montant_annuel, taux_interet, annees, type_invest)
        st.dataframe(df.style.format({"Capital accumulé": "${:,.2f}"}))
        fig = px.line(df, x="Année", y="Capital accumulé", title="Évolution du Capital")
        st.plotly_chart(fig)
        st.success(f"Capital final après {annees} ans : ${df['Capital accumulé'].iloc[-1]:,.2f}")

# Section 2 : Portefeuille
elif page == "Portefeuille":
    st.title("📊 Mon Portefeuille")
    
    if "portefeuille" not in st.session_state:
        st.session_state.portefeuille = pd.DataFrame(columns=["Entreprise", "Symbole", "Type", "Quantité", "Prix Achat", "Valeur Actuelle"])
    
    with st.form(key="ajout_actif"):
        company_name = st.text_input("Nom de l'entreprise")
        quantite = st.number_input("Quantité", min_value=0.0, step=1.0)
        type_actif = st.selectbox("Type", ["Actions", "Obligations"])
        prix_achat = st.number_input("Prix d'achat ($)", min_value=0.0, step=0.1)
        submit = st.form_submit_button("Ajouter")
        
        if submit and company_name:
            symbole = get_ticker(company_name)
            if symbole:
                actif = yf.Ticker(symbole)
                hist = actif.history(period="1d")
                if not hist.empty:
                    prix_actuel = hist["Close"].iloc[-1]
                    new_row = {"Entreprise": company_name, "Symbole": symbole, "Type": type_actif, "Quantité": quantite, "Prix Achat": prix_achat, "Valeur Actuelle": prix_actuel}
                    st.session_state.portefeuille = pd.concat([st.session_state.portefeuille, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"{company_name} ajouté au portefeuille !")
                else:
                    st.error("Données indisponibles pour cette entreprise.")
            else:
                st.error("Entreprise introuvable. Vérifiez le nom.")
    
    if not st.session_state.portefeuille.empty:
        st.subheader("Composition du portefeuille")
        st.session_state.portefeuille["Valeur Totale"] = st.session_state.portefeuille["Quantité"] * st.session_state.portefeuille["Valeur Actuelle"]
        st.session_state.portefeuille["Profit/Perte"] = (st.session_state.portefeuille["Valeur Actuelle"] - st.session_state.portefeuille["Prix Achat"]) * st.session_state.portefeuille["Quantité"]
        st.dataframe(st.session_state.portefeuille.style.format({
            "Prix Achat": "${:.2f}", "Valeur Actuelle": "${:.2f}", "Valeur Totale": "${:,.2f}", "Profit/Perte": "${:,.2f}"
        }))
        
        # Graphique de répartition
        fig = px.pie(st.session_state.portefeuille, names="Entreprise", values="Valeur Totale", title="Répartition du Portefeuille")
        st.plotly_chart(fig)
        
        # Option de suppression
        entreprise_a_supprimer = st.selectbox("Supprimer une entreprise", st.session_state.portefeuille["Entreprise"].unique())
        if st.button("Supprimer"):
            st.session_state.portefeuille = st.session_state.portefeuille[st.session_state.portefeuille["Entreprise"] != entreprise_a_supprimer]
            st.success(f"{entreprise_a_supprimer} retiré du portefeuille.")

# Footer
st.sidebar.markdown("---")
st.sidebar.write(f"Date : {datetime.now().strftime('%Y-%m-%d')}")
