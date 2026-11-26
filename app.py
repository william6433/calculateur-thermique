import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime
import os
import json
import urllib.request

# --- CONFIGURATION DE LA PAGE (AUTO-RESPONSIVE MOBILE) ---
st.set_page_config(
    page_title="Lidea | Calculateur Potentiel Thermique & Positionnement Variétal",
    page_icon="🌽",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- GESTION DE L'OUTIL ACTIF ---
if "outil_actif" not in st.session_state:
    st.session_state.outil_actif = "potentiel"

# --- DESIGN, CODE COULEUR LIDEA & RESPONSIVE MOBILE (CSS) ---
st.markdown("""
<style>
    .stApp {
        background-color: #F8FAF7;
    }
    .lidea-banner {
        background: linear-gradient(90deg, #2E5E2E 0%, #4E8B3B 100%);
        padding: 1.2rem 1.8rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(46, 94, 46, 0.15);
    }
    .lidea-banner h1 {
        color: white !important;
        font-size: 1.7rem !important;
        margin: 0 !important;
        font-weight: 700 !important;
        line-height: 1.25 !important;
    }
    .lidea-banner p {
        color: #E2EFDA !important;
        margin: 0.35rem 0 0 0 !important;
        font-size: 0.95rem !important;
    }
    /* Boutons de navigation principaux (Primary = actif, Secondary = inactif) */
    button[kind="primary"] {
        background-color: #2E5E2E !important;
        color: white !important;
        border: 2px solid #2E5E2E !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        min-height: 54px !important;
        box-shadow: 0 4px 10px rgba(46, 94, 46, 0.25) !important;
    }
    button[kind="primary"]:hover {
        background-color: #244B24 !important;
        border-color: #244B24 !important;
    }
    button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #2E5E2E !important;
        border: 2px solid #76B82A !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        min-height: 54px !important;
    }
    button[kind="secondary"]:hover {
        background-color: #EBF2E7 !important;
        color: #2E5E2E !important;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border-left: 5px solid #5B9A32;
        border-radius: 8px;
        padding: 14px 18px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
    }
    div[data-testid="stMetricLabel"] {
        color: #4A5568 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #2E5E2E !important;
        font-weight: 700 !important;
    }
    .section-title {
        color: #2E5E2E;
        border-bottom: 2px solid #76B82A;
        padding-bottom: 6px;
        margin-top: 1rem;
        margin-bottom: 1rem;
        font-weight: 700;
        font-size: 1.25rem;
    }

    /* --- ADAPTATIONS SPÉCIFIQUES TÉLÉPHONE PORTABLE --- */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            padding-top: 2.5rem !important;
        }
        .lidea-banner {
            padding: 0.9rem 1rem;
            margin-bottom: 0.8rem;
        }
        .lidea-banner h1 {
            font-size: 1.2rem !important;
        }
        .lidea-banner p {
            font-size: 0.8rem !important;
        }
        button[kind="primary"], button[kind="secondary"] {
            font-size: 0.92rem !important;
            min-height: 48px !important;
        }
        .section-title {
            font-size: 1.05rem;
        }
        div[data-testid="stMetric"] {
            padding: 10px 12px;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
        }
        div[data-testid="column"]:has(.mobile-hide-logo) {
            display: none;
        }
    }
</style>
""", unsafe_allow_html=True)

SHEET_ID = "11tZCCjazkhdk-E_kr8DvE5LicmsL5719U3fdZilJd-0"
GID_BDD = "893102045"
GID_VARIETES = "511199017"
GID_REGIONS = "891769745"

# --- CHARGEMENT DES DONNÉES (AVEC CACHE 1H) ---
def to_float(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", ".").str.replace("\u202f", "").str.strip(),
        errors="coerce"
    )

@st.cache_data(ttl=3600, show_spinner="Chargement de la base météo (300 000+ lignes)...")
def load_bdd():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_BDD}"
    df = pd.read_csv(url, dtype={"Code INSEE département": str}, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Année"] = df["Date"].dt.year
    df["MoisJour"] = df["Date"].dt.strftime("%m-%d")
    df["Code INSEE département"] = df["Code INSEE département"].astype(str).str.strip().str.zfill(2)
    df["Somme d°C/j"] = to_float(df["Somme d°C/j"])
    df["Somme d°C/j Sorgho (base 8-34)"] = to_float(df["Somme d°C/j Sorgho (base 8-34)"])
    return df.dropna(subset=["Date", "Département"]).sort_values(["Département", "Date"])

@st.cache_data(ttl=3600, show_spinner="Chargement de la base variétés...")
def load_varietes():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_VARIETES}"
    df = pd.read_csv(url)
    for col in [
        "UC semis-épiaison",
        "UC semis-récolte",
        "UC semis-floraison",
        "UC semis-récolte (32% H2O)",
        "UC semis-récolte (32% MS)"
    ]:
        if col in df.columns:
            df[col] = to_float(df[col])
    return df

@st.cache_data(ttl=3600)
def load_regions():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_REGIONS}"
    df = pd.read_csv(url, dtype={"Code": str})
    df["Code"] = df["Code"].astype(str).str.strip().str.zfill(2)
    return df

@st.cache_data(ttl=86400)
def load_geojson_and_centroids():
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    with urllib.request.urlopen(url) as resp:
        geojson_data = json.loads(resp.read().decode("utf-8"))
    centroids = {}
    for feat in geojson_data["features"]:
        code = str(feat["properties"]["code"]).strip().zfill(2)
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            coords = geom["coordinates"][0]
        else:
            coords = max(geom["coordinates"], key=lambda p: len(p[0]))[0]
        lon = sum(c[0] for c in coords) / len(coords)
        lat = sum(c[1] for c in coords) / len(coords)
        centroids[code] = (lon, lat)
    return geojson_data, centroids

# --- FONCTIONS DE COULEURS CONDITIONNELLES ---
def color_somme_thermique(val):
    if pd.isna(val):
        return ""
    if val < 1200:
        return "background-color: #FADBD8; color: #922B21; font-weight: 600;"
    elif val < 1500:
        return "background-color: #FDEBD0; color: #9C640C; font-weight: 600;"
    else:
        return "background-color: #D4EFDF; color: #1E8449; font-weight: 600;"

def color_ecart(val):
    if pd.isna(val):
        return ""
    if val >= 0:
        return "color: #1E8449; font-weight: 600;"
    return "color: #922B21; font-weight: 600;"

def color_statut_var(val):
    if isinstance(val, str) and "Non atteint" in val:
        return "background-color: #E5E7E9; color: #566573; font-weight: 600;"
    elif isinstance(val, str) and "Non renseigné" in val:
        return "color: #7F8C8D;"
    elif isinstance(val, str) and ("/" in val or "j" in val):
        return "background-color: #E8F5E9; color: #1E8449; font-weight: 600;"
    return ""

# --- RECHERCHE DU LOGO ---
logo_path = None
for fname in ["logo_lidea.png", "logo_lidea.jpg", "logo_lidea.jpeg"]:
    if os.path.exists(fname):
        logo_path = fname
        break

