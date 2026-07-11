from calendar import monthrange
from datetime import date
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Budget personnel",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1280px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            letter-spacing: -0.02em;
        }

        [data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 12px;
            padding: 14px;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128, 128, 128, 0.18);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

FICHIER_DEPENSES = DATA_DIR / "depenses.csv"
FICHIER_MOIS = DATA_DIR / "budgets_mensuels.csv"
FICHIER_REMBOURSEMENTS = DATA_DIR / "remboursements_dette.csv"
FICHIER_RECURRENCES = DATA_DIR / "depenses_recurrentes.csv"
FICHIER_GENERAL = DATA_DIR / "parametres_generaux.csv"

COMPTES = ["Revolut", "Lydia"]

CATEGORIES_DEPENSES = [
    "Logement",
    "Courses",
    "Restaurant",
    "Transport",
    "Shopping",
    "Abonnements",
    "Santé",
    "Loisirs",
    "Voyage",
    "Soraya",
    "Nacer",
    "Malek",
    "Autre",
]

CATEGORIES_BUDGET = CATEGORIES_DEPENSES + ["Dette appartement"]

MOIS_FR = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}

PERIODES = list(pd.period_range("2026-07", "2027-07", freq="M"))


# ============================================================
# OUTILS
# ============================================================

def format_euros(montant: float) -> str:
    return f"{float(montant):,.2f} €".replace(",", " ")


def libelle_periode(periode: pd.Period) -> str:
    return f"{MOIS_FR[periode.month]} {periode.year}"


def lire_csv(fichier: Path, colonnes: list[str]) -> pd.DataFrame:
    if not fichier.exists():
        return pd.DataFrame(columns=colonnes)

    try:
        df = pd.read_csv(fichier)
    except (pd.errors.EmptyDataError, UnicodeDecodeError):
        return pd.DataFrame(columns=colonnes)

    for colonne in colonnes:
        if colonne not in df.columns:
            df[colonne] = None

    return df[colonnes]


def sauvegarder_csv(df: pd.DataFrame, fichier: Path) -> None:
    df.to_csv(fichier, index=False)


def convertir_dates(df: pd.DataFrame, colonne: str = "date") -> pd.DataFrame:
    if colonne in df.columns and not df.empty:
        df[colonne] = pd.to_datetime(df[colonne], errors="coerce")
    return df


def convertir_numerique(
    df: pd.DataFrame,
    colonnes: list[str],
) -> pd.DataFrame:
    for colonne in colonnes:
        if colonne in df.columns and not df.empty:
            df[colonne] = pd.to_numeric(df[colonne], errors="coerce")
    return df


