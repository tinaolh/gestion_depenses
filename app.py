from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st


# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Mon budget freelance",
    page_icon="💸",
    layout="wide",
)

FICHIER_DEPENSES = Path("depenses.csv")
FICHIER_PARAMETRES = Path("parametres.csv")
FICHIER_REMBOURSEMENTS = Path("remboursements_dette.csv")

CATEGORIES = [
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
    "Dette appartement",
    "Autre",
]

MOIS = {
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


# =====================================================
# FONCTIONS GÉNÉRALES
# =====================================================

def format_euros(montant):
    """Affiche un montant au format euros."""
    return f"{float(montant):,.2f} €".replace(",", " ")


def lire_csv_securise(fichier, colonnes):
    """Lit un fichier CSV ou crée un tableau vide."""

    if not fichier.exists():
        return pd.DataFrame(columns=colonnes)

    try:
        dataframe = pd.read_csv(fichier)
    except (pd.errors.EmptyDataError, UnicodeDecodeError):
        return pd.DataFrame(columns=colonnes)

    for colonne in colonnes:
        if colonne not in dataframe.columns:
            dataframe[colonne] = None

    return dataframe[colonnes]


# =====================================================
# GESTION DES DÉPENSES
# =====================================================

def charger_depenses():
    """Charge les dépenses personnelles."""

    colonnes = [
        "date",
        "description",
        "categorie",
        "montant",
    ]

    dataframe = lire_csv_securise(
        FICHIER_DEPENSES,
        colonnes,
    )

    if dataframe.empty:
        return dataframe

    dataframe["date"] = pd.to_datetime(
        dataframe["date"],
        errors="coerce",
    )

    dataframe["montant"] = pd.to_numeric(
        dataframe["montant"],
        errors="coerce",
    )

    dataframe["description"] = (
        dataframe["description"]
        .fillna("")
        .astype(str)
    )

    dataframe["categorie"] = (
        dataframe["categorie"]
        .fillna("Autre")
        .astype(str)
    )

    dataframe = dataframe.dropna(
        subset=["date", "montant"]
    )

    return dataframe.reset_index(drop=True)


def enregistrer_depenses(dataframe):
    """Enregistre les dépenses dans le fichier CSV."""

    dataframe_a_enregistrer = dataframe.copy()

    if not dataframe_a_enregistrer.empty:
        dataframe_a_enregistrer["date"] = pd.to_datetime(
            dataframe_a_enregistrer["date"]
        ).dt.strftime("%Y-%m-%d")

    dataframe_a_enregistrer.to_csv(
        FICHIER_DEPENSES,
        index=False,
    )


# =====================================================
# GESTION DE LA DETTE
# =====================================================

def charger_remboursements():
    """Charge les remboursements de la dette."""

    colonnes = [
        "date",
        "description",
        "montant",
    ]

    dataframe = lire_csv_securise(
        FICHIER_REMBOURSEMENTS,
        colonnes,
    )

    if dataframe.empty:
        return dataframe

    dataframe["date"] = pd.to_datetime(
        dataframe["date"],
        errors="coerce",
    )

    dataframe["montant"] = pd.to_numeric(
        dataframe["montant"],
        errors="coerce",
    )

    dataframe["description"] = (
        dataframe["description"]
        .fillna("Remboursement dette appartement")
        .astype(str)
    )

    dataframe = dataframe.dropna(
        subset=["date", "montant"]
    )

    return dataframe.reset_index(drop=True)


def enregistrer_remboursements(dataframe):
    """Enregistre les remboursements de la dette."""

    dataframe_a_enregistrer = dataframe.copy()

    if not dataframe_a_enregistrer.empty:
        dataframe_a_enregistrer["date"] = pd.to_datetime(
            dataframe_a_enregistrer["date"]
        ).dt.strftime("%Y-%m-%d")

    dataframe_a_enregistrer.to_csv(
        FICHIER_REMBOURSEMENTS,
        index=False,
    )


# =====================================================
# GESTION DES PARAMÈTRES
# =====================================================

def charger_parametres():
    """Charge les paramètres de l’application."""

    parametres_defaut = {
        "chiffre_affaires": 5500.0,
        "taux_urssaf": 28.0,
        "autres_charges_pro": 0.0,
        "objectif_epargne": 500.0,
        "dette_initiale": 2500.0,
    }

    for categorie in CATEGORIES:
        parametres_defaut[categorie] = 0.0

    if not FICHIER_PARAMETRES.exists():
        return parametres_defaut

    try:
        dataframe = pd.read_csv(
            FICHIER_PARAMETRES
        )
    except pd.errors.EmptyDataError:
        return parametres_defaut

    if dataframe.empty:
        return parametres_defaut

    ancienne_ligne = dataframe.iloc[0].to_dict()

    # Compatibilité avec les anciennes versions
    if (
        "chiffre_affaires" not in ancienne_ligne
        and "revenu" in ancienne_ligne
        and pd.notna(ancienne_ligne["revenu"])
    ):
        ancienne_ligne["chiffre_affaires"] = (
            ancienne_ligne["revenu"]
        )

    for cle in parametres_defaut:
        valeur = ancienne_ligne.get(cle)

        if pd.notna(valeur):
            try:
                parametres_defaut[cle] = float(valeur)
            except (TypeError, ValueError):
                pass

    return parametres_defaut


def enregistrer_parametres(parametres):
    """Enregistre les paramètres."""

    pd.DataFrame([parametres]).to_csv(
        FICHIER_PARAMETRES,
        index=False,
    )


# =====================================================
# CHARGEMENT DES DONNÉES
# =====================================================

depenses = charger_depenses()
remboursements = charger_remboursements()
parametres = charger_parametres()


# =====================================================
# EN-TÊTE
# =====================================================

st.title("💸 Mon gestionnaire de budget freelance")

st.write(
    "Suis ton chiffre d’affaires, réserve l’URSSAF, "
    "gère tes dépenses et rembourse ta dette appartement."
)


# =====================================================
# BARRE LATÉRALE : PÉRIODE
# =====================================================

st.sidebar.header("📅 Période affichée")

mois_choisi = st.sidebar.selectbox(
    "Mois",
    options=list(MOIS.keys()),
    index=date.today().month - 1,
    format_func=lambda valeur: MOIS[valeur],
)

annee_choisie = st.sidebar.number_input(
    "Année",
    min_value=2020,
    max_value=2100,
    value=date.today().year,
    step=1,
)


# =====================================================
# BARRE LATÉRALE : FREELANCE
# =====================================================

st.sidebar.divider()
st.sidebar.header("💼 Activité freelance")

chiffre_affaires = st.sidebar.number_input(
    "Chiffre d’affaires encaissé",
    min_value=0.0,
    value=float(
        parametres["chiffre_affaires"]
    ),
    step=50.0,
    format="%.2f",
    help=(
        "Indique uniquement l’argent réellement reçu "
        "de tes clients pendant le mois."
    ),
)

taux_urssaf = st.sidebar.number_input(
    "Taux URSSAF estimé (%)",
    min_value=0.0,
    max_value=100.0,
    value=float(
        parametres["taux_urssaf"]
    ),
    step=0.1,
    format="%.1f",
)

autres_charges_pro = st.sidebar.number_input(
    "Autres charges professionnelles",
    min_value=0.0,
    value=float(
        parametres["autres_charges_pro"]
    ),
    step=10.0,
    format="%.2f",
)

objectif_epargne = st.sidebar.number_input(
    "Objectif d’épargne",
    min_value=0.0,
    value=float(
        parametres["objectif_epargne"]
    ),
    step=50.0,
    format="%.2f",
)


# =====================================================
# BARRE LATÉRALE : DETTE
# =====================================================

st.sidebar.divider()
st.sidebar.header("🏠 Dette appartement")

dette_initiale = st.sidebar.number_input(
    "Dette initiale envers mes parents",
    min_value=0.0,
    value=float(
        parametres["dette_initiale"]
    ),
    step=50.0,
    format="%.2f",
)


# =====================================================
# CALCULS FREELANCE
# =====================================================

cotisations_urssaf = (
    chiffre_affaires * taux_urssaf / 100
)

revenu_apres_urssaf = (
    chiffre_affaires - cotisations_urssaf
)

revenu_net_disponible = (
    revenu_apres_urssaf - autres_charges_pro
)

st.sidebar.metric(
    "URSSAF à réserver",
    format_euros(cotisations_urssaf),
)

st.sidebar.metric(
    "Disponible avant dépenses perso",
    format_euros(revenu_net_disponible),
)


# =====================================================
# BARRE LATÉRALE : BUDGETS
# =====================================================

st.sidebar.divider()
st.sidebar.header("🎯 Budgets par catégorie")

budgets_categories = {}

for categorie in CATEGORIES:
    budgets_categories[categorie] = (
        st.sidebar.number_input(
            categorie,
            min_value=0.0,
            value=float(
                parametres.get(categorie, 0.0)
            ),
            step=10.0,
            format="%.2f",
            key=f"budget_{categorie}",
        )
    )

if st.sidebar.button(
    "Enregistrer mes paramètres",
    use_container_width=True,
):
    nouveaux_parametres = {
        "chiffre_affaires": chiffre_affaires,
        "taux_urssaf": taux_urssaf,
        "autres_charges_pro": autres_charges_pro,
        "objectif_epargne": objectif_epargne,
        "dette_initiale": dette_initiale,
    }

    nouveaux_parametres.update(
        budgets_categories
    )

    enregistrer_parametres(
        nouveaux_parametres
    )

    st.sidebar.success(
        "Paramètres enregistrés."
    )


# =====================================================
# ONGLETS
# =====================================================

onglet_budget, onglet_dette = st.tabs(
    [
        "💳 Budget mensuel",
        "🏠 Dette appartement",
    ]
)


# =====================================================
# ONGLET 1 : BUDGET MENSUEL
# =====================================================

with onglet_budget:

    st.subheader("➕ Ajouter une dépense")

    with st.form(
        "formulaire_ajout_depense",
        clear_on_submit=True,
    ):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            date_depense = st.date_input(
                "Date",
                value=date.today(),
                key="date_depense",
            )

        with col2:
            description = st.text_input(
                "Description",
                placeholder="Exemple : Carrefour",
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
                key="montant_depense",
            )

        ajouter_depense = st.form_submit_button(
            "Ajouter la dépense",
            use_container_width=True,
        )

    if ajouter_depense:
        if not description.strip():
            st.error("Ajoute une description.")

        elif montant <= 0:
            st.error(
                "Le montant doit être supérieur à 0 €."
            )

        else:
            nouvelle_depense = pd.DataFrame(
                [
                    {
                        "date": pd.to_datetime(
                            date_depense
                        ),
                        "description": (
                            description.strip()
                        ),
                        "categorie": categorie,
                        "montant": float(montant),
                    }
                ]
            )

            depenses = pd.concat(
                [depenses, nouvelle_depense],
                ignore_index=True,
            )

            enregistrer_depenses(depenses)

            st.success("Dépense enregistrée.")
            st.rerun()

    # -------------------------------------------------
    # FILTRAGE DES DÉPENSES
    # -------------------------------------------------

    if not depenses.empty:
        depenses["date"] = pd.to_datetime(
            depenses["date"]
        )

        depenses_du_mois = depenses[
            (
                depenses["date"].dt.month
                == mois_choisi
            )
            & (
                depenses["date"].dt.year
                == annee_choisie
            )
        ].copy()

    else:
        depenses_du_mois = depenses.copy()

    # -------------------------------------------------
    # REMBOURSEMENTS DU MOIS
    # -------------------------------------------------

    if not remboursements.empty:
        remboursements["date"] = pd.to_datetime(
            remboursements["date"]
        )

        remboursements_du_mois = remboursements[
            (
                remboursements["date"].dt.month
                == mois_choisi
            )
            & (
                remboursements["date"].dt.year
                == annee_choisie
            )
        ].copy()

    else:
        remboursements_du_mois = (
            remboursements.copy()
        )

    total_depenses_classiques = depenses_du_mois[
        "montant"
    ].sum()

    total_remboursements_mois = (
        remboursements_du_mois["montant"].sum()
        if not remboursements_du_mois.empty
        else 0.0
    )

    total_sorties_mois = (
        total_depenses_classiques
        + total_remboursements_mois
    )

    reste_apres_depenses = (
        revenu_net_disponible
        - total_sorties_mois
    )

    epargne_potentielle = max(
        reste_apres_depenses,
        0,
    )

    taux_depenses = (
        total_sorties_mois / revenu_net_disponible
        if revenu_net_disponible > 0
        else 0
    )

    # -------------------------------------------------
    # RÉSUMÉ
    # -------------------------------------------------

    st.divider()

    st.subheader(
        f"📊 Résumé — "
        f"{MOIS[mois_choisi]} {annee_choisie}"
    )

    col1, col2, col3, col4, col5, col6 = (
        st.columns(6)
    )

    col1.metric(
        "Chiffre d’affaires",
        format_euros(chiffre_affaires),
    )

    col2.metric(
        "URSSAF à réserver",
        format_euros(cotisations_urssaf),
    )

    col3.metric(
        "Disponible net",
        format_euros(revenu_net_disponible),
    )

    col4.metric(
        "Dépenses",
        format_euros(total_depenses_classiques),
    )

    col5.metric(
        "Dette remboursée",
        format_euros(total_remboursements_mois),
    )

    col6.metric(
        "Reste disponible",
        format_euros(reste_apres_depenses),
    )

    # -------------------------------------------------
    # ALERTES
    # -------------------------------------------------

    st.subheader("🚨 État du mois")

    if reste_apres_depenses < 0:
        st.error(
            "Tu as dépassé ton revenu disponible de "
            f"{format_euros(abs(reste_apres_depenses))}."
        )

    elif epargne_potentielle < objectif_epargne:
        manque = (
            objectif_epargne
            - epargne_potentielle
        )

        st.warning(
            f"Il te manque {format_euros(manque)} "
            "pour atteindre ton objectif d’épargne."
        )

    else:
        st.success(
            "Tu peux atteindre ton objectif "
            "d’épargne ce mois-ci."
        )

    if revenu_net_disponible > 0:
        st.write(
            f"Tu as utilisé **"
            f"{taux_depenses * 100:.1f} %** "
            "de ton revenu disponible."
        )

        st.progress(
            min(max(taux_depenses, 0.0), 1.0)
        )

    # -------------------------------------------------
    # BUDGETS PAR CATÉGORIE
    # -------------------------------------------------

    st.divider()
    st.subheader("🎯 Budgets par catégorie")

    resultats_categories = []

    for nom_categorie in CATEGORIES:

        if nom_categorie == "Dette appartement":
            depense_categorie = (
                total_remboursements_mois
            )
        else:
            depense_categorie = (
                depenses_du_mois.loc[
                    depenses_du_mois["categorie"]
                    == nom_categorie,
                    "montant",
                ].sum()
            )

        budget_categorie = (
            budgets_categories[nom_categorie]
        )

        reste_categorie = (
            budget_categorie
            - depense_categorie
        )

        resultats_categories.append(
            {
                "Catégorie": nom_categorie,
                "Budget": budget_categorie,
                "Dépensé": depense_categorie,
                "Reste": reste_categorie,
            }
        )

    dataframe_budgets = pd.DataFrame(
        resultats_categories
    )

    dataframe_budgets = dataframe_budgets[
        (dataframe_budgets["Budget"] > 0)
        | (dataframe_budgets["Dépensé"] > 0)
    ]

    if dataframe_budgets.empty:
        st.info(
            "Ajoute tes budgets dans le menu "
            "de gauche."
        )

    else:
        for _, ligne in (
            dataframe_budgets.iterrows()
        ):
            nom_categorie = ligne["Catégorie"]
            budget = float(ligne["Budget"])
            depense = float(ligne["Dépensé"])
            reste = float(ligne["Reste"])

            col_nom, col_barre, col_montants = (
                st.columns([1, 3, 1.5])
            )

            with col_nom:
                st.write(
                    f"**{nom_categorie}**"
                )

            with col_barre:
                if budget > 0:
                    progression = depense / budget

                    st.progress(
                        min(
                            max(progression, 0.0),
                            1.0,
                        )
                    )
                else:
                    st.caption(
                        "Aucun budget défini"
                    )

            with col_montants:
                if budget > 0:
                    st.write(
                        f"{format_euros(depense)} / "
                        f"{format_euros(budget)}"
                    )

                    if reste < 0:
                        st.error(
                            "Dépassé de "
                            f"{format_euros(abs(reste))}"
                        )

                    elif reste > 0:
                        st.caption(
                            "Reste : "
                            f"{format_euros(reste)}"
                        )

                else:
                    st.write(
                        format_euros(depense)
                    )

    # -------------------------------------------------
    # GRAPHIQUE
    # -------------------------------------------------

    st.divider()
    st.subheader("📈 Dépenses par catégorie")

    depenses_pour_graphique = (
        depenses_du_mois
        .groupby("categorie")["montant"]
        .sum()
        .reset_index()
    )

    if total_remboursements_mois > 0:
        ligne_dette = pd.DataFrame(
            [
                {
                    "categorie": "Dette appartement",
                    "montant": (
                        total_remboursements_mois
                    ),
                }
            ]
        )

        depenses_pour_graphique = pd.concat(
            [
                depenses_pour_graphique,
                ligne_dette,
            ],
            ignore_index=True,
        )

    if depenses_pour_graphique.empty:
        st.info(
            "Aucune dépense enregistrée "
            "pour ce mois."
        )

    else:
        depenses_pour_graphique = (
            depenses_pour_graphique
            .groupby("categorie")["montant"]
            .sum()
            .sort_values(ascending=False)
        )

        st.bar_chart(
            depenses_pour_graphique
        )

    # -------------------------------------------------
    # LISTE DES DÉPENSES
    # -------------------------------------------------

    st.divider()
    st.subheader("🧾 Mes dépenses personnelles")

    if depenses_du_mois.empty:
        st.info(
            "Aucune dépense personnelle "
            "pour ce mois."
        )

    else:
        tableau_depenses = (
            depenses_du_mois.copy()
        )

        tableau_depenses["date"] = (
            tableau_depenses["date"]
            .dt.strftime("%d/%m/%Y")
        )

        tableau_depenses = (
            tableau_depenses.rename(
                columns={
                    "date": "Date",
                    "description": "Description",
                    "categorie": "Catégorie",
                    "montant": "Montant",
                }
            )
        )

        st.dataframe(
            tableau_depenses,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Montant": (
                    st.column_config.NumberColumn(
                        "Montant",
                        format="%.2f €",
                    )
                ),
            },
        )

    # -------------------------------------------------
    # SUPPRESSION D’UNE DÉPENSE
    # -------------------------------------------------

    if not depenses_du_mois.empty:
        st.subheader(
            "🗑️ Supprimer une dépense personnelle"
        )

        options_depenses = {}

        for index, ligne in (
            depenses_du_mois.iterrows()
        ):
            texte = (
                f"{ligne['date'].strftime('%d/%m/%Y')}"
                f" — {ligne['description']}"
                f" — {format_euros(ligne['montant'])}"
                f" — n°{index + 1}"
            )

            options_depenses[texte] = index

        depense_selectionnee = st.selectbox(
            "Dépense à supprimer",
            list(options_depenses.keys()),
            key="suppression_depense",
        )

        confirmation_depense = st.checkbox(
            "Je confirme la suppression "
            "de cette dépense.",
            key="confirmation_depense",
        )

        if st.button(
            "Supprimer la dépense",
            disabled=not confirmation_depense,
        ):
            index_a_supprimer = (
                options_depenses[
                    depense_selectionnee
                ]
            )

            depenses = depenses.drop(
                index=index_a_supprimer
            ).reset_index(drop=True)

            enregistrer_depenses(depenses)

            st.success("Dépense supprimée.")
            st.rerun()