# --- BARRE LATÉRALE ---
with st.sidebar:
    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("## 🌱 **LIDEA**")
    st.caption("Outil d'aide à la décision — Maïs & Sorgho")
    st.divider()
    if st.button("🔄 Actualiser les données Sheets", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    st.info("Les ajouts dans Google Sheets (`BDD` et `BDD variétés`) sont actualisés automatiquement toutes les heures, ou immédiatement via le bouton ci-dessus.")

# --- EN-TÊTE PRINCIPAL ---
col_head_txt, col_head_logo = st.columns([4, 1])
with col_head_txt:
    st.markdown("""
    <div class="lidea-banner">
        <h1>🌽 Calculateur Potentiel Thermique & Positionnement Variétal</h1>
        <p>Pilotage des choix variétaux Maïs & Sorgho • Historique climatique 2018 – 2026 sur 96 départements</p>
    </div>
    """, unsafe_allow_html=True)
with col_head_logo:
    if logo_path:
        st.markdown('<div class="mobile-hide-logo"></div>', unsafe_allow_html=True)
        st.image(logo_path, use_container_width=True)

# --- SÉLECTEUR D'OUTIL BIEN VISIBLE ---
st.markdown("##### Choisissez votre outil :")
nav_c1, nav_c2 = st.columns(2)
with nav_c1:
    if st.button(
        "🌡️ POTENTIEL THERMIQUE DÉPARTEMENTAL",
        use_container_width=True,
        type="primary" if st.session_state.outil_actif == "potentiel" else "secondary"
    ):
        st.session_state.outil_actif = "potentiel"
        st.rerun()
with nav_c2:
    if st.button(
        "🌱 POSITIONNEMENT VARIÉTAL",
        use_container_width=True,
        type="primary" if st.session_state.outil_actif == "positionnement" else "secondary"
    ):
        st.session_state.outil_actif = "positionnement"
        st.rerun()

st.divider()

# Chargement initial
bdd = load_bdd()
varietes = load_varietes()
regions = load_regions()
geojson_data, centroids = load_geojson_and_centroids()
liste_deps = sorted(bdd["Département"].unique().tolist())
annees_dispo = sorted(bdd["Année"].dropna().astype(int).unique().tolist())

plotly_config = {
    "responsive": True,
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"]
}

# ==============================================================================
# OUTIL 1 : POTENTIEL THERMIQUE DÉPARTEMENTAL
# ==============================================================================
if st.session_state.outil_actif == "potentiel":
    st.markdown('<div class="section-title">1. Historique thermique pluriannuel local (2018 - 2026)</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    espece_t1 = c1.selectbox("Espèce", ["Maïs", "Sorgho"], key="t1_esp")
    dep_t1 = c2.selectbox(
        "Département",
        liste_deps,
        index=liste_deps.index("Ille-et-Vilaine") if "Ille-et-Vilaine" in liste_deps else 0,
        key="t1_dep"
    )
    semis_t1 = c3.date_input("Date de semis (JJ/MM)", value=datetime.date(2026, 4, 15), format="DD/MM/YYYY", key="t1_semis")
    recolte_t1 = c4.date_input("Date de récolte (JJ/MM)", value=datetime.date(2026, 9, 20), format="DD/MM/YYYY", key="t1_rec")

    col_uc_t1 = "Somme d°C/j Sorgho (base 8-34)" if espece_t1 == "Sorgho" else "Somme d°C/j"
    base_txt_t1 = "Base 8-34°C" if espece_t1 == "Sorgho" else "Base 6-30°C"
    st.caption(f"📌 Base de calcul appliquée : **{base_txt_t1}**")

    mj_s1, mj_r1 = semis_t1.strftime("%m-%d"), recolte_t1.strftime("%m-%d")
    sub_t1 = bdd[(bdd["Département"] == dep_t1) & (bdd["MoisJour"] >= mj_s1) & (bdd["MoisJour"] <= mj_r1)]

    hist_rows = []
    for an in annees_dispo:
        df_an = sub_t1[sub_t1["Année"] == an]
        somme = df_an[col_uc_t1].sum() if not df_an.empty else 0.0
        moy = df_an[col_uc_t1].mean() if not df_an.empty else 0.0
        hist_rows.append({
            "Année": str(an),
            "Date semis": f"{semis_t1.strftime('%d/%m')}/{an}",
            "Date récolte": f"{recolte_t1.strftime('%d/%m')}/{an}",
            "Somme (°C/j)": round(somme, 1),
            "Moyenne journalière (°C/j)": round(moy, 2)
        })
    df_hist = pd.DataFrame(hist_rows)
    moy_somme = df_hist["Somme (°C/j)"].mean()
    moy_jour = df_hist["Moyenne journalière (°C/j)"].mean()

    k1, k2 = st.columns(2)
    k1.metric(f"Moyenne pluriannuelle — Cumul ({dep_t1})", f"{moy_somme:,.1f} °C/j".replace(",", " "))
    k2.metric("Moyenne journalière", f"{moy_jour:.2f} °C/j")

    st.dataframe(
        df_hist.style.format({"Somme (°C/j)": "{:.1f}", "Moyenne journalière (°C/j)": "{:.2f}"})
                     .map(color_somme_thermique, subset=["Somme (°C/j)"]),
        use_container_width=True,
        hide_index=True
    )

    st.markdown('<div class="section-title">2. Cumuls et analyse thermique comparative des 96 départements</div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    espece_t2 = d1.selectbox("Espèce", ["Maïs", "Sorgho"], key="t2_esp")
    annee_t2 = d2.selectbox("Année à analyser", annees_dispo, index=len(annees_dispo) - 1, key="t2_an")
    semis_t2 = d3.date_input("Date de semis", value=datetime.date(2026, 4, 15), format="DD/MM/YYYY", key="t2_semis")
    recolte_t2 = d4.date_input("Date de récolte", value=datetime.date(2026, 9, 20), format="DD/MM/YYYY", key="t2_rec")

    col_uc_t2 = "Somme d°C/j Sorgho (base 8-34)" if espece_t2 == "Sorgho" else "Somme d°C/j"
    mj_s2, mj_r2 = semis_t2.strftime("%m-%d"), recolte_t2.strftime("%m-%d")
    sub_t2 = bdd[(bdd["Année"] == annee_t2) & (bdd["MoisJour"] >= mj_s2) & (bdd["MoisJour"] <= mj_r2)]

    nat_df = sub_t2.groupby(["Code INSEE département", "Département"], as_index=False).agg(
        Somme=(col_uc_t2, "sum"),
        Moyenne_jour=(col_uc_t2, "mean")
    )
    moy_fr = nat_df["Somme"].mean() if not nat_df.empty else 0
    nat_df["Écart vs Moyenne France (°C/j)"] = (nat_df["Somme"] - moy_fr).round(1)
    nat_df["Somme (°C/j)"] = nat_df["Somme"].round(1)
    nat_df["Moyenne journalière (°C/j)"] = nat_df["Moyenne_jour"].round(2)

    if not nat_df.empty:
        row_max = nat_df.loc[nat_df["Somme"].idxmax()]
        row_min = nat_df.loc[nat_df["Somme"].idxmin()]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Moyenne France", f"{moy_fr:,.1f} °C/j".replace(",", " "))
        m2.metric("Département le + Chaud", row_max["Département"], f"{row_max['Somme (°C/j)']:,.1f} °C/j".replace(",", " "))
        m3.metric("Département le + Frais", row_min["Département"], f"{row_min['Somme (°C/j)']:,.1f} °C/j".replace(",", " "))
        m4.metric("Amplitude Max - Min", f"{(row_max['Somme'] - row_min['Somme']):,.1f} °C/j".replace(",", " "))

    st.caption("Légende : 🔴 Rouge (< 1 200 °C/j)  •  🟠 Orange (1 200 - 1 500 °C/j)  •  🟢 Vert (≥ 1 500 °C/j)")

    col_tab, col_map = st.columns([1.1, 1.15])
    with col_tab:
        df_nat_disp = nat_df[["Code INSEE département", "Département", "Moyenne journalière (°C/j)", "Somme (°C/j)", "Écart vs Moyenne France (°C/j)"]]
        st.dataframe(
            df_nat_disp.style.format({
                "Moyenne journalière (°C/j)": "{:.2f}",
                "Somme (°C/j)": "{:.1f}",
                "Écart vs Moyenne France (°C/j)": "{:+.1f}"
            }).map(color_somme_thermique, subset=["Somme (°C/j)"])
              .map(color_ecart, subset=["Écart vs Moyenne France (°C/j)"]),
            use_container_width=True, height=450, hide_index=True
        )
    with col_map:
        if not nat_df.empty:
            nat_df["lon"] = nat_df["Code INSEE département"].map(lambda c: centroids.get(c, (None, None))[0])
            nat_df["lat"] = nat_df["Code INSEE département"].map(lambda c: centroids.get(c, (None, None))[1])
            nat_df["label_carte"] = nat_df["Somme (°C/j)"].round(0).astype(int).astype(str)

            fig = go.Figure()
            fig.add_trace(go.Choropleth(
                geojson=geojson_data,
                locations=nat_df["Code INSEE département"],
                featureidkey="properties.code",
                z=nat_df["Somme (°C/j)"],
                text=nat_df["Département"],
                colorscale=[[0, "#d73027"], [0.5, "#fee08b"], [1, "#2E5E2E"]],
                colorbar=dict(
                    title="°C/j",
                    orientation="h",
                    y=-0.05,
                    yanchor="top",
                    thickness=12,
                    len=0.75,
                    x=0.5,
                    xanchor="center"
                ),
                marker_line_color="white",
                marker_line_width=0.6,
                hovertemplate="<b>%{text}</b><br>Somme : %{z:.1f} °C/j<extra></extra>"
            ))
            df_lbl = nat_df.dropna(subset=["lon", "lat"])
            fig.add_trace(go.Scattergeo(
                lon=df_lbl["lon"],
                lat=df_lbl["lat"],
                text=df_lbl["label_carte"],
                mode="text",
                textfont=dict(size=7.5, color="#111111"),
                hoverinfo="skip",
                showlegend=False
            ))
            fig.add_annotation(
                text="Source LIDEA = outil interne",
                xref="paper", yref="paper",
                x=0.99, y=0.01,
                xanchor="right", yanchor="bottom",
                showarrow=False,
                font=dict(size=10, color="#4A5568")
            )
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(
                title=f"Carte thermique {annee_t2} ({espece_t2}) — °C/j<br><sup>Semis : {semis_t2.strftime('%d/%m/%Y')}  •  Récolte : {recolte_t2.strftime('%d/%m/%Y')}</sup>",
                margin={"r": 0, "t": 55, "l": 0, "b": 45},
                height=535,
                paper_bgcolor="rgba(0,0,0,0)",
                geo_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)

# ==============================================================================
# OUTIL 2 : POSITIONNEMENT VARIÉTAL
# ==============================================================================
else:
    # --------------------------------------------------------------------------
    # PARTIE 1 : ANALYSE LOCALE (Lignes 5 à 28 du Google Sheet)
    # --------------------------------------------------------------------------
    st.markdown('<div class="section-title">1. Cycle phénologique local — Paramètres de sélection</div>', unsafe_allow_html=True)
    p1, p2, p3, p4 = st.columns(4)
    dep_v = p1.selectbox(
        "Département",
        liste_deps,
        index=liste_deps.index("Morbihan") if "Morbihan" in liste_deps else 0,
        key="v_dep"
    )
    esp_v = p2.selectbox("Espèce", sorted(varietes["Espèce"].dropna().unique()), key="v_esp")

    var_esp = varietes[varietes["Espèce"] == esp_v]
    dest_v = p3.selectbox("Destination", sorted(var_esp["Destination"].dropna().unique()), key="v_dest")

    var_dest = var_esp[var_esp["Destination"] == dest_v]
    prec_v = p4.selectbox("Précocité", sorted(var_dest["Précocité"].dropna().unique()), key="v_prec")

    p5, p6, p7, p8 = st.columns(4)
    var_prec = var_dest[var_dest["Précocité"] == prec_v]
    nom_var = p5.selectbox("Variété", sorted(var_prec["Variétés"].dropna().unique()), key="v_nom")

    obj_val = "Grain"
    if esp_v.lower() == "maïs" and dest_v.lower() == "mixte":
        obj_val = p6.selectbox("Objectif valorisation (Mixte)", ["Fourrage", "Grain"], key="v_obj")
    else:
        p6.text_input("Objectif valorisation", value=dest_v, disabled=True, key="v_obj_disp")

    semis_v = p7.date_input("Date de semis", value=datetime.date(2026, 4, 20), format="DD/MM/YYYY", key="v_semis")
    recolte_cible_v = p8.date_input("Date de récolte cible", value=datetime.date(2026, 9, 15), format="DD/MM/YYYY", key="v_rec_cible")

    an_min, an_max = min(annees_dispo), max(annees_dispo)
    periode = st.slider("Période d'analyse locale (campagnes)", an_min, an_max, (an_min, an_max), key="v_periode")

    row_v = var_prec[var_prec["Variétés"] == nom_var].iloc[0]
    if esp_v.lower() == "sorgho":
        besoin_flo = row_v["UC semis-épiaison"]
        besoin_rec = row_v["UC semis-récolte"]
        lbl_flo = "Épiaison"
        col_uc_v = "Somme d°C/j Sorgho (base 8-34)"
    else:
        besoin_flo = row_v["UC semis-floraison"]
        if dest_v.lower() == "fourrage" or (dest_v.lower() == "mixte" and obj_val.lower() == "fourrage"):
            besoin_rec = row_v["UC semis-récolte (32% MS)"]
        else:
            besoin_rec = row_v["UC semis-récolte (32% H2O)"]
        lbl_flo = "Floraison"
        col_uc_v = "Somme d°C/j"

    b1, b2, b3 = st.columns(3)
    b1.metric(f"Besoin {lbl_flo}", f"{besoin_flo:.0f} °C/j" if pd.notna(besoin_flo) else "Non renseigné")
    b2.metric("Besoin Récolte", f"{besoin_rec:.0f} °C/j" if pd.notna(besoin_rec) else "Non renseigné")
    b3.metric("Base thermique", "Base 8-34°C" if esp_v.lower() == "sorgho" else "Base 6-30°C")

    st.subheader(f"Résultats locaux — {nom_var} en {dep_v} ({periode[0]} - {periode[1]})")
    bdd_loc = bdd[(bdd["Département"] == dep_v) & (bdd["Année"] >= periode[0]) & (bdd["Année"] <= periode[1])]

    loc_rows = []
    durees_flo, durees_rec = [], []
    reussites = 0
    nb_campagnes = periode[1] - periode[0] + 1

    for an in range(periode[0], periode[1] + 1):
        d_sem = datetime.date(an, semis_v.month, semis_v.day)
        d_cible = datetime.date(an, recolte_cible_v.month, recolte_cible_v.day)
        df_y = bdd_loc[(bdd_loc["Année"] == an) & (bdd_loc["Date"] >= pd.Timestamp(d_sem))].copy()
        df_y["Cumul"] = df_y[col_uc_v].cumsum()

        if pd.isna(besoin_flo):
            str_flo, str_d_flo = "Non renseigné", "Non renseigné"
        else:
            hit_f = df_y[df_y["Cumul"] >= besoin_flo]
            if hit_f.empty:
                str_flo, str_d_flo = "Non atteint", "Non atteint"
            else:
                dt_f = hit_f.iloc[0]["Date"].date()
                nb_f = (dt_f - d_sem).days
                str_flo, str_d_flo = dt_f.strftime("%d/%m/%Y"), f"{nb_f} j"
                durees_flo.append(nb_f)

        if pd.isna(besoin_rec):
            str_rec, str_d_rec = "Non renseigné", "Non renseigné"
        else:
            hit_r = df_y[df_y["Cumul"] >= besoin_rec]
            if hit_r.empty:
                str_rec, str_d_rec = "Non atteint", "Non atteint"
            else:
                dt_r = hit_r.iloc[0]["Date"].date()
                nb_r = (dt_r - d_sem).days
                if dt_r > d_cible:
                    str_rec = f"Non atteint ({dt_r.strftime('%d/%m/%Y')})"
                    str_d_rec = f"Non atteint ({nb_r} j)"
                else:
                    str_rec = dt_r.strftime("%d/%m/%Y")
                    str_d_rec = f"{nb_r} j"
                    reussites += 1
                durees_rec.append(nb_r)

        loc_rows.append({
            "Année": str(an),
            "Date semis": d_sem.strftime("%d/%m/%Y"),
            f"Date {lbl_flo.lower()}": str_flo,
            f"Semis-{lbl_flo.lower()}": str_d_flo,
            "Date récolte": str_rec,
            "Semis-récolte": str_d_rec
        })

    moy_f = round(np.mean(durees_flo)) if durees_flo else None
    moy_r = round(np.mean(durees_rec)) if durees_rec else None
    k_v1, k_v2, k_v3 = st.columns(3)
    if moy_f:
        dt_moy_f = semis_v + datetime.timedelta(days=moy_f)
        k_v1.metric(f"Estimation {lbl_flo} (moyenne)", dt_moy_f.strftime("%d/%m"), f"{moy_f} jours")
    else:
        k_v1.metric(f"Estimation {lbl_flo}", "N/A")

    if moy_r:
        dt_moy_r = semis_v + datetime.timedelta(days=moy_r)
        k_v2.metric("Estimation Récolte (moyenne)", dt_moy_r.strftime("%d/%m"), f"{moy_r} jours")
    else:
        k_v2.metric("Estimation Récolte", "Maturité non garantie")

    k_v3.metric("Taux de réussite (avant date cible)", f"{reussites} / {nb_campagnes} campagnes")

    df_loc_res = pd.DataFrame(loc_rows)
    cols_statut = [f"Date {lbl_flo.lower()}", f"Semis-{lbl_flo.lower()}", "Date récolte", "Semis-récolte"]
    st.dataframe(
        df_loc_res.style.map(color_statut_var, subset=cols_statut),
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------------------------
    # PARTIE 2 : VISION NATIONALE (Lignes 33 à 138 du Google Sheet)
    # --------------------------------------------------------------------------
    st.divider()
    st.markdown('<div class="section-title">2. Vision nationale (96 départements) — Paramètres de sélection</div>', unsafe_allow_html=True)

    vn_c1, vn_c2, vn_c3, vn_c4 = st.columns(4)
    esp_vn = vn_c1.selectbox("Espèce", sorted(varietes["Espèce"].dropna().unique()), key="vn_esp")

    var_esp_n = varietes[varietes["Espèce"] == esp_vn]
    dest_list_n = sorted(var_esp_n["Destination"].dropna().unique())
    dest_vn = vn_c2.selectbox(
        "Destination",
        dest_list_n,
        index=dest_list_n.index("Grain") if "Grain" in dest_list_n else 0,
        key="vn_dest"
    )

    var_dest_n = var_esp_n[var_esp_n["Destination"] == dest_vn]
    prec_list_n = sorted(var_dest_n["Précocité"].dropna().unique())
    prec_vn = vn_c3.selectbox(
        "Précocité",
        prec_list_n,
        index=prec_list_n.index("G1") if "G1" in prec_list_n else 0,
        key="vn_prec"
    )

    var_prec_n = var_dest_n[var_dest_n["Précocité"] == prec_vn]
    nom_list_n = sorted(var_prec_n["Variétés"].dropna().unique())
    nom_vn = vn_c4.selectbox(
        "Variété",
        nom_list_n,
        index=nom_list_n.index("BANDANA") if "BANDANA" in nom_list_n else 0,
        key="vn_nom"
    )

    vn_c5, vn_c6, vn_c7 = st.columns(3)
    obj_val_n = "Grain"
    if esp_vn.lower() == "maïs" and dest_vn.lower() == "mixte":
        obj_val_n = vn_c5.selectbox("Objectif valorisation (Mixte)", ["Fourrage", "Grain"], key="vn_obj")
    else:
        vn_c5.text_input("Objectif valorisation", value=dest_vn, disabled=True, key="vn_obj_disp")

    semis_vn = vn_c6.date_input("Date de semis", value=datetime.date(2027, 4, 1), format="DD/MM/YYYY", key="vn_semis")
    recolte_cible_vn = vn_c7.date_input("Date de récolte cible", value=datetime.date(2027, 9, 10), format="DD/MM/YYYY", key="vn_rec_cible")

    default_deb_vn = 2021 if 2021 >= an_min and 2021 <= an_max else an_min
    periode_vn = st.slider("Période d'analyse nationale (campagnes)", an_min, an_max, (default_deb_vn, an_max), key="vn_periode")

    row_vn = var_prec_n[var_prec_n["Variétés"] == nom_vn].iloc[0]
    if esp_vn.lower() == "sorgho":
        besoin_flo_n = row_vn["UC semis-épiaison"]
        besoin_rec_n = row_vn["UC semis-récolte"]
        lbl_flo_n = "Épiaison"
        col_uc_vn = "Somme d°C/j Sorgho (base 8-34)"
    else:
        besoin_flo_n = row_vn["UC semis-floraison"]
        if dest_vn.lower() == "fourrage" or (dest_vn.lower() == "mixte" and obj_val_n.lower() == "fourrage"):
            besoin_rec_n = row_vn["UC semis-récolte (32% MS)"]
        else:
            besoin_rec_n = row_vn["UC semis-récolte (32% H2O)"]
        lbl_flo_n = "Floraison"
        col_uc_vn = "Somme d°C/j"

    bn1, bn2, bn3 = st.columns(3)
    bn1.metric(f"Besoin {lbl_flo_n}", f"{besoin_flo_n:.0f} °C/j" if pd.notna(besoin_flo_n) else "Non renseigné")
    bn2.metric("Besoin Récolte", f"{besoin_rec_n:.0f} °C/j" if pd.notna(besoin_rec_n) else "Non renseigné")
    bn3.metric("Base thermique", "Base 8-34°C" if esp_vn.lower() == "sorgho" else "Base 6-30°C")

    st.subheader(f"Analyse comparative des 96 départements — {nom_vn} ({periode_vn[0]} - {periode_vn[1]})")
    bdd_nat = bdd[(bdd["Année"] >= periode_vn[0]) & (bdd["Année"] <= periode_vn[1]) & (bdd["MoisJour"] >= semis_vn.strftime("%m-%d"))]
    d_cible_ref = datetime.date(semis_vn.year, recolte_cible_vn.month, recolte_cible_vn.day)

    nat_var_rows = []
    for (code_dep, nom_dep), grp in bdd_nat.groupby(["Code INSEE département", "Département"]):
        d_f_list, d_r_list = [], []
        for an, g_an in grp.groupby("Année"):
            g_an = g_an.sort_values("Date")
            cum = g_an[col_uc_vn].cumsum()
            d0 = g_an["Date"].iloc[0]
            if pd.notna(besoin_flo_n):
                hf = g_an[cum >= besoin_flo_n]
                if not hf.empty:
                    d_f_list.append((hf["Date"].iloc[0] - d0).days)
            if pd.notna(besoin_rec_n):
                hr = g_an[cum >= besoin_rec_n]
                if not hr.empty:
                    d_r_list.append((hr["Date"].iloc[0] - d0).days)

        mf = round(np.mean(d_f_list)) if len(d_f_list) > 0 else None
        mr = round(np.mean(d_r_list)) if len(d_r_list) > 0 else None
        date_f_est = (semis_vn + datetime.timedelta(days=mf)).strftime("%d/%m/%Y") if mf else "Non atteint"

        if mr:
            dt_r_est = semis_vn + datetime.timedelta(days=mr)
            label_carte = dt_r_est.strftime("%d/%m")
            if dt_r_est > d_cible_ref:
                date_r_est = f"Non atteint ({dt_r_est.strftime('%d/%m/%Y')})"
                dur_r_est = mr
                atteint = False
            else:
                date_r_est = dt_r_est.strftime("%d/%m/%Y")
                dur_r_est = mr
                atteint = True
        else:
            date_r_est = "Non atteint"
            label_carte = "N/A"
            dur_r_est = np.nan
            atteint = False

        nat_var_rows.append({
            "Code INSEE": code_dep,
            "Département": nom_dep,
            f"Date {lbl_flo_n.lower()} estimée": date_f_est,
            f"Durée {lbl_flo_n.lower()} (j)": mf if mf else np.nan,
            "Date récolte estimée": date_r_est,
            "Durée récolte (j)": dur_r_est,
            "Atteint": atteint,
            "Label Carte": label_carte
        })

    df_nat_var = pd.DataFrame(nat_var_rows)
    st.caption("Légende carte : 🟢 Vert à Jaune = Maturité atteinte avant la date cible  •  ⬜ Gris = Date cible non atteinte (avec date estimative affichée)")

    col_vt, col_vm = st.columns([1.1, 1.15])
    with col_vt:
        df_vt_disp = df_nat_var.drop(columns=["Atteint", "Label Carte"])
        st.dataframe(
            df_vt_disp.style.format({
                f"Durée {lbl_flo_n.lower()} (j)": "{:.0f}",
                "Durée récolte (j)": "{:.0f}"
            }, na_rep="—").map(color_statut_var, subset=[f"Date {lbl_flo_n.lower()} estimée", "Date récolte estimée"]),
            use_container_width=True, height=450, hide_index=True
        )
    with col_vm:
        df_nat_var["lon"] = df_nat_var["Code INSEE"].map(lambda c: centroids.get(c, (None, None))[0])
        df_nat_var["lat"] = df_nat_var["Code INSEE"].map(lambda c: centroids.get(c, (None, None))[1])

        df_ok = df_nat_var[df_nat_var["Atteint"] == True]
        df_ko = df_nat_var[df_nat_var["Atteint"] == False]

        fig_v = go.Figure()
        if not df_ko.empty:
            fig_v.add_trace(go.Choropleth(
                geojson=geojson_data,
                locations=df_ko["Code INSEE"],
                featureidkey="properties.code",
                z=[1] * len(df_ko),
                text=df_ko["Département"],
                customdata=df_ko["Date récolte estimée"],
                colorscale=[[0, "#D5D8DC"], [1, "#D5D8DC"]],
                showscale=False,
                marker_line_color="white",
                marker_line_width=0.6,
                hovertemplate="<b>%{text}</b><br>Statut : %{customdata}<extra></extra>"
            ))

        if not df_ok.empty:
            fig_v.add_trace(go.Choropleth(
                geojson=geojson_data,
                locations=df_ok["Code INSEE"],
                featureidkey="properties.code",
                z=df_ok["Durée récolte (j)"],
                text=df_ok["Département"],
                customdata=df_ok["Date récolte estimée"],
                colorscale=[[0, "#2E5E2E"], [0.5, "#76B82A"], [1, "#fee08b"]],
                colorbar=dict(
                    title="Jours",
                    orientation="h",
                    y=-0.05,
                    yanchor="top",
                    thickness=12,
                    len=0.75,
                    x=0.5,
                    xanchor="center"
                ),
                marker_line_color="white",
                marker_line_width=0.6,
                hovertemplate="<b>%{text}</b><br>Date récolte : %{customdata}<br>Durée : %{z:.0f} j<extra></extra>"
            ))

        df_lbl_v = df_nat_var.dropna(subset=["lon", "lat"])
        fig_v.add_trace(go.Scattergeo(
            lon=df_lbl_v["lon"],
            lat=df_lbl_v["lat"],
            text=df_lbl_v["Label Carte"],
            mode="text",
            textfont=dict(size=7, color="#111111"),
            hoverinfo="skip",
            showlegend=False
        ))

        fig_v.add_annotation(
            text="Source LIDEA = outil interne",
            xref="paper", yref="paper",
            x=0.99, y=0.01,
            xanchor="right", yanchor="bottom",
            showarrow=False,
            font=dict(size=10, color="#4A5568")
        )
        fig_v.update_geos(fitbounds="locations", visible=False)
        fig_v.update_layout(
            title=f"Date de récolte estimée (JJ/MM) — {nom_vn}<br><sup>Semis : {semis_vn.strftime('%d/%m/%Y')}  •  Récolte cible : {recolte_cible_vn.strftime('%d/%m/%Y')}  •  Période : {periode_vn[0]}-{periode_vn[1]}</sup>",
            margin={"r": 0, "t": 55, "l": 0, "b": 45},
            height=535,
            paper_bgcolor="rgba(0,0,0,0)",
            geo_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_v, use_container_width=True, config=plotly_config)
