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
    page_title="Gestion Budget Freelance",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1150px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            letter-spacing: -0.02em;
        }

        [data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 14px;
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

CATEGORIES = [
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

CATEGORIES_BUDGET = CATEGORIES + ["Dette appartement"]

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


def filtrer_periode(
    df: pd.DataFrame,
    periode: pd.Period,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    dates = pd.to_datetime(df["date"], errors="coerce")
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
    "recurrence_id",
]


def charger_depenses() -> pd.DataFrame:
    df = lire_csv(FICHIER_DEPENSES, COLONNES_DEPENSES)

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["montant"] = pd.to_numeric(df["montant"], errors="coerce")
        df["id"] = df["id"].fillna("").astype(str)
        df["description"] = df["description"].fillna("").astype(str)
        df["categorie"] = df["categorie"].fillna("Autre").astype(str)
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
    recurrence_id: str = "",
) -> pd.DataFrame:
    nouvelle = pd.DataFrame(
        [{
            "id": uuid4().hex,
            "date": pd.Timestamp(date_depense),
            "description": description.strip(),
            "categorie": categorie,
            "montant": float(montant),
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
    "chiffre_affaires",
    "taux_urssaf",
    "loyer",
    "objectif_epargne",
    "solde_initial_revolut",
]

COLONNES_MOIS = COLONNES_MOIS_BASE + [
    f"budget_{categorie}" for categorie in CATEGORIES_BUDGET
]


def valeurs_mois_defaut(periode: pd.Period) -> dict:
    valeurs = {
        "periode": str(periode),
        "chiffre_affaires": 0.0,
        "taux_urssaf": 28.0,
        "loyer": 0.0,
        "objectif_epargne": 0.0,
        "solde_initial_revolut": 0.0,
    }

    for categorie in CATEGORIES_BUDGET:
        valeurs[f"budget_{categorie}"] = 0.0

    return valeurs


def charger_mois() -> pd.DataFrame:
    df = lire_csv(FICHIER_MOIS, COLONNES_MOIS)

    if not df.empty:
        df["periode"] = df["periode"].astype(str)

        for colonne in COLONNES_MOIS:
            if colonne != "periode":
                df[colonne] = pd.to_numeric(
                    df[colonne],
                    errors="coerce",
                )

        df = df.drop_duplicates(
            subset=["periode"],
            keep="last",
        )

    return df


def obtenir_parametres_mois(
    df_mois: pd.DataFrame,
    periode: pd.Period,
) -> dict:
    valeurs = valeurs_mois_defaut(periode)

    if df_mois.empty:
        return valeurs

    ligne = df_mois.loc[
        df_mois["periode"] == str(periode)
    ]

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

    df_mois = df_mois.loc[
        df_mois["periode"] != periode
    ].copy()

    df_mois = pd.concat(
        [df_mois, pd.DataFrame([valeurs])],
        ignore_index=True,
    )

    ordre = {
        str(periode): index
        for index, periode in enumerate(PERIODES)
    }

    df_mois["_ordre"] = (
        df_mois["periode"]
        .map(ordre)
        .fillna(9999)
    )

    df_mois = (
        df_mois
        .sort_values("_ordre")
        .drop(columns="_ordre")
    )

    sauvegarder_csv(
        df_mois,
        FICHIER_MOIS,
    )

    return df_mois


# ============================================================
# DETTE APPARTEMENT
# ============================================================

COLONNES_REMBOURSEMENTS = [
    "id",
    "date",
    "description",
    "montant",
]


def charger_remboursements() -> pd.DataFrame:
    df = lire_csv(
        FICHIER_REMBOURSEMENTS,
        COLONNES_REMBOURSEMENTS,
    )

    if not df.empty:
        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        df["montant"] = pd.to_numeric(
            df["montant"],
            errors="coerce",
        )

        df["id"] = df["id"].fillna("").astype(str)

        df["description"] = (
            df["description"]
            .fillna("Remboursement dette appartement")
            .astype(str)
        )

        df = df.dropna(
            subset=["date", "montant"]
        ).reset_index(drop=True)

    return df


def sauvegarder_remboursements(
    df: pd.DataFrame,
) -> None:
    copie = df.copy()

    if not copie.empty:
        copie["date"] = (
            pd.to_datetime(copie["date"])
            .dt.strftime("%Y-%m-%d")
        )

    sauvegarder_csv(
        copie,
        FICHIER_REMBOURSEMENTS,
    )


def charger_parametres_generaux() -> dict:
    defaut = {
        "dette_initiale": 2500.0,
    }

    if not FICHIER_GENERAL.exists():
        return defaut

    try:
        df = pd.read_csv(FICHIER_GENERAL)
    except pd.errors.EmptyDataError:
        return defaut

    if df.empty:
        return defaut

    valeur = pd.to_numeric(
        pd.Series(
            [df.iloc[0].get("dette_initiale")]
        ),
        errors="coerce",
    ).iloc[0]

    if pd.notna(valeur):
        defaut["dette_initiale"] = float(valeur)

    return defaut


def sauvegarder_parametres_generaux(
    dette_initiale: float,
) -> None:
    sauvegarder_csv(
        pd.DataFrame(
            [{
                "dette_initiale": float(
                    dette_initiale
                )
            }]
        ),
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
    "jour",
    "debut",
    "fin",
    "active",
]


def charger_recurrences() -> pd.DataFrame:
    df = lire_csv(
        FICHIER_RECURRENCES,
        COLONNES_RECURRENCES,
    )

    if not df.empty:
        df["id"] = df["id"].fillna("").astype(str)
        df["description"] = df["description"].fillna("").astype(str)
        df["categorie"] = df["categorie"].fillna("Autre").astype(str)

        df["montant"] = pd.to_numeric(
            df["montant"],
            errors="coerce",
        )

        df["jour"] = pd.to_numeric(
            df["jour"],
            errors="coerce",
        )

        df["debut"] = (
            df["debut"]
            .fillna("2026-07")
            .astype(str)
        )

        df["fin"] = (
            df["fin"]
            .fillna("2027-07")
            .astype(str)
        )

        df["active"] = (
            df["active"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "oui"])
        )

        df = df.dropna(
            subset=["montant", "jour"]
        ).reset_index(drop=True)

    return df


def sauvegarder_recurrences(
    df: pd.DataFrame,
) -> None:
    sauvegarder_csv(
        df,
        FICHIER_RECURRENCES,
    )


def recurrence_valable(
    ligne: pd.Series,
    periode: pd.Period,
) -> bool:
    if not bool(ligne["active"]):
        return False

    debut = pd.Period(
        str(ligne["debut"]),
        freq="M",
    )

    fin = pd.Period(
        str(ligne["fin"]),
        freq="M",
    )

    return debut <= periode <= fin


def ajouter_recurrences_automatiquement(
    depenses: pd.DataFrame,
    recurrents: pd.DataFrame,
    periode: pd.Period,
) -> tuple[pd.DataFrame, int]:
    nombre_ajoute = 0

    for _, ligne in recurrents.iterrows():
        if not recurrence_valable(
            ligne,
            periode,
        ):
            continue

        recurrence_id = str(ligne["id"])
        deja_ajoutee = False

        if not depenses.empty:
            dates = pd.to_datetime(
                depenses["date"],
                errors="coerce",
            )

            deja_ajoutee = (
                (
                    depenses["recurrence_id"]
                    .astype(str)
                    == recurrence_id
                )
                & (
                    dates.dt.to_period("M")
                    == periode
                )
            ).any()

        if deja_ajoutee:
            continue

        dernier_jour = monthrange(
            periode.year,
            periode.month,
        )[1]

        jour = min(
            int(ligne["jour"]),
            dernier_jour,
        )

        depenses = ajouter_depense(
            depenses,
            date(
                periode.year,
                periode.month,
                jour,
            ),
            str(ligne["description"]),
            str(ligne["categorie"]),
            float(ligne["montant"]),
            recurrence_id=recurrence_id,
        )

        nombre_ajoute += 1

    return depenses, nombre_ajoute


# ============================================================
# CALCUL DU BUDGET
# ============================================================

def calculer_mois(
    periode: pd.Period,
    df_mois: pd.DataFrame,
    depenses: pd.DataFrame,
    remboursements: pd.DataFrame,
    cache: dict[str, dict],
) -> dict:
    cle = str(periode)

    if cle in cache:
        return cache[cle]

    parametres = obtenir_parametres_mois(
        df_mois,
        periode,
    )

    if periode == PERIODES[0]:
        solde_reporte = float(
            parametres["solde_initial_revolut"]
        )
    else:
        precedent = calculer_mois(
            periode - 1,
            df_mois,
            depenses,
            remboursements,
            cache,
        )

        solde_reporte = precedent[
            "solde_final_revolut"
        ]

    depenses_mois = filtrer_periode(
        depenses,
        periode,
    )

    remboursements_mois = filtrer_periode(
        remboursements,
        periode,
    )

    total_depenses = (
        depenses_mois["montant"].sum()
        if not depenses_mois.empty
        else 0.0
    )

    total_remboursements = (
        remboursements_mois["montant"].sum()
        if not remboursements_mois.empty
        else 0.0
    )

    chiffre_affaires = float(
        parametres["chiffre_affaires"]
    )

    urssaf = (
        chiffre_affaires
        * float(parametres["taux_urssaf"])
        / 100
    )

    loyer = float(
        parametres["loyer"]
    )

    virement_vers_revolut = max(
        chiffre_affaires
        - urssaf
        - loyer,
        0.0,
    )

    solde_final_revolut = (
        solde_reporte
        + virement_vers_revolut
        - total_depenses
        - total_remboursements
    )

    resultat = {
        "solde_reporte": solde_reporte,
        "chiffre_affaires": chiffre_affaires,
        "urssaf": urssaf,
        "loyer": loyer,
        "virement_vers_revolut": (
            virement_vers_revolut
        ),
        "total_depenses": total_depenses,
        "total_remboursements": (
            total_remboursements
        ),
        "solde_final_revolut": (
            solde_final_revolut
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
# TITRE
# ============================================================

st.title("Gestion Budget Freelance")

st.subheader(
    "Suivi simple de mes revenus, "
    "de mes dépenses et de mon épargne"
)

st.caption(
    "Le chiffre d’affaires arrive sur Lydia. "
    "L’URSSAF et le loyer sont retirés automatiquement, "
    "puis le reste est transféré vers Revolut."
)


# ============================================================
# BARRE LATERALE
# ============================================================

st.sidebar.title("Mois affiché")

periode_choisie = st.sidebar.selectbox(
    "Période",
    options=PERIODES,
    index=0,
    format_func=libelle_periode,
)

parametres_mois = obtenir_parametres_mois(
    df_mois,
    periode_choisie,
)

st.sidebar.divider()
st.sidebar.subheader("Informations du mois")

chiffre_affaires = st.sidebar.number_input(
    "Chiffre d’affaires encaissé",
    min_value=0.0,
    value=float(
        parametres_mois["chiffre_affaires"]
    ),
    step=50.0,
    format="%.2f",
)

taux_urssaf = st.sidebar.number_input(
    "Taux URSSAF estimé (%)",
    min_value=0.0,
    max_value=100.0,
    value=float(
        parametres_mois["taux_urssaf"]
    ),
    step=0.1,
    format="%.1f",
)

loyer = st.sidebar.number_input(
    "Loyer payé depuis Lydia",
    min_value=0.0,
    value=float(
        parametres_mois["loyer"]
    ),
    step=50.0,
    format="%.2f",
)

objectif_epargne = st.sidebar.number_input(
    "Objectif d’épargne",
    min_value=0.0,
    value=float(
        parametres_mois["objectif_epargne"]
    ),
    step=50.0,
    format="%.2f",
)

if periode_choisie == PERIODES[0]:
    st.sidebar.divider()
    st.sidebar.subheader("Départ en juillet 2026")

    solde_initial_revolut = st.sidebar.number_input(
        "Solde Revolut au début de juillet",
        value=float(
            parametres_mois[
                "solde_initial_revolut"
            ]
        ),
        step=50.0,
        format="%.2f",
    )
else:
    solde_initial_revolut = float(
        parametres_mois[
            "solde_initial_revolut"
        ]
    )

st.sidebar.divider()
st.sidebar.subheader("Budgets par catégorie")

budgets = {}

for categorie in CATEGORIES_BUDGET:
    budgets[categorie] = st.sidebar.number_input(
        categorie,
        min_value=0.0,
        value=float(
            parametres_mois.get(
                f"budget_{categorie}",
                0.0,
            )
        ),
        step=10.0,
        format="%.2f",
        key=(
            f"budget_"
            f"{periode_choisie}_"
            f"{categorie}"
        ),
    )

if st.sidebar.button(
    "Enregistrer ce mois",
    use_container_width=True,
):
    valeurs = {
        "periode": str(
            periode_choisie
        ),
        "chiffre_affaires": (
            chiffre_affaires
        ),
        "taux_urssaf": (
            taux_urssaf
        ),
        "loyer": loyer,
        "objectif_epargne": (
            objectif_epargne
        ),
        "solde_initial_revolut": (
            solde_initial_revolut
        ),
    }

    for categorie, budget in budgets.items():
        valeurs[
            f"budget_{categorie}"
        ] = budget

    df_mois = enregistrer_parametres_mois(
        df_mois,
        valeurs,
    )

    st.sidebar.success(
        "Mois enregistré."
    )

    st.rerun()


# ============================================================
# RECURRENCES AUTOMATIQUES
# ============================================================

depenses, recurrence_ajoutee = (
    ajouter_recurrences_automatiquement(
        depenses,
        recurrents,
        periode_choisie,
    )
)

if recurrence_ajoutee > 0:
    st.toast(
        f"{recurrence_ajoutee} dépense(s) "
        "récurrente(s) ajoutée(s)."
    )


# ============================================================
# CALCULS COURANTS
# ============================================================

cache_mois = {}

resume = calculer_mois(
    periode_choisie,
    df_mois,
    depenses,
    remboursements,
    cache_mois,
)

depenses_mois = filtrer_periode(
    depenses,
    periode_choisie,
)

remboursements_mois = filtrer_periode(
    remboursements,
    periode_choisie,
)

dette_initiale = float(
    parametres_generaux["dette_initiale"]
)

total_deja_rembourse = (
    remboursements["montant"].sum()
    if not remboursements.empty
    else 0.0
)

dette_restante = max(
    dette_initiale
    - total_deja_rembourse,
    0.0,
)


# ============================================================
# ONGLETS
# ============================================================

onglet_recap, onglet_depenses, onglet_dette, onglet_historique = st.tabs(
    [
        "Récapitulatif",
        "Dépenses",
        "Dette appartement",
        "Historique",
    ]
)


# ============================================================
# RECAPITULATIF
# ============================================================

with onglet_recap:
    st.header(
        libelle_periode(
            periode_choisie
        )
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Solde Revolut reporté",
        format_euros(
            resume["solde_reporte"]
        ),
    )

    col2.metric(
        "Montant transféré vers Revolut",
        format_euros(
            resume[
                "virement_vers_revolut"
            ]
        ),
    )

    col3.metric(
        "Dépenses du mois",
        format_euros(
            resume["total_depenses"]
            + resume[
                "total_remboursements"
            ]
        ),
    )

    col4.metric(
        "Solde Revolut final",
        format_euros(
            resume[
                "solde_final_revolut"
            ]
        ),
    )

    with st.expander(
        "Voir le calcul du montant transféré"
    ):
        st.write(
            f"Chiffre d’affaires : "
            f"**{format_euros(resume['chiffre_affaires'])}**"
        )

        st.write(
            f"URSSAF : "
            f"**-{format_euros(resume['urssaf'])}**"
        )

        st.write(
            f"Loyer : "
            f"**-{format_euros(resume['loyer'])}**"
        )

        st.write(
            f"Montant transféré vers Revolut : "
            f"**{format_euros(resume['virement_vers_revolut'])}**"
        )

    st.subheader(
        "Objectif d’épargne"
    )

    if objectif_epargne <= 0:
        st.info(
            "Aucun objectif d’épargne "
            "défini pour ce mois."
        )

    elif (
        resume["solde_final_revolut"]
        >= objectif_epargne
    ):
        reste = (
            resume["solde_final_revolut"]
            - objectif_epargne
        )

        st.success(
            f"Objectif atteignable. "
            f"Après avoir mis de côté "
            f"{format_euros(objectif_epargne)}, "
            f"il resterait "
            f"{format_euros(reste)}."
        )

        st.progress(1.0)

    else:
        manque = (
            objectif_epargne
            - resume[
                "solde_final_revolut"
            ]
        )

        progression = (
            max(
                resume[
                    "solde_final_revolut"
                ]
                / objectif_epargne,
                0.0,
            )
            if objectif_epargne > 0
            else 0.0
        )

        st.warning(
            f"Il manque "
            f"{format_euros(manque)} "
            "pour atteindre l’objectif."
        )

        st.progress(
            min(progression, 1.0)
        )

    st.subheader(
        "Budgets par catégorie"
    )

    lignes_budgets = []

    for categorie in CATEGORIES_BUDGET:
        if categorie == "Dette appartement":
            depense_categorie = (
                resume[
                    "total_remboursements"
                ]
            )
        else:
            depense_categorie = (
                depenses_mois.loc[
                    depenses_mois[
                        "categorie"
                    ] == categorie,
                    "montant",
                ].sum()
                if not depenses_mois.empty
                else 0.0
            )

        budget = float(
            budgets[categorie]
        )

        if (
            budget > 0
            or depense_categorie > 0
        ):
            lignes_budgets.append(
                {
                    "Catégorie": categorie,
                    "Budget": budget,
                    "Dépensé": (
                        depense_categorie
                    ),
                    "Reste": (
                        budget
                        - depense_categorie
                    ),
                }
            )

    if not lignes_budgets:
        st.info(
            "Aucun budget ni aucune "
            "dépense enregistré."
        )

    else:
        df_budgets = pd.DataFrame(
            lignes_budgets
        )

        st.dataframe(
            df_budgets,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Budget": (
                    st.column_config
                    .NumberColumn(
                        "Budget",
                        format="%.2f €",
                    )
                ),
                "Dépensé": (
                    st.column_config
                    .NumberColumn(
                        "Dépensé",
                        format="%.2f €",
                    )
                ),
                "Reste": (
                    st.column_config
                    .NumberColumn(
                        "Reste",
                        format="%.2f €",
                    )
                ),
            },
        )

    st.subheader(
        "Répartition des dépenses"
    )

    graphique = (
        depenses_mois
        .groupby("categorie")[
            "montant"
        ]
        .sum()
        .sort_values(
            ascending=False
        )
        if not depenses_mois.empty
        else pd.Series(dtype=float)
    )

    if (
        resume[
            "total_remboursements"
        ] > 0
    ):
        graphique.loc[
            "Dette appartement"
        ] = resume[
            "total_remboursements"
        ]

    if graphique.empty:
        st.info(
            "Aucune dépense enregistrée "
            "pour ce mois."
        )
    else:
        st.bar_chart(
            graphique
        )


# ============================================================
# DEPENSES
# ============================================================

with onglet_depenses:
    st.header(
        "Dépenses"
    )

    st.subheader(
        "Ajouter une dépense"
    )

    with st.form(
        "formulaire_depense",
        clear_on_submit=True,
    ):
        col1, col2, col3, col4 = (
            st.columns(4)
        )

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
                placeholder=(
                    "Exemple : Carrefour"
                ),
            )

        with col3:
            categorie = st.selectbox(
                "Catégorie",
                CATEGORIES,
            )

        with col4:
            montant = st.number_input(
                "Montant",
                min_value=0.0,
                step=1.0,
                format="%.2f",
            )

        ajouter = (
            st.form_submit_button(
                "Ajouter la dépense",
                use_container_width=True,
            )
        )

    if ajouter:
        if not description.strip():
            st.error(
                "Ajoute une description."
            )

        elif montant <= 0:
            st.error(
                "Le montant doit être "
                "supérieur à 0 €."
            )

        else:
            depenses = ajouter_depense(
                depenses,
                date_depense,
                description,
                categorie,
                montant,
            )

            st.success(
                "Dépense ajoutée."
            )

            st.rerun()

    st.subheader(
        "Liste des dépenses"
    )

    if depenses_mois.empty:
        st.info(
            "Aucune dépense pour ce mois."
        )

    else:
        tableau = depenses_mois.copy()

        tableau["date"] = (
            tableau["date"]
            .dt.strftime("%d/%m/%Y")
        )

        tableau = tableau.rename(
            columns={
                "date": "Date",
                "description": (
                    "Description"
                ),
                "categorie": (
                    "Catégorie"
                ),
                "montant": "Montant",
            }
        )

        st.dataframe(
            tableau[
                [
                    "Date",
                    "Description",
                    "Catégorie",
                    "Montant",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Montant": (
                    st.column_config
                    .NumberColumn(
                        "Montant",
                        format="%.2f €",
                    )
                ),
            },
        )

        st.subheader(
            "Supprimer une dépense"
        )

        options = {}

        for index, ligne in (
            depenses_mois.iterrows()
        ):
            texte = (
                f"{ligne['date'].strftime('%d/%m/%Y')}"
                f" — {ligne['description']}"
                f" — {format_euros(ligne['montant'])}"
            )

            options[texte] = index

        selection = st.selectbox(
            "Dépense",
            options=list(
                options.keys()
            ),
        )

        confirmation = st.checkbox(
            "Je confirme la suppression.",
            key="confirmation_depense",
        )

        if st.button(
            "Supprimer la dépense",
            disabled=not confirmation,
        ):
            depenses = depenses.drop(
                index=options[selection]
            ).reset_index(drop=True)

            sauvegarder_depenses(
                depenses
            )

            st.success(
                "Dépense supprimée."
            )

            st.rerun()

    st.divider()

    st.header(
        "Dépenses récurrentes"
    )

    st.caption(
        "Tu crées une dépense récurrente "
        "une seule fois. Elle sera ensuite "
        "ajoutée automatiquement chaque mois."
    )

    with st.form(
        "formulaire_recurrence",
        clear_on_submit=True,
    ):
        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:
            description_recurrence = (
                st.text_input(
                    "Description",
                    placeholder=(
                        "Exemple : Netflix"
                    ),
                )
            )

        with col2:
            categorie_recurrence = (
                st.selectbox(
                    "Catégorie",
                    CATEGORIES,
                    key=(
                        "categorie_recurrence"
                    ),
                )
            )

        with col3:
            montant_recurrence = (
                st.number_input(
                    "Montant",
                    min_value=0.0,
                    step=10.0,
                    format="%.2f",
                    key=(
                        "montant_recurrence"
                    ),
                )
            )

        col4, col5, col6 = (
            st.columns(3)
        )

        with col4:
            jour_recurrence = (
                st.number_input(
                    "Jour du mois",
                    min_value=1,
                    max_value=31,
                    value=1,
                    step=1,
                )
            )

        with col5:
            debut_recurrence = (
                st.selectbox(
                    "Premier mois",
                    PERIODES,
                    index=0,
                    format_func=(
                        libelle_periode
                    ),
                    key=(
                        "debut_recurrence"
                    ),
                )
            )

        with col6:
            fin_recurrence = (
                st.selectbox(
                    "Dernier mois",
                    PERIODES,
                    index=(
                        len(PERIODES) - 1
                    ),
                    format_func=(
                        libelle_periode
                    ),
                    key=(
                        "fin_recurrence"
                    ),
                )
            )

        ajouter_recurrence = (
            st.form_submit_button(
                "Créer la dépense récurrente",
                use_container_width=True,
            )
        )

    if ajouter_recurrence:
        if not (
            description_recurrence
            .strip()
        ):
            st.error(
                "Ajoute une description."
            )

        elif montant_recurrence <= 0:
            st.error(
                "Le montant doit être "
                "supérieur à 0 €."
            )

        elif (
            debut_recurrence
            > fin_recurrence
        ):
            st.error(
                "Le premier mois doit être "
                "avant le dernier mois."
            )

        else:
            nouvelle = pd.DataFrame(
                [{
                    "id": uuid4().hex,
                    "description": (
                        description_recurrence
                        .strip()
                    ),
                    "categorie": (
                        categorie_recurrence
                    ),
                    "montant": float(
                        montant_recurrence
                    ),
                    "jour": int(
                        jour_recurrence
                    ),
                    "debut": str(
                        debut_recurrence
                    ),
                    "fin": str(
                        fin_recurrence
                    ),
                    "active": True,
                }]
            )

            recurrents = pd.concat(
                [
                    recurrents,
                    nouvelle,
                ],
                ignore_index=True,
            )

            sauvegarder_recurrences(
                recurrents
            )

            st.success(
                "Dépense récurrente créée."
            )

            st.rerun()

    if recurrents.empty:
        st.info(
            "Aucune dépense récurrente."
        )

    else:
        affichage = recurrents.copy()

        affichage["debut"] = (
            affichage["debut"]
            .apply(
                lambda valeur: (
                    libelle_periode(
                        pd.Period(
                            str(valeur),
                            freq="M",
                        )
                    )
                )
            )
        )

        affichage["fin"] = (
            affichage["fin"]
            .apply(
                lambda valeur: (
                    libelle_periode(
                        pd.Period(
                            str(valeur),
                            freq="M",
                        )
                    )
                )
            )
        )

        affichage = affichage.rename(
            columns={
                "description": (
                    "Description"
                ),
                "categorie": (
                    "Catégorie"
                ),
                "montant": "Montant",
                "jour": "Jour",
                "debut": "Début",
                "fin": "Fin",
            }
        )

        st.dataframe(
            affichage[
                [
                    "Description",
                    "Catégorie",
                    "Montant",
                    "Jour",
                    "Début",
                    "Fin",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Montant": (
                    st.column_config
                    .NumberColumn(
                        "Montant",
                        format="%.2f €",
                    )
                ),
            },
        )

        options_recurrences = {
            (
                f"{ligne['description']}"
                f" — {format_euros(ligne['montant'])}"
            ): index
            for index, ligne in (
                recurrents.iterrows()
            )
        }

        selection_recurrence = (
            st.selectbox(
                "Dépense récurrente "
                "à supprimer",
                options=list(
                    options_recurrences
                    .keys()
                ),
            )
        )

        confirmation_recurrence = (
            st.checkbox(
                "Je confirme la suppression.",
                key=(
                    "confirmation_recurrence"
                ),
            )
        )

        if st.button(
            "Supprimer la dépense récurrente",
            disabled=(
                not confirmation_recurrence
            ),
        ):
            recurrents = recurrents.drop(
                index=options_recurrences[
                    selection_recurrence
                ]
            ).reset_index(drop=True)

            sauvegarder_recurrences(
                recurrents
            )

            st.success(
                "Dépense récurrente supprimée."
            )

            st.rerun()


# ============================================================
# DETTE APPARTEMENT
# ============================================================

with onglet_dette:
    st.header(
        "Dette appartement"
    )

    nouvelle_dette_initiale = (
        st.number_input(
            "Montant initial dû "
            "aux parents",
            min_value=0.0,
            value=float(
                dette_initiale
            ),
            step=50.0,
            format="%.2f",
        )
    )

    if st.button(
        "Enregistrer le montant "
        "de la dette"
    ):
        sauvegarder_parametres_generaux(
            nouvelle_dette_initiale
        )

        st.success(
            "Dette initiale enregistrée."
        )

        st.rerun()

    progression_dette = (
        total_deja_rembourse
        / dette_initiale
        if dette_initiale > 0
        else 0.0
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    col1.metric(
        "Dette initiale",
        format_euros(
            dette_initiale
        ),
    )

    col2.metric(
        "Déjà remboursé",
        format_euros(
            total_deja_rembourse
        ),
    )

    col3.metric(
        "Reste à rembourser",
        format_euros(
            dette_restante
        ),
    )

    if dette_initiale > 0:
        st.progress(
            min(
                max(
                    progression_dette,
                    0.0,
                ),
                1.0,
            )
        )

    st.subheader(
        "Ajouter un remboursement"
    )

    with st.form(
        "formulaire_remboursement",
        clear_on_submit=True,
    ):
        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:
            date_remboursement = (
                st.date_input(
                    "Date",
                    value=date(
                        periode_choisie.year,
                        periode_choisie.month,
                        1,
                    ),
                    key=(
                        "date_remboursement"
                    ),
                )
            )

        with col2:
            description_remboursement = (
                st.text_input(
                    "Description",
                    value=(
                        "Remboursement "
                        "dette appartement"
                    ),
                )
            )

        with col3:
            montant_remboursement = (
                st.number_input(
                    "Montant",
                    min_value=0.0,
                    step=50.0,
                    format="%.2f",
                    key=(
                        "montant_remboursement"
                    ),
                )
            )

        ajouter_remboursement = (
            st.form_submit_button(
                "Ajouter le remboursement",
                use_container_width=True,
            )
        )

    if ajouter_remboursement:
        if montant_remboursement <= 0:
            st.error(
                "Le montant doit être "
                "supérieur à 0 €."
            )

        elif (
            montant_remboursement
            > dette_restante
        ):
            st.error(
                f"Le montant dépasse "
                f"la dette restante de "
                f"{format_euros(dette_restante)}."
            )

        else:
            nouveau = pd.DataFrame(
                [{
                    "id": uuid4().hex,
                    "date": pd.Timestamp(
                        date_remboursement
                    ),
                    "description": (
                        description_remboursement
                        .strip()
                        or (
                            "Remboursement "
                            "dette appartement"
                        )
                    ),
                    "montant": float(
                        montant_remboursement
                    ),
                }]
            )

            remboursements = pd.concat(
                [
                    remboursements,
                    nouveau,
                ],
                ignore_index=True,
            )

            sauvegarder_remboursements(
                remboursements
            )

            st.success(
                "Remboursement ajouté."
            )

            st.rerun()

    st.subheader(
        "Historique des remboursements"
    )

    if remboursements.empty:
        st.info(
            "Aucun remboursement enregistré."
        )

    else:
        historique = remboursements.copy()

        historique["date"] = (
            historique["date"]
            .dt.strftime("%d/%m/%Y")
        )

        historique = historique.rename(
            columns={
                "date": "Date",
                "description": (
                    "Description"
                ),
                "montant": "Montant",
            }
        )

        st.dataframe(
            historique[
                [
                    "Date",
                    "Description",
                    "Montant",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Montant": (
                    st.column_config
                    .NumberColumn(
                        "Montant",
                        format="%.2f €",
                    )
                ),
            },
        )

        options = {}

        for index, ligne in (
            remboursements.iterrows()
        ):
            texte = (
                f"{ligne['date'].strftime('%d/%m/%Y')}"
                f" — {ligne['description']}"
                f" — {format_euros(ligne['montant'])}"
            )

            options[texte] = index

        selection = st.selectbox(
            "Remboursement à supprimer",
            options=list(
                options.keys()
            ),
        )

        confirmation = st.checkbox(
            "Je confirme la suppression.",
            key=(
                "confirmation_remboursement"
            ),
        )

        if st.button(
            "Supprimer le remboursement",
            disabled=not confirmation,
        ):
            remboursements = (
                remboursements.drop(
                    index=options[
                        selection
                    ]
                )
                .reset_index(drop=True)
            )

            sauvegarder_remboursements(
                remboursements
            )

            st.success(
                "Remboursement supprimé."
            )

            st.rerun()


# ============================================================
# HISTORIQUE
# ============================================================

with onglet_historique:
    st.header(
        "Historique mensuel"
    )

    lignes = []
    cache_historique = {}

    for periode in PERIODES:
        valeurs = calculer_mois(
            periode,
            df_mois,
            depenses,
            remboursements,
            cache_historique,
        )

        lignes.append(
            {
                "Mois": (
                    libelle_periode(
                        periode
                    )
                ),
                "Solde reporté": (
                    valeurs[
                        "solde_reporte"
                    ]
                ),
                "Chiffre d’affaires": (
                    valeurs[
                        "chiffre_affaires"
                    ]
                ),
                "Transféré vers Revolut": (
                    valeurs[
                        "virement_vers_revolut"
                    ]
                ),
                "Dépenses": (
                    valeurs[
                        "total_depenses"
                    ]
                ),
                "Dette remboursée": (
                    valeurs[
                        "total_remboursements"
                    ]
                ),
                "Solde final Revolut": (
                    valeurs[
                        "solde_final_revolut"
                    ]
                ),
            }
        )

    historique = pd.DataFrame(
        lignes
    )

    st.dataframe(
        historique,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Solde reporté": (
                st.column_config
                .NumberColumn(
                    "Solde reporté",
                    format="%.2f €",
                )
            ),
            "Chiffre d’affaires": (
                st.column_config
                .NumberColumn(
                    "Chiffre d’affaires",
                    format="%.2f €",
                )
            ),
            "Transféré vers Revolut": (
                st.column_config
                .NumberColumn(
                    "Transféré vers Revolut",
                    format="%.2f €",
                )
            ),
            "Dépenses": (
                st.column_config
                .NumberColumn(
                    "Dépenses",
                    format="%.2f €",
                )
            ),
            "Dette remboursée": (
                st.column_config
                .NumberColumn(
                    "Dette remboursée",
                    format="%.2f €",
                )
            ),
            "Solde final Revolut": (
                st.column_config
                .NumberColumn(
                    "Solde final Revolut",
                    format="%.2f €",
                )
            ),
        },
    )

    st.subheader(
        "Évolution du solde Revolut"
    )

    st.line_chart(
        historique.set_index(
            "Mois"
        )["Solde final Revolut"]
    )

    export = historique.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "Télécharger l’historique",
        data=export,
        file_name=(
            "historique_budget.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )