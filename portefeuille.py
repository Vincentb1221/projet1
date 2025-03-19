# app.py
import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# Configuration de la page
st.set_page_config(page_title="Gestion Financière", layout="wide")

# Menu latéral
st.sidebar.header("Navigation")
page = st.sidebar.selectbox("Choisir une section", 
                           ["Calculateur d'Intérêts", "Portefeuille", "Watchlist", "Informations Financières"])

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

# Section 1 : Calculateur d'Intérêts Composés
if page == "Calculateur d'Intérêts":
    st.title("💰 Calculateur de Placement et Intérêts Composés")
    
    col1, col2 = st.columns(2)
    with col1:
        montant_annuel = st.number_input("Montant investi par an ($)", min_value=0.0, value=1000.0, step=100.0)
        taux_interet = st.number_input("Taux d'intérêt annuel (%)", min_value=0.0, value=5.0, step=0.1)
    with col2:
        annees = st.number_input("Nombre d'années", min_value=1, value=10, step=1)
        type_invest = st.selectbox("Type d'investissement", ["Actions", "Obligations"])

    if st.button("Calculer"):
        df = calculer_capital(montant_annuel, taux_interet, annees, type_invest)
        
        st.subheader("📈 Évolution du capital")
        st.dataframe(df.style.format({"Capital accumulé": "${:,.2f}"}))

        # Graphique avec st.line_chart
        st.line_chart(df.set_index("Année")["Capital accumulé"].rename(type_invest))

        total = df["Capital accumulé"].iloc[-1]
        st.success(f"Capital final après {annees} ans : ${total:,.2f}")
        
        csv = df.to_csv(index=False)
        st.download_button("Télécharger les données", csv, "evolution_capital.csv", "text/csv")

