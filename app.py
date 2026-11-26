Python
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Calculateur Potentiel Thermique & Positionnement Variétal",
    page_icon="🌽",
    layout="wide"
)

SHEET_ID = "1wOQ0DTyrDGVB7g0jBTkbn8R6yme7PpUlOV5cc993sBY"
GID_BDD = "893102045"
GID_VARIETES = "511199017"
GID_REGIONS = "891769745"

# --- CHARGEMENT DES DONNÉES (AVEC CACHE 1H) ---
def to_float(series):
    return pd.to_numeric(series.astype(str).str.replace(",", ".").str.replace("\u202f", "").str.strip(), errors="coerce")

@st.cache_data(ttl=3600, show_spinner="Chargement de la base météo (300 000+ lignes)...")
def load_bdd():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_BDD}"
    df = pd.read_csv(url, dtype={"Code INSEE département": str})
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
    for col in ["UC semis-épiaison", "UC semis-récolte", "UC semis-floraison", "UC semis-récolte (32% H2O)", "UC semis-récolte (32% MS)"]:
        if col in df.columns:
            df[col] = to_float(df[col])
    return df

@st.cache_data(ttl=3600)
def load_regions():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_REGIONS}"
    df = pd.read_csv(url, dtype={"Code": str})
    df["Code"] = df["Code"].astype(str).str.strip().str.zfill(2)
    return df

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.title("🌽 Pilotage Variétal")
    st.caption("Outil d'aide à la décision - Maïs & Sorgho")
    if st.button("🔄 Actualiser les données Sheets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.info("Les modifications faites dans Google Sheets (`BDD` et `BDD variétés`) sont prises en compte toutes les heures, ou immédiatement via le bouton ci-dessus.")

# Chargement initial
bdd = load_bdd()
varietes = load_varietes()
regions = load_regions()
liste_deps = sorted(bdd["Département"].unique().tolist())
annees_dispo = sorted(bdd["Année"].dropna().astype(int).unique().tolist())
geojson_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"

# --- ONGLETS PRINCIPAUX ---
tab1, tab2 = st.tabs(["🌡️ Potentiel Thermique Départemental", "🌱 Positionnement Variétal"])

# ==============================================================================
# ONGLET 1 : POTENTIEL THERMIQUE DÉPARTEMENTAL
# ==============================================================================
with tab1:
    st.header("1. Historique thermique pluriannuel local (2018 - 2026)")
    c1, c2, c3, c4 = st.columns(4)
    espece_t1 = c1.selectbox("Espèce", ["Maïs", "Sorgho"], key="t1_esp")
    dep_t1 = c2.selectbox("Département", liste_deps, index=liste_deps.index("Ille-et-Vilaine") if "Ille-et-Vilaine" in liste_deps else 0, key="t1_dep")
    semis_t1 = c3.date_input("Date de semis (JJ/MM)", value=datetime.date(2026, 4, 15), format="DD/MM/YYYY", key="t1_semis")
    recolte_t1 = c4.date_input("Date de récolte (JJ/MM)", value=datetime.date(2026, 9, 20), format="DD/MM/YYYY", key="t1_rec")

    col_uc_t1 = "Somme d°C/j Sorgho (base 8-34)" if espece_t1 == "Sorgho" else "Somme d°C/j"
    base_txt_t1 = "Base 8-34°C" if espece_t1 == "Sorgho" else "Base 6-30°C"
    st.caption(f"Base de calcul appliquée : **{base_txt_t1}**")

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
    k1.metric(f"Moyenne pluriannuelle - Cumul ({dep_t1})", f"{moy_somme:,.1f} °C/j".replace(",", " "))
    k2.metric("Moyenne journalière", f"{moy_jour:.2f} °C/j")
    st.dataframe(df_hist, use_container_width=True, hide_index=True)

    st.divider()
    st.header("2. Cumuls et analyse thermique comparative des 96 départements")
    d1, d2, d3, d4 = st.columns(4)
    espece_t2 = d1.selectbox("Espèce", ["Maïs", "Sorgho"], key="t2_esp")
    annee_t2 = d2.selectbox("Année à analyser", annees_dispo, index=len(annees_dispo)-1, key="t2_an")
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

    col_tab, col_map = st.columns([1.2, 1])
    with col_tab:
        st.dataframe(
            nat_df[["Code INSEE département", "Département", "Moyenne journalière (°C/j)", "Somme (°C/j)", "Écart vs Moyenne France (°C/j)"]],
            use_container_width=True, height=500, hide_index=True
        )
    with col_map:
        if not nat_df.empty:
            fig = px.choropleth(
                nat_df,
                geojson=geojson_url,
                locations="Code INSEE département",
                featureidkey="properties.code",
                color="Somme (°C/j)",
                hover_name="Département",
                color_continuous_scale=["#d73027", "#fee08b", "#1a9850"],
                title=f"Carte thermique {annee_t2} ({espece_t2})"
            )
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=500)
            st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# ONGLET 2 : POSITIONNEMENT VARIÉTAL