# =====================================================
# ONGLET 2 : DETTE APPARTEMENT
# =====================================================

with onglet_dette:

    total_deja_rembourse = (
        remboursements["montant"].sum()
        if not remboursements.empty
        else 0.0
    )

    total_deja_rembourse = min(
        total_deja_rembourse,
        dette_initiale,
    )

    dette_restante = max(
        dette_initiale - total_deja_rembourse,
        0,
    )

    progression_dette = (
        total_deja_rembourse / dette_initiale
        if dette_initiale > 0
        else 0
    )

    st.subheader("🏠 Suivi de ma dette")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Dette initiale",
        format_euros(dette_initiale),
    )

    col2.metric(
        "Déjà remboursé",
        format_euros(total_deja_rembourse),
    )

    col3.metric(
        "Reste à rembourser",
        format_euros(dette_restante),
    )

    if dette_initiale > 0:
        st.progress(
            min(max(progression_dette, 0.0), 1.0)
        )

        st.write(
            f"Tu as remboursé **"
            f"{progression_dette * 100:.1f} %** "
            "de ta dette."
        )

    if dette_restante == 0:
        st.success(
            "🎉 La dette appartement est entièrement "
            "remboursée."
        )

    else:
        st.info(
            f"Il te reste encore "
            f"**{format_euros(dette_restante)}** "
            "à rembourser à tes parents."
        )

    # -------------------------------------------------
    # AJOUTER UN REMBOURSEMENT
    # -------------------------------------------------

    st.divider()
    st.subheader("➕ Ajouter un remboursement")

    with st.form(
        "formulaire_remboursement",
        clear_on_submit=True,
    ):
        col1, col2, col3 = st.columns(3)

        with col1:
            date_remboursement = st.date_input(
                "Date du remboursement",
                value=date.today(),
                key="date_remboursement",
            )

        with col2:
            description_remboursement = (
                st.text_input(
                    "Description",
                    value=(
                        "Remboursement dette appartement"
                    ),
                )
            )

        with col3:
            montant_remboursement = (
                st.number_input(
                    "Montant remboursé",
                    min_value=0.0,
                    step=50.0,
                    format="%.2f",
                )
            )

        ajouter_remboursement = (
            st.form_submit_button(
                "Enregistrer le remboursement",
                use_container_width=True,
            )
        )

    if ajouter_remboursement:

        if montant_remboursement <= 0:
            st.error(
                "Le remboursement doit être "
                "supérieur à 0 €."
            )

        elif montant_remboursement > dette_restante:
            st.error(
                "Ce montant dépasse la dette restante "
                f"de {format_euros(dette_restante)}."
            )

        else:
            nouveau_remboursement = pd.DataFrame(
                [
                    {
                        "date": pd.to_datetime(
                            date_remboursement
                        ),
                        "description": (
                            description_remboursement
                            .strip()
                            or (
                                "Remboursement dette "
                                "appartement"
                            )
                        ),
                        "montant": float(
                            montant_remboursement
                        ),
                    }
                ]
            )

            remboursements = pd.concat(
                [
                    remboursements,
                    nouveau_remboursement,
                ],
                ignore_index=True,
            )

            enregistrer_remboursements(
                remboursements
            )

            st.success(
                "Remboursement enregistré."
            )

            st.rerun()

    # -------------------------------------------------
    # HISTORIQUE DES REMBOURSEMENTS
    # -------------------------------------------------

    st.divider()
    st.subheader(
        "📋 Historique des remboursements"
    )

    if remboursements.empty:
        st.info(
            "Tu n’as encore enregistré "
            "aucun remboursement."
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
                "description": "Description",
                "montant": "Montant remboursé",
            }
        )

        st.dataframe(
            historique,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Montant remboursé": (
                    st.column_config.NumberColumn(
                        "Montant remboursé",
                        format="%.2f €",
                    )
                ),
            },
        )

    # -------------------------------------------------
    # SUPPRIMER UN REMBOURSEMENT
    # -------------------------------------------------

    if not remboursements.empty:
        st.divider()
        st.subheader(
            "🗑️ Corriger un remboursement"
        )

        options_remboursements = {}

        for index, ligne in (
            remboursements.iterrows()
        ):
            texte = (
                f"{ligne['date'].strftime('%d/%m/%Y')}"
                f" — {ligne['description']}"
                f" — {format_euros(ligne['montant'])}"
                f" — n°{index + 1}"
            )

            options_remboursements[texte] = index

        remboursement_selectionne = (
            st.selectbox(
                "Remboursement à supprimer",
                list(
                    options_remboursements.keys()
                ),
            )
        )

        confirmation_remboursement = st.checkbox(
            "Je confirme la suppression "
            "de ce remboursement.",
            key="confirmation_remboursement",
        )

        if st.button(
            "Supprimer le remboursement",
            disabled=not confirmation_remboursement,
        ):
            index_a_supprimer = (
                options_remboursements[
                    remboursement_selectionne
                ]
            )

            remboursements = remboursements.drop(
                index=index_a_supprimer
            ).reset_index(drop=True)

            enregistrer_remboursements(
                remboursements
            )

            st.success(
                "Remboursement supprimé."
            )

            st.rerun()