# Section 2 : Portefeuille
elif page == "Portefeuille":
    st.title("📊 Mon Portefeuille")
    
    if "portefeuille" not in st.session_state:
        st.session_state.portefeuille = pd.DataFrame(columns=["Actif", "Type", "Quantité", "Prix Achat", "Valeur Actuelle"])
    
    with st.form(key="ajout_actif"):
        col1, col2, col3 = st.columns(3)
        with col1:
            symbole = st.text_input("Symbole (ex: AAPL, TSLA)")
            quantite = st.number_input("Quantité", min_value=0.0, step=1.0)
        with col2:
            type_actif = st.selectbox("Type", ["Actions", "Obligations"])
            prix_achat = st.number_input("Prix d'achat ($)", min_value=0.0, step=0.1)
        with col3:
            submit = st.form_submit_button("Ajouter")
        
        if submit and symbole:
            try:
                actif = yf.Ticker(symbole.upper())
                hist = actif.history(period="1d")
                if hist.empty:
                    raise ValueError("Aucune donnée disponible")
                prix_actuel = hist["Close"].iloc[-1]
                new_row = {"Actif": symbole.upper(), "Type": type_actif, "Quantité": quantite, 
                          "Prix Achat": prix_achat, "Valeur Actuelle": prix_actuel}
                st.session_state.portefeuille = pd.concat([st.session_state.portefeuille, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"{symbole.upper()} ajouté au portefeuille !")
            except Exception as e:
                st.error(f"Erreur : {str(e)}")

    if not st.session_state.portefeuille.empty:
        st.subheader("Composition du portefeuille")
        st.session_state.portefeuille["Valeur Totale"] = st.session_state.portefeuille["Quantité"] * st.session_state.portefeuille["Valeur Actuelle"]
        st.session_state.portefeuille["Profit/Perte"] = (st.session_state.portefeuille["Valeur Actuelle"] - st.session_state.portefeuille["Prix Achat"]) * st.session_state.portefeuille["Quantité"]
        
        risques = []
        for symbole in st.session_state.portefeuille["Actif"]:
            try:
                hist = yf.Ticker(symbole).history(period="1y")["Close"]
                volatilite, var = calculer_risque(hist)
                risques.append({"Volatilité (annuelle)": volatilite, "VaR (95%)": var})
            except:
                risques.append({"Volatilité (annuelle)": "N/A", "VaR (95%)": "N/A"})
        
        risque_df = pd.DataFrame(risques)
        portefeuille_complet = pd.concat([st.session_state.portefeuille, risque_df], axis=1)
        st.dataframe(portefeuille_complet.style.format({
            "Prix Achat": "${:.2f}", "Valeur Actuelle": "${:.2f}", 
            "Valeur Totale": "${:,.2f}", "Profit/Perte": "${:,.2f}",
            "Volatilité (annuelle)": lambda x: "N/A" if x == "N/A" else "{:.2%}".format(x),
            "VaR (95%)": lambda x: "N/A" if x == "N/A" else "{:.2%}".format(x)
        }))

        # Graphique de répartition avec st.bar_chart
        repartition = portefeuille_complet.groupby("Actif")["Valeur Totale"].sum()
        st.bar_chart(repartition)

# Section 3 : Watchlist
elif page == "Watchlist":
    st.title("👀 Ma Watchlist")
    
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []
    
    symbole = st.text_input("Ajouter un symbole à la watchlist (ex: AAPL)")
    if st.button("Ajouter") and symbole:
        st.session_state.watchlist.append(symbole.upper())
        st.success(f"{symbole.upper()} ajouté à la watchlist !")
    
    if st.session_state.watchlist:
        st.subheader("Ma Watchlist")
        data = {}
        risques = []
        for symbole in st.session_state.watchlist:
            try:
                actif = yf.Ticker(symbole)
                hist = actif.history(period="1mo")
                if hist.empty:
                    raise ValueError("Aucune donnée disponible")
                data[symbole] = hist["Close"].iloc[-1]
                volatilite, var = calculer_risque(hist["Close"])
                risques.append({"Volatilité (annuelle)": volatilite, "VaR (95%)": var})
            except:
                data[symbole] = "N/A"
                risques.append({"Volatilité (annuelle)": "N/A", "VaR (95%)": "N/A"})
        
        watch_df = pd.DataFrame(list(data.items()), columns=["Symbole", "Prix Actuel"])
        risque_df = pd.DataFrame(risques)
        watch_complet = pd.concat([watch_df, risque_df], axis=1)
        st.dataframe(watch_complet.style.format({
            "Prix Actuel": lambda x: "N/A" if x == "N/A" else "${:.2f}".format(x),
            "Volatilité (annuelle)": lambda x: "N/A" if x == "N/A" else "{:.2%}".format(x),
            "VaR (95%)": lambda x: "N/A" if x == "N/A" else "{:.2%}".format(x)
        }))
        
        # Graphique avec st.line_chart
        watch_data = pd.DataFrame()
        for symbole in st.session_state.watchlist:
            try:
                hist = yf.Ticker(symbole).history(period="1mo")["Close"]
                watch_data[symbole] = hist
            except:
                pass
        if not watch_data.empty:
            st.line_chart(watch_data)

# Section 4 : Informations Financières
elif page == "Informations Financières":
    st.title("ℹ️ Informations Financières")
    
    symbole = st.text_input("Entrez un symbole (ex: AAPL)")
    if symbole:
        try:
            actif = yf.Ticker(symbole.upper())
            info = actif.info
            st.subheader(f"{info['longName']} ({symbole.upper()})")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Secteur** : {info.get('sector', 'N/A')}")
                st.write(f"**Prix actuel** : ${info.get('currentPrice', 'N/A'):.2f}")
                st.write(f"**Capitalisation** : ${info.get('marketCap', 0):,.0f}")
            with col2:
                st.write(f"**PER** : {info.get('trailingPE', 'N/A'):.2f}")
                st.write(f"**Dividende** : {info.get('dividendYield', 0) * 100:.2f}%")
                st.write(f"**52 semaines** : ${info.get('fiftyTwoWeekLow', 0):.2f} - ${info.get('fiftyTwoWeekHigh', 0):.2f}")
            
            hist = actif.history(period="1y")
            if not hist.empty:
                volatilite, var = calculer_risque(hist["Close"])
                st.write(f"**Volatilité (annuelle)** : {'N/A' if volatilite == 'N/A' else f'{volatilite:.2%}'}")
                st.write(f"**VaR (95%)** : {'N/A' if var == 'N/A' else f'{var:.2%}'} (perte potentielle max sur 1 jour)")
            
            periode = st.selectbox("Période", ["1mo", "6mo", "1y", "5y"])
            hist = actif.history(period=periode)
            if not hist.empty:
                st.line_chart(hist["Close"].rename(f"Historique {symbole.upper()} ({periode})"))
        except Exception as e:
            st.error(f"Erreur : {str(e)}")

# Footer
st.sidebar.markdown("---")
st.sidebar.write(f"Date : {datetime.now().strftime('%Y-%m-%d')}")