def filtrer_periode(
    df: pd.DataFrame,
    periode: pd.Period,
    colonne_date: str = "date",
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    dates = pd.to_datetime(df[colonne_date], errors="coerce")
    return df.loc[dates.dt.to_period("M") == periode].copy()


# ============================================================
# DEPENSES
# ============================================================

COLONNES_DEPENSES = [
    "id",
    "date",
    "description",
    "categorie",
    "montant",
    "compte",
    "recurrence_id",
]


def charger_depenses() -> pd.DataFrame:
    df = lire_csv(FICHIER_DEPENSES, COLONNES_DEPENSES)
    df = convertir_dates(df)
    df = convertir_numerique(df, ["montant"])

    if not df.empty:
        df["id"] = df["id"].fillna("").astype(str)
        df["description"] = df["description"].fillna("").astype(str)
        df["categorie"] = df["categorie"].fillna("Autre").astype(str)
        df["compte"] = df["compte"].fillna("Revolut").astype(str)
        df["recurrence_id"] = df["recurrence_id"].fillna("").astype(str)
        df = df.dropna(subset=["date", "montant"]).reset_index(drop=True)

    return df


def sauvegarder_depenses(df: pd.DataFrame) -> None:
    copie = df.copy()

    if not copie.empty:
        copie["date"] = pd.to_datetime(copie["date"]).dt.strftime("%Y-%m-%d")

    sauvegarder_csv(copie, FICHIER_DEPENSES)


def ajouter_depense(
    df: pd.DataFrame,
    date_depense: date,
    description: str,
    categorie: str,
    montant: float,
    compte: str,
    recurrence_id: str = "",
) -> pd.DataFrame:
    nouvelle = pd.DataFrame(
        [{
            "id": uuid4().hex,
            "date": pd.Timestamp(date_depense),
            "description": description.strip(),
            "categorie": categorie,
            "montant": float(montant),
            "compte": compte,
            "recurrence_id": recurrence_id,
        }]
    )

    resultat = pd.concat([df, nouvelle], ignore_index=True)
    sauvegarder_depenses(resultat)
    return resultat


# ============================================================
# PARAMETRES MENSUELS
# ============================================================

COLONNES_MOIS_BASE = [
    "periode",
    "ca_revolut",
    "ca_lydia",
    "taux_urssaf",
    "compte_urssaf",
    "charges_pro",
    "compte_charges_pro",
    "objectif_epargne",
    "solde_initial_revolut",
    "solde_initial_lydia",
]

COLONNES_MOIS = COLONNES_MOIS_BASE + [
    f"budget_{categorie}" for categorie in CATEGORIES_BUDGET
]


def valeurs_mois_defaut(periode: pd.Period) -> dict:
    valeurs = {
        "periode": str(periode),
        "ca_revolut": 0.0,
        "ca_lydia": 0.0,
        "taux_urssaf": 28.0,
        "compte_urssaf": "Revolut",
        "charges_pro": 0.0,
        "compte_charges_pro": "Revolut",
        "objectif_epargne": 0.0,
        "solde_initial_revolut": 0.0,
        "solde_initial_lydia": 0.0,
    }

    for categorie in CATEGORIES_BUDGET:
        valeurs[f"budget_{categorie}"] = 0.0

    return valeurs


def charger_mois() -> pd.DataFrame:
    df = lire_csv(FICHIER_MOIS, COLONNES_MOIS)

    if not df.empty:
        df["periode"] = df["periode"].astype(str)

        colonnes_numeriques = [
            colonne
            for colonne in COLONNES_MOIS
            if colonne not in {
                "periode",
                "compte_urssaf",
                "compte_charges_pro",
            }
        ]

        df = convertir_numerique(df, colonnes_numeriques)
        df["compte_urssaf"] = (
            df["compte_urssaf"].fillna("Revolut").astype(str)
        )
        df["compte_charges_pro"] = (
            df["compte_charges_pro"].fillna("Revolut").astype(str)
        )
        df = df.drop_duplicates(subset=["periode"], keep="last")

    return df


def obtenir_parametres_mois(
    df_mois: pd.DataFrame,
    periode: pd.Period,
) -> dict:
    valeurs = valeurs_mois_defaut(periode)

    if df_mois.empty:
        return valeurs

    ligne = df_mois.loc[df_mois["periode"] == str(periode)]

    if ligne.empty:
        return valeurs

    donnees = ligne.iloc[-1].to_dict()

    for cle, valeur_defaut in valeurs.items():
        valeur = donnees.get(cle, valeur_defaut)

        if pd.isna(valeur):
            donnees[cle] = valeur_defaut

    return donnees


def enregistrer_parametres_mois(
    df_mois: pd.DataFrame,
    valeurs: dict,
) -> pd.DataFrame:
    periode = str(valeurs["periode"])
    df_mois = df_mois.loc[df_mois["periode"] != periode].copy()
    df_mois = pd.concat([df_mois, pd.DataFrame([valeurs])], ignore_index=True)

    ordre = {str(p): i for i, p in enumerate(PERIODES)}
    df_mois["_ordre"] = df_mois["periode"].map(ordre).fillna(9999)
    df_mois = df_mois.sort_values("_ordre").drop(columns="_ordre")

    sauvegarder_csv(df_mois, FICHIER_MOIS)
    return df_mois


# ============================================================
# DETTE APPARTEMENT
# ============================================================

COLONNES_REMBOURSEMENTS = [
    "id",
    "date",
    "description",
    "montant",
    "compte",
]


def charger_remboursements() -> pd.DataFrame:
    df = lire_csv(FICHIER_REMBOURSEMENTS, COLONNES_REMBOURSEMENTS)
    df = convertir_dates(df)
    df = convertir_numerique(df, ["montant"])

    if not df.empty:
        df["id"] = df["id"].fillna("").astype(str)
        df["description"] = (
            df["description"]
            .fillna("Remboursement dette appartement")
            .astype(str)
        )
        df["compte"] = df["compte"].fillna("Revolut").astype(str)
        df = df.dropna(subset=["date", "montant"]).reset_index(drop=True)

    return df


def sauvegarder_remboursements(df: pd.DataFrame) -> None:
    copie = df.copy()

    if not copie.empty:
        copie["date"] = pd.to_datetime(copie["date"]).dt.strftime("%Y-%m-%d")

    sauvegarder_csv(copie, FICHIER_REMBOURSEMENTS)


def charger_parametres_generaux() -> dict:
    defaut = {"dette_initiale": 2500.0}

    if not FICHIER_GENERAL.exists():
        return defaut

    try:
        df = pd.read_csv(FICHIER_GENERAL)
    except pd.errors.EmptyDataError:
        return defaut

    if df.empty:
        return defaut

    valeur = pd.to_numeric(
        pd.Series([df.iloc[0].get("dette_initiale")]),
        errors="coerce",
    ).iloc[0]

    if pd.notna(valeur):
        defaut["dette_initiale"] = float(valeur)

    return defaut


def sauvegarder_parametres_generaux(dette_initiale: float) -> None:
    sauvegarder_csv(
        pd.DataFrame([{"dette_initiale": float(dette_initiale)}]),
        FICHIER_GENERAL,
    )


# ============================================================
# DEPENSES RECURRENTES
# ============================================================

COLONNES_RECURRENCES = [
    "id",
    "description",
    "categorie",
    "montant",
    "compte",
    "jour",
    "debut",
    "fin",
    "active",
]


def charger_recurrences() -> pd.DataFrame:
    df = lire_csv(FICHIER_RECURRENCES, COLONNES_RECURRENCES)

    if not df.empty:
        df["id"] = df["id"].fillna("").astype(str)
        df["description"] = df["description"].fillna("").astype(str)
        df["categorie"] = df["categorie"].fillna("Autre").astype(str)
        df["compte"] = df["compte"].fillna("Revolut").astype(str)
        df["montant"] = pd.to_numeric(df["montant"], errors="coerce")
        df["jour"] = pd.to_numeric(df["jour"], errors="coerce")
        df["debut"] = df["debut"].fillna("2026-07").astype(str)
        df["fin"] = df["fin"].fillna("2027-07").astype(str)
        df["active"] = (
            df["active"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "oui"])
        )
        df = df.dropna(subset=["montant", "jour"]).reset_index(drop=True)

    return df


def sauvegarder_recurrences(df: pd.DataFrame) -> None:
    sauvegarder_csv(df, FICHIER_RECURRENCES)


def recurrence_valable(
    ligne: pd.Series,
    periode: pd.Period,
) -> bool:
    if not bool(ligne["active"]):
        return False

    debut = pd.Period(str(ligne["debut"]), freq="M")
    fin = pd.Period(str(ligne["fin"]), freq="M")
    return debut <= periode <= fin


def ajouter_recurrences_du_mois(
    depenses: pd.DataFrame,
    recurrents: pd.DataFrame,
    periode: pd.Period,
) -> tuple[pd.DataFrame, int]:
    ajoutees = 0

    for _, ligne in recurrents.iterrows():
        if not recurrence_valable(ligne, periode):
            continue

        recurrence_id = str(ligne["id"])
        deja_ajoutee = False

        if not depenses.empty:
            dates = pd.to_datetime(depenses["date"], errors="coerce")
            deja_ajoutee = (
                (depenses["recurrence_id"].astype(str) == recurrence_id)
                & (dates.dt.to_period("M") == periode)
            ).any()

        if deja_ajoutee:
            continue

        dernier_jour = monthrange(periode.year, periode.month)[1]
        jour = min(int(ligne["jour"]), dernier_jour)

        depenses = ajouter_depense(
            depenses,
            date(periode.year, periode.month, jour),
            str(ligne["description"]),
            str(ligne["categorie"]),
            float(ligne["montant"]),
            str(ligne["compte"]),
            recurrence_id=recurrence_id,
        )
        ajoutees += 1

    return depenses, ajoutees


# ============================================================
# CALCULS DE SOLDES
# ============================================================

def calculer_soldes_mois(
    periode: pd.Period,
    df_mois: pd.DataFrame,
    depenses: pd.DataFrame,
    remboursements: pd.DataFrame,
    cache: dict[str, dict],
) -> dict:
    cle = str(periode)

    if cle in cache:
        return cache[cle]

    parametres = obtenir_parametres_mois(df_mois, periode)

    if periode == PERIODES[0]:
        debut_revolut = float(parametres["solde_initial_revolut"])
        debut_lydia = float(parametres["solde_initial_lydia"])
    else:
        periode_precedente = periode - 1
        precedent = calculer_soldes_mois(
            periode_precedente,
            df_mois,
            depenses,
            remboursements,
            cache,
        )
        debut_revolut = precedent["fin_revolut"]
        debut_lydia = precedent["fin_lydia"]

    depenses_mois = filtrer_periode(depenses, periode)
    remboursements_mois = filtrer_periode(remboursements, periode)

    depenses_revolut = (
        depenses_mois.loc[
            depenses_mois["compte"] == "Revolut",
            "montant",
        ].sum()
        if not depenses_mois.empty
        else 0.0
    )

    depenses_lydia = (
        depenses_mois.loc[
            depenses_mois["compte"] == "Lydia",
            "montant",
        ].sum()
        if not depenses_mois.empty
        else 0.0
    )

    remboursements_revolut = (
        remboursements_mois.loc[
            remboursements_mois["compte"] == "Revolut",
            "montant",
        ].sum()
        if not remboursements_mois.empty
        else 0.0
    )

    remboursements_lydia = (
        remboursements_mois.loc[
            remboursements_mois["compte"] == "Lydia",
            "montant",
        ].sum()
        if not remboursements_mois.empty
        else 0.0
    )

    ca_revolut = float(parametres["ca_revolut"])
    ca_lydia = float(parametres["ca_lydia"])
    ca_total = ca_revolut + ca_lydia

    urssaf = ca_total * float(parametres["taux_urssaf"]) / 100
    charges_pro = float(parametres["charges_pro"])

    urssaf_revolut = (
        urssaf if parametres["compte_urssaf"] == "Revolut" else 0.0
    )
    urssaf_lydia = (
        urssaf if parametres["compte_urssaf"] == "Lydia" else 0.0
    )

    charges_revolut = (
        charges_pro
        if parametres["compte_charges_pro"] == "Revolut"
        else 0.0
    )
    charges_lydia = (
        charges_pro
        if parametres["compte_charges_pro"] == "Lydia"
        else 0.0
    )

    fin_revolut = (
        debut_revolut
        + ca_revolut
        - depenses_revolut
        - remboursements_revolut
        - urssaf_revolut
        - charges_revolut
    )

    fin_lydia = (
        debut_lydia
        + ca_lydia
        - depenses_lydia
        - remboursements_lydia
        - urssaf_lydia
        - charges_lydia
    )

    resultat = {
        "debut_revolut": debut_revolut,
        "debut_lydia": debut_lydia,
        "ca_revolut": ca_revolut,
        "ca_lydia": ca_lydia,
        "ca_total": ca_total,
        "urssaf": urssaf,
        "charges_pro": charges_pro,
        "depenses_revolut": depenses_revolut,
        "depenses_lydia": depenses_lydia,
        "remboursements_revolut": remboursements_revolut,
        "remboursements_lydia": remboursements_lydia,
        "fin_revolut": fin_revolut,
        "fin_lydia": fin_lydia,
        "fin_total": fin_revolut + fin_lydia,
        "depenses_total": depenses_revolut + depenses_lydia,
        "remboursements_total": (
            remboursements_revolut + remboursements_lydia
        ),
    }

    cache[cle] = resultat
    return resultat