# ==============================================================================
with tab2:
    st.header("Paramètres de la variété")
    p1, p2, p3, p4 = st.columns(4)
    dep_v = p1.selectbox("Département (Analyse locale)", liste_deps, index=liste_deps.index("Morbihan") if "Morbihan" in liste_deps else 0, key="v_dep")
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
        p6.text_input("Objectif valorisation", value=dest_v, disabled=True)

    semis_v = p7.date_input("Date de semis", value=datetime.date(2026, 4, 20), format="DD/MM/YYYY", key="v_semis")
    recolte_cible_v = p8.date_input("Date de récolte cible", value=datetime.date(2026, 9, 15), format="DD/MM/YYYY", key="v_rec_cible")

    # Période d'analyse
    an_min, an_max = min(annees_dispo), max(annees_dispo)
    periode = st.slider("Période d'analyse (campagnes)", an_min, an_max, (an_min, an_max))

    # Récupération besoins thermiques
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

    st.subheader(f"1. Cycle phénologique local — {dep_v} ({periode[0]} - {periode[1]})")
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

        # Floraison
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

        # Récolte
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

    # Indicateurs moyens
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
    st.dataframe(pd.DataFrame(loc_rows), use_container_width=True, hide_index=True)

    # Vision nationale
    st.divider()
    st.subheader(f"2. Vision nationale de la variété {nom_var} (96 départements)")
    bdd_nat = bdd[(bdd["Année"] >= periode[0]) & (bdd["Année"] <= periode[1]) & (bdd["MoisJour"] >= semis_v.strftime("%m-%d"))]

    nat_var_rows = []
    for (code_dep, nom_dep), grp in bdd_nat.groupby(["Code INSEE département", "Département"]):
        d_f_list, d_r_list = [], []
        for an, g_an in grp.groupby("Année"):
            g_an = g_an.sort_values("Date")
            cum = g_an[col_uc_v].cumsum()
            d0 = g_an["Date"].iloc[0]
            if pd.notna(besoin_flo):
                hf = g_an[cum >= besoin_flo]
                if not hf.empty:
                    d_f_list.append((hf["Date"].iloc[0] - d0).days)
            if pd.notna(besoin_rec):
                hr = g_an[cum >= besoin_rec]
                if not hr.empty:
                    d_r_list.append((hr["Date"].iloc[0] - d0).days)

        mf = round(np.mean(d_f_list)) if len(d_f_list) > 0 else None
        mr = round(np.mean(d_r_list)) if len(d_r_list) > 0 else None
        date_f_est = (semis_v + datetime.timedelta(days=mf)).strftime("%d/%m/%Y") if mf else "Non atteint"

        if mr:
            dt_r_est = semis_v + datetime.timedelta(days=mr)
            if dt_r_est > recolte_cible_v:
                date_r_est, dur_r_est, statut_map = "Non atteint", None, 0
            else:
                date_r_est, dur_r_est, statut_map = dt_r_est.strftime("%d/%m/%Y"), mr, mr
        else:
            date_r_est, dur_r_est, statut_map = "Non atteint", None, 0

        nat_var_rows.append({
            "Code INSEE": code_dep,
            "Département": nom_dep,
            f"Date {lbl_flo.lower()} estimée": date_f_est,
            f"Durée {lbl_flo.lower()} (j)": mf if mf else np.nan,
            "Date récolte estimée": date_r_est,
            "Durée récolte (j)": dur_r_est if dur_r_est else np.nan,
            "Récoltable (j)": statut_map
        })

    df_nat_var = pd.DataFrame(nat_var_rows)
    col_vt, col_vm = st.columns([1.2, 1])
    with col_vt:
        st.dataframe(df_nat_var.drop(columns=["Récoltable (j)"]), use_container_width=True, height=500, hide_index=True)
    with col_vm:
        fig_v = px.choropleth(
            df_nat_var,
            geojson=geojson_url,
            locations="Code INSEE",
            featureidkey="properties.code",
            color="Durée récolte (j)",
            hover_name="Département",
            hover_data=["Date récolte estimée"],
            color_continuous_scale="YlGn_r",
            title=f"Durée semis-récolte estimée (jours) — {nom_var}"
        )
        fig_v.update_geos(fitbounds="locations", visible=False)
        fig_v.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=500)
        st.plotly_chart(fig_v, use_container_width=True)