# ============================================================
# CHARGEMENT
# ============================================================

depenses = charger_depenses()
df_mois = charger_mois()
remboursements = charger_remboursements()
recurrents = charger_recurrences()
parametres_generaux = charger_parametres_generaux()


# ============================================================
# PERIODE
# ============================================================

st.sidebar.title("Budget personnel")

periode_choisie = st.sidebar.selectbox(
    "Mois",
    options=PERIODES,
    index=0,
    format_func=libelle_periode,
)

parametres_mois = obtenir_parametres_mois(
    df_mois,
    periode_choisie,
)


# ============================================================
# PARAMETRES DU MOIS
# ============================================================

st.sidebar.divider()
st.sidebar.subheader("Revenus et charges du mois")

ca_revolut = st.sidebar.number_input(
    "Chiffre d’affaires reçu sur Revolut",
    min_value=0.0,
    value=float(parametres_mois["ca_revolut"]),
    step=50.0,
    format="%.2f",
)

ca_lydia = st.sidebar.number_input(
    "Chiffre d’affaires reçu sur Lydia",
    min_value=0.0,
    value=float(parametres_mois["ca_lydia"]),
    step=50.0,
    format="%.2f",
)

taux_urssaf = st.sidebar.number_input(
    "Taux URSSAF estimé (%)",
    min_value=0.0,
    max_value=100.0,
    value=float(parametres_mois["taux_urssaf"]),
    step=0.1,
    format="%.1f",
)

compte_urssaf = st.sidebar.selectbox(
    "Compte utilisé pour l’URSSAF",
    COMPTES,
    index=COMPTES.index(
        str(parametres_mois["compte_urssaf"])
        if str(parametres_mois["compte_urssaf"]) in COMPTES
        else "Revolut"
    ),
)

charges_pro = st.sidebar.number_input(
    "Autres charges professionnelles",
    min_value=0.0,
    value=float(parametres_mois["charges_pro"]),
    step=10.0,
    format="%.2f",
)

compte_charges_pro = st.sidebar.selectbox(
    "Compte utilisé pour les charges pro",
    COMPTES,
    index=COMPTES.index(
        str(parametres_mois["compte_charges_pro"])
        if str(parametres_mois["compte_charges_pro"]) in COMPTES
        else "Revolut"
    ),
)

objectif_epargne = st.sidebar.number_input(
    "Objectif d’épargne du mois",
    min_value=0.0,
    value=float(parametres_mois["objectif_epargne"]),
    step=50.0,
    format="%.2f",
)

if periode_choisie == PERIODES[0]:
    st.sidebar.divider()
    st.sidebar.subheader("Soldes de départ en juillet 2026")

    solde_initial_revolut = st.sidebar.number_input(
        "Solde Revolut au début de juillet",
        value=float(parametres_mois["solde_initial_revolut"]),
        step=50.0,
        format="%.2f",
    )

    solde_initial_lydia = st.sidebar.number_input(
        "Solde Lydia au début de juillet",
        value=float(parametres_mois["solde_initial_lydia"]),
        step=50.0,
        format="%.2f",
    )
else:
    solde_initial_revolut = float(
        parametres_mois["solde_initial_revolut"]
    )
    solde_initial_lydia = float(
        parametres_mois["solde_initial_lydia"]
    )

st.sidebar.divider()
st.sidebar.subheader("Budgets par catégorie")

budgets = {}

for categorie in CATEGORIES_BUDGET:
    budgets[categorie] = st.sidebar.number_input(
        categorie,
        min_value=0.0,
        value=float(parametres_mois.get(f"budget_{categorie}", 0.0)),
        step=10.0,
        format="%.2f",
        key=f"budget_{periode_choisie}_{categorie}",
    )

if st.sidebar.button(
    "Enregistrer ce mois",
    use_container_width=True,
):
    valeurs = {
        "periode": str(periode_choisie),
        "ca_revolut": ca_revolut,
        "ca_lydia": ca_lydia,
        "taux_urssaf": taux_urssaf,
        "compte_urssaf": compte_urssaf,
        "charges_pro": charges_pro,
        "compte_charges_pro": compte_charges_pro,
        "objectif_epargne": objectif_epargne,
        "solde_initial_revolut": solde_initial_revolut,
        "solde_initial_lydia": solde_initial_lydia,
    }

    for categorie, montant_budget in budgets.items():
        valeurs[f"budget_{categorie}"] = montant_budget

    df_mois = enregistrer_parametres_mois(df_mois, valeurs)
    st.sidebar.success("Mois enregistré.")
    st.rerun()


# ============================================================
# CALCULS PRINCIPAUX
# ============================================================

cache_soldes = {}

soldes = calculer_soldes_mois(
    periode_choisie,
    df_mois,
    depenses,
    remboursements,
    cache_soldes,
)

depenses_mois = filtrer_periode(depenses, periode_choisie)
remboursements_mois = filtrer_periode(
    remboursements,
    periode_choisie,
)

total_deja_rembourse = (
    remboursements["montant"].sum()
    if not remboursements.empty
    else 0.0
)

dette_initiale = float(parametres_generaux["dette_initiale"])
dette_restante = max(dette_initiale - total_deja_rembourse, 0.0)

reste_apres_objectif = soldes["fin_total"] - objectif_epargne


# ============================================================
# INTERFACE
# ============================================================

st.title("Budget personnel")
st.caption(
    "Suivi mensuel de juillet 2026 à juillet 2027, avec report automatique des soldes."
)

onglet_accueil, onglet_depenses, onglet_dette, onglet_recurrences, onglet_historique = st.tabs(
    [
        "Tableau de bord",
        "Dépenses",
        "Dette appartement",
        "Dépenses récurrentes",
        "Historique",
    ]
)


# ============================================================
# TABLEAU DE BORD
# ============================================================

with onglet_accueil:
    st.subheader(libelle_periode(periode_choisie))

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Solde de début total",
        format_euros(
            soldes["debut_revolut"]
            + soldes["debut_lydia"]
        ),
    )

    col2.metric(
        "Chiffre d’affaires encaissé",
        format_euros(soldes["ca_total"]),
    )

    col3.metric(
        "Total des sorties",
        format_euros(
            soldes["depenses_total"]
            + soldes["remboursements_total"]
            + soldes["urssaf"]
            + soldes["charges_pro"]
        ),
    )

    col4.metric(
        "Solde de fin total",
        format_euros(soldes["fin_total"]),
    )

    st.divider()

    col_revolut, col_lydia = st.columns(2)

    with col_revolut:
        st.subheader("Revolut")
        a, b, c = st.columns(3)
        a.metric("Début", format_euros(soldes["debut_revolut"]))
        b.metric("Revenus", format_euros(soldes["ca_revolut"]))
        c.metric("Fin", format_euros(soldes["fin_revolut"]))

    with col_lydia:
        st.subheader("Lydia")
        a, b, c = st.columns(3)
        a.metric("Début", format_euros(soldes["debut_lydia"]))
        b.metric("Revenus", format_euros(soldes["ca_lydia"]))
        c.metric("Fin", format_euros(soldes["fin_lydia"]))

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("URSSAF à réserver", format_euros(soldes["urssaf"]))
    col2.metric("Charges professionnelles", format_euros(soldes["charges_pro"]))
    col3.metric("Dépenses personnelles", format_euros(soldes["depenses_total"]))
    col4.metric("Dette remboursée ce mois", format_euros(soldes["remboursements_total"]))

    st.subheader("Objectif d’épargne")

    if objectif_epargne <= 0:
        st.info("Aucun objectif d’épargne défini pour ce mois.")
    elif soldes["fin_total"] >= objectif_epargne:
        st.success(
            f"Objectif atteignable. Après avoir mis de côté "
            f"{format_euros(objectif_epargne)}, il resterait "
            f"{format_euros(reste_apres_objectif)}."
        )
        st.progress(1.0)
    else:
        progression = max(soldes["fin_total"] / objectif_epargne, 0.0)
        st.warning(
            f"Il manque {format_euros(objectif_epargne - soldes['fin_total'])} "
            "pour atteindre l’objectif."
        )
        st.progress(min(progression, 1.0))

    st.subheader("Budgets par catégorie")

    resultats_budgets = []

    for categorie in CATEGORIES_BUDGET:
        if categorie == "Dette appartement":
            depense_categorie = soldes["remboursements_total"]
        else:
            depense_categorie = (
                depenses_mois.loc[
                    depenses_mois["categorie"] == categorie,
                    "montant",
                ].sum()
                if not depenses_mois.empty
                else 0.0
            )

        budget = float(budgets[categorie])
        reste = budget - depense_categorie

        if budget > 0 or depense_categorie > 0:
            resultats_budgets.append(
                {
                    "Catégorie": categorie,
                    "Budget": budget,
                    "Dépensé": depense_categorie,
                    "Reste": reste,
                }
            )

    if not resultats_budgets:
        st.info("Aucun budget ni dépense enregistré pour ce mois.")
    else:
        df_budgets = pd.DataFrame(resultats_budgets)

        st.dataframe(
            df_budgets,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Budget": st.column_config.NumberColumn(
                    "Budget",
                    format="%.2f €",
                ),
                "Dépensé": st.column_config.NumberColumn(
                    "Dépensé",
                    format="%.2f €",
                ),
                "Reste": st.column_config.NumberColumn(
                    "Reste",
                    format="%.2f €",
                ),
            },
        )

    st.subheader("Répartition des dépenses")

    graphique = (
        depenses_mois
        .groupby("categorie")["montant"]
        .sum()
        .sort_values(ascending=False)
        if not depenses_mois.empty
        else pd.Series(dtype=float)
    )

    if soldes["remboursements_total"] > 0:
        graphique.loc["Dette appartement"] = soldes["remboursements_total"]

    if graphique.empty:
        st.info("Aucune dépense enregistrée pour ce mois.")
    else:
        st.bar_chart(graphique)


# ============================================================
# DEPENSES
# ============================================================

with onglet_depenses:
    st.subheader("Ajouter une dépense")

    with st.form("formulaire_depense", clear_on_submit=True):
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            date_depense = st.date_input(
                "Date",
                value=date(
                    periode_choisie.year,
                    periode_choisie.month,
                    1,
                ),
            )

        with col2:
            description = st.text_input(
                "Description",
                placeholder="Exemple : Carrefour",
            )

        with col3:
            categorie = st.selectbox(
                "Catégorie",
                CATEGORIES_DEPENSES,
            )

        with col4:
            montant = st.number_input(
                "Montant",
                min_value=0.0,
                step=1.0,
                format="%.2f",
            )

        with col5:
            compte = st.selectbox(
                "Compte",
                COMPTES,
            )

        ajouter = st.form_submit_button(
            "Ajouter",
            use_container_width=True,
        )

    if ajouter:
        if not description.strip():
            st.error("Ajoute une description.")
        elif montant <= 0:
            st.error("Le montant doit être supérieur à 0 €.")
        else:
            depenses = ajouter_depense(
                depenses,
                date_depense,
                description,
                categorie,
                montant,
                compte,
            )
            st.success("Dépense ajoutée.")
            st.rerun()

    st.subheader("Dépenses du mois")

    if depenses_mois.empty:
        st.info("Aucune dépense pour ce mois.")
    else:
        tableau = depenses_mois.copy()
        tableau["date"] = tableau["date"].dt.strftime("%d/%m/%Y")
        tableau = tableau.rename(
            columns={
                "date": "Date",
                "description": "Description",
                "categorie": "Catégorie",
                "montant": "Montant",
                "compte": "Compte",
            }
        )

        st.dataframe(
            tableau[
                [
                    "Date",
                    "Description",
                    "Catégorie",
                    "Montant",
                    "Compte",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Montant": st.column_config.NumberColumn(
                    "Montant",
                    format="%.2f €",
                ),
            },
        )

        st.subheader("Supprimer une dépense")

        options = {}

        for index, ligne in depenses_mois.iterrows():
            texte = (
                f"{ligne['date'].strftime('%d/%m/%Y')} — "
                f"{ligne['description']} — "
                f"{format_euros(ligne['montant'])} — "
                f"{ligne['compte']}"
            )
            options[texte] = index

        selection = st.selectbox(
            "Dépense",
            options=list(options.keys()),
        )

        confirmation = st.checkbox(
            "Je confirme la suppression.",
            key="confirmer_suppression_depense",
        )

        if st.button(
            "Supprimer la dépense",
            disabled=not confirmation,
        ):
            depenses = depenses.drop(
                index=options[selection]
            ).reset_index(drop=True)
            sauvegarder_depenses(depenses)
            st.success("Dépense supprimée.")
            st.rerun()


# ============================================================
# DETTE
# ============================================================

with onglet_dette:
    st.subheader("Dette appartement")

    nouvelle_dette_initiale = st.number_input(
        "Montant initial dû aux parents",
        min_value=0.0,
        value=float(dette_initiale),
        step=50.0,
        format="%.2f",
    )

    if st.button("Enregistrer le montant de la dette"):
        sauvegarder_parametres_generaux(nouvelle_dette_initiale)
        st.success("Dette initiale enregistrée.")
        st.rerun()

    progression_dette = (
        total_deja_rembourse / dette_initiale
        if dette_initiale > 0
        else 0.0
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Dette initiale", format_euros(dette_initiale))
    col2.metric("Déjà remboursé", format_euros(total_deja_rembourse))
    col3.metric("Reste à rembourser", format_euros(dette_restante))

    if dette_initiale > 0:
        st.progress(min(max(progression_dette, 0.0), 1.0))

    st.subheader("Ajouter un remboursement")

    with st.form("formulaire_remboursement", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            date_remboursement = st.date_input(
                "Date",
                value=date(
                    periode_choisie.year,
                    periode_choisie.month,
                    1,
                ),
                key="date_remboursement",
            )

        with col2:
            description_remboursement = st.text_input(
                "Description",
                value="Remboursement dette appartement",
            )

        with col3:
            montant_remboursement = st.number_input(
                "Montant",
                min_value=0.0,
                step=50.0,
                format="%.2f",
                key="montant_remboursement",
            )

        with col4:
            compte_remboursement = st.selectbox(
                "Compte",
                COMPTES,
                key="compte_remboursement",
            )

        ajouter_remboursement = st.form_submit_button(
            "Ajouter le remboursement",
            use_container_width=True,
        )

    if ajouter_remboursement:
        if montant_remboursement <= 0:
            st.error("Le montant doit être supérieur à 0 €.")
        elif montant_remboursement > dette_restante:
            st.error(
                f"Le montant dépasse la dette restante de "
                f"{format_euros(dette_restante)}."
            )
        else:
            nouveau = pd.DataFrame(
                [{
                    "id": uuid4().hex,
                    "date": pd.Timestamp(date_remboursement),
                    "description": (
                        description_remboursement.strip()
                        or "Remboursement dette appartement"
                    ),
                    "montant": float(montant_remboursement),
                    "compte": compte_remboursement,
                }]
            )

            remboursements = pd.concat(
                [remboursements, nouveau],
                ignore_index=True,
            )
            sauvegarder_remboursements(remboursements)
            st.success("Remboursement ajouté.")
            st.rerun()

    st.subheader("Historique des remboursements")

    if remboursements.empty:
        st.info("Aucun remboursement enregistré.")
    else:
        historique = remboursements.copy()
        historique["date"] = historique["date"].dt.strftime("%d/%m/%Y")
        historique = historique.rename(
            columns={
                "date": "Date",
                "description": "Description",
                "montant": "Montant",
                "compte": "Compte",
            }
        )

        st.dataframe(
            historique[
                [
                    "Date",
                    "Description",
                    "Montant",
                    "Compte",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Montant": st.column_config.NumberColumn(
                    "Montant",
                    format="%.2f €",
                ),
            },
        )

        st.subheader("Supprimer un remboursement")

        options = {}

        for index, ligne in remboursements.iterrows():
            texte = (
                f"{ligne['date'].strftime('%d/%m/%Y')} — "
                f"{ligne['description']} — "
                f"{format_euros(ligne['montant'])} — "
                f"{ligne['compte']}"
            )
            options[texte] = index

        selection = st.selectbox(
            "Remboursement",
            options=list(options.keys()),
        )

        confirmation = st.checkbox(
            "Je confirme la suppression.",
            key="confirmer_suppression_remboursement",
        )

        if st.button(
            "Supprimer le remboursement",
            disabled=not confirmation,
        ):
            remboursements = remboursements.drop(
                index=options[selection]
            ).reset_index(drop=True)
            sauvegarder_remboursements(remboursements)
            st.success("Remboursement supprimé.")
            st.rerun()


# ============================================================
# RECURRENCES
# ============================================================

with onglet_recurrences:
    st.subheader("Ajouter une dépense récurrente")

    with st.form("formulaire_recurrence", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            description_recurrence = st.text_input(
                "Description",
                placeholder="Exemple : Loyer",
            )

        with col2:
            categorie_recurrence = st.selectbox(
                "Catégorie",
                CATEGORIES_DEPENSES,
                key="categorie_recurrence",
            )

        with col3:
            montant_recurrence = st.number_input(
                "Montant",
                min_value=0.0,
                step=10.0,
                format="%.2f",
                key="montant_recurrence",
            )

        with col4:
            compte_recurrence = st.selectbox(
                "Compte",
                COMPTES,
                key="compte_recurrence",
            )

        col5, col6, col7 = st.columns(3)

        with col5:
            jour_recurrence = st.number_input(
                "Jour du mois",
                min_value=1,
                max_value=31,
                value=1,
                step=1,
            )

        with col6:
            debut_recurrence = st.selectbox(
                "Premier mois",
                PERIODES,
                index=0,
                format_func=libelle_periode,
                key="debut_recurrence",
            )

        with col7:
            fin_recurrence = st.selectbox(
                "Dernier mois",
                PERIODES,
                index=len(PERIODES) - 1,
                format_func=libelle_periode,
                key="fin_recurrence",
            )

        ajouter_recurrence = st.form_submit_button(
            "Créer la dépense récurrente",
            use_container_width=True,
        )

    if ajouter_recurrence:
        if not description_recurrence.strip():
            st.error("Ajoute une description.")
        elif montant_recurrence <= 0:
            st.error("Le montant doit être supérieur à 0 €.")
        elif debut_recurrence > fin_recurrence:
            st.error("Le premier mois doit être avant le dernier mois.")
        else:
            nouvelle = pd.DataFrame(
                [{
                    "id": uuid4().hex,
                    "description": description_recurrence.strip(),
                    "categorie": categorie_recurrence,
                    "montant": float(montant_recurrence),
                    "compte": compte_recurrence,
                    "jour": int(jour_recurrence),
                    "debut": str(debut_recurrence),
                    "fin": str(fin_recurrence),
                    "active": True,
                }]
            )

            recurrents = pd.concat(
                [recurrents, nouvelle],
                ignore_index=True,
            )
            sauvegarder_recurrences(recurrents)
            st.success("Dépense récurrente créée.")
            st.rerun()

    if st.button(
        f"Ajouter les récurrences de {libelle_periode(periode_choisie)}"
    ):
        depenses, nombre = ajouter_recurrences_du_mois(
            depenses,
            recurrents,
            periode_choisie,
        )

        if nombre == 0:
            st.info(
                "Aucune nouvelle dépense récurrente à ajouter pour ce mois."
            )
        else:
            st.success(f"{nombre} dépense(s) récurrente(s) ajoutée(s).")
        st.rerun()

    st.subheader("Liste des dépenses récurrentes")

    if recurrents.empty:
        st.info("Aucune dépense récurrente.")
    else:
        affichage = recurrents.copy()
        affichage["debut"] = affichage["debut"].apply(
            lambda x: libelle_periode(pd.Period(str(x), freq="M"))
        )
        affichage["fin"] = affichage["fin"].apply(
            lambda x: libelle_periode(pd.Period(str(x), freq="M"))
        )
        affichage = affichage.rename(
            columns={
                "description": "Description",
                "categorie": "Catégorie",
                "montant": "Montant",
                "compte": "Compte",
                "jour": "Jour",
                "debut": "Début",
                "fin": "Fin",
                "active": "Active",
            }
        )

        st.dataframe(
            affichage[
                [
                    "Description",
                    "Catégorie",
                    "Montant",
                    "Compte",
                    "Jour",
                    "Début",
                    "Fin",
                    "Active",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Montant": st.column_config.NumberColumn(
                    "Montant",
                    format="%.2f €",
                ),
            },
        )

        options = {
            f"{ligne['description']} — {format_euros(ligne['montant'])} — {ligne['compte']}": index
            for index, ligne in recurrents.iterrows()
        }

        selection = st.selectbox(
            "Dépense récurrente à supprimer",
            options=list(options.keys()),
        )

        confirmation = st.checkbox(
            "Je confirme la suppression.",
            key="confirmer_suppression_recurrence",
        )

        if st.button(
            "Supprimer la dépense récurrente",
            disabled=not confirmation,
        ):
            recurrents = recurrents.drop(
                index=options[selection]
            ).reset_index(drop=True)
            sauvegarder_recurrences(recurrents)
            st.success("Dépense récurrente supprimée.")
            st.rerun()


# ============================================================
# HISTORIQUE
# ============================================================

with onglet_historique:
    st.subheader("Historique mensuel")

    lignes_historique = []
    cache_historique = {}

    for periode in PERIODES:
        valeurs = calculer_soldes_mois(
            periode,
            df_mois,
            depenses,
            remboursements,
            cache_historique,
        )

        lignes_historique.append(
            {
                "Mois": libelle_periode(periode),
                "Solde début": (
                    valeurs["debut_revolut"]
                    + valeurs["debut_lydia"]
                ),
                "CA encaissé": valeurs["ca_total"],
                "URSSAF": valeurs["urssaf"],
                "Charges pro": valeurs["charges_pro"],
                "Dépenses": valeurs["depenses_total"],
                "Dette remboursée": valeurs["remboursements_total"],
                "Solde fin": valeurs["fin_total"],
            }
        )

    historique = pd.DataFrame(lignes_historique)

    st.dataframe(
        historique,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Solde début": st.column_config.NumberColumn(
                "Solde début",
                format="%.2f €",
            ),
            "CA encaissé": st.column_config.NumberColumn(
                "CA encaissé",
                format="%.2f €",
            ),
            "URSSAF": st.column_config.NumberColumn(
                "URSSAF",
                format="%.2f €",
            ),
            "Charges pro": st.column_config.NumberColumn(
                "Charges pro",
                format="%.2f €",
            ),
            "Dépenses": st.column_config.NumberColumn(
                "Dépenses",
                format="%.2f €",
            ),
            "Dette remboursée": st.column_config.NumberColumn(
                "Dette remboursée",
                format="%.2f €",
            ),
            "Solde fin": st.column_config.NumberColumn(
                "Solde fin",
                format="%.2f €",
            ),
        },
    )

    graphique_historique = historique.set_index("Mois")["Solde fin"]
    st.line_chart(graphique_historique)

    fichier_export = historique.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "Télécharger l’historique en CSV",
        data=fichier_export,
        file_name="historique_budget.csv",
        mime="text/csv",
        use_container_width=True,
    )