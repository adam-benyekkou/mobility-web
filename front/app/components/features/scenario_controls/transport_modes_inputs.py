import dash_mantine_components as dmc
from dash import html

# -------------------------
# Données mock : 5 modes (PT inclus) + sous-modes PT
# -------------------------
MOCK_MODES = [
    {
        "name": "Walking",
        "active": True,
        "vars": {
            "Time Value (€/h)": 12,
            "Distance Value (€/km)": 0.01,
            "Mode Constant (€)": 1,
        },
    },
    {
        "name": "Cycling",
        "active": True,
        "vars": {
            "Time Value (€/h)": 12,
            "Distance Value (€/km)": 0.01,
            "Mode Constant (€)": 1,
        },
    },
    {
        "name": "Car",
        "active": True,
        "vars": {
            "Time Value (€/h)": 12,
            "Distance Value (€/km)": 0.01,
            "Mode Constant (€)": 1,
        },
    },
    {
        "name": "Carpooling",
        "active": True,
        "vars": {
            "Time Value (€/h)": 12,
            "Distance Value (€/km)": 0.01,
            "Mode Constant (€)": 1,
        },
    },
    {
        "name": "Public Transport",
        "active": True,  # coché par défaut
        "vars": {
            "Time Value (€/h)": 12,
            "Distance Value (€/km)": 0.01,
            "Mode Constant (€)": 1,
        },
        "pt_submodes": {
            # 3 sous-modes cochés par défaut
            "walk_pt": True,
            "car_pt": True,
            "bicycle_pt": True,
        },
    },
]

VAR_SPECS = {
    "Time Value (€/h)": {"min": 0, "max": 50, "step": 1},
    "Distance Value (€/km)": {"min": 0, "max": 2, "step": 0.1},
    "Mode Constant (€)": {"min": 0, "max": 20, "step": 1},
}

PT_SUB_LABELS = {
    "walk_pt": "Walk + PT",
    "car_pt": "Car + PT",
    "bicycle_pt": "Bike + PT",
}

PT_COLOR = "#e5007d"  # rouge/magenta du logo AREP


def _mode_header(mode):
    """Crée l'en-tête d'un mode de transport avec case à cocher et tooltip d'avertissement.

    Cette fonction construit un composant `dmc.Group` contenant :
      - une case à cocher permettant d'activer ou désactiver le mode ;
      - un texte affichant le nom du mode ;
      - un tooltip rouge s'affichant si l'utilisateur tente de désactiver tous les modes.

    Args:
        mode (dict): Dictionnaire représentant un mode de transport, issu de MOCK_MODES.

    Returns:
        dmc.Group: Composant Mantine contenant la case à cocher, le texte et le tooltip.
    """
    return dmc.Group(
        [
            dmc.Tooltip(
                label="At least one mode must remain active",
                position="right",
                withArrow=True,
                color=PT_COLOR,
                opened=False,
                withinPortal=True,
                zIndex=9999,
                transitionProps={"transition": "fade", "duration": 300, "timingFunction": "ease-in-out"},
                id={"type": "mode-tip", "index": mode["name"]},
                children=dmc.Checkbox(
                    id={"type": "mode-active", "index": mode["name"]},
                    checked=mode["active"],
                ),
            ),
            dmc.Text(mode["name"], fw=700),
        ],
        gap="sm",
        align="center",
        w="100%",
    )


def _pt_submodes_block(mode):
    """Construit le bloc des sous-modes pour le transport en commun (TC).

    Crée une pile verticale de cases à cocher correspondant aux sous-modes :
    - Marche + TC
    - Voiture + TC
    - Vélo + TC

    Chaque case est associée à un tooltip rouge indiquant qu'au moins un sous-mode
    doit rester activé.

    Args:
        mode (dict): Dictionnaire décrivant le mode "Transport en commun" et ses sous-modes.

    Returns:
        dmc.Stack: Bloc vertical contenant les sous-modes configurables.
    """
    pt_cfg = mode.get("pt_submodes") or {}
    rows = []
    for key, label in PT_SUB_LABELS.items():
        rows.append(
            dmc.Group(
                [
                    dmc.Tooltip(
                        label="At least one PT submode must remain active",
                        position="right",
                        withArrow=True,
                        color=PT_COLOR,
                        opened=False,
                        withinPortal=True,
                        zIndex=9999,
                        transitionProps={"transition": "fade", "duration": 300, "timingFunction": "ease-in-out"},
                        id={"type": "pt-tip", "index": key},
                        children=dmc.Checkbox(
                            id={"type": "pt-submode", "index": key},
                            checked=bool(pt_cfg.get(key, True)),
                        ),
                    ),
                    dmc.Text(label, size="sm"),
                ],
                gap="sm",
                align="center",
            )
        )
    return dmc.Stack(rows, gap="xs")


def _mode_body(mode):
    """Construit le corps (contenu détaillé) d'un mode de transport.

    Ce bloc inclut les paramètres numériques (valeur du temps, distance, constante)
    sous forme de champs `NumberInput`. Si le mode est "Transport en commun",
    le corps inclut également la section des sous-modes.

    Args:
        mode (dict): Dictionnaire décrivant un mode de transport avec ses variables.

    Returns:
        dmc.Stack: Bloc vertical avec les variables d'entrée et, si applicable, les sous-modes TC.
    """
    rows = []
    # Variables principales
    for label, val in mode["vars"].items():
        spec = VAR_SPECS[label]
        rows.append(
            dmc.Group(
                [
                    dmc.Text(label),
                    dmc.NumberInput(
                        value=val,
                        min=spec["min"],
                        max=spec["max"],
                        step=spec["step"],
                        style={"width": 140},
                        id={"type": "mode-var", "mode": mode["name"], "var": label},
                    ),
                ],
                justify="space-between",
                align="center",
            )
        )
    # Sous-modes TC
    if mode["name"] == "Public Transport":
        rows.append(dmc.Divider())
        rows.append(dmc.Text("Submodes (Cumulative)", size="sm", fw=600))
        rows.append(_pt_submodes_block(mode))
    return dmc.Stack(rows, gap="md")


def _modes_list():
    """Construit la liste complète des modes de transport sous forme d'accordéon.

    Chaque item correspond à un mode de transport (piéton, vélo, voiture, etc.)
    et contient :
      - un en-tête (nom + case à cocher) ;
      - un panneau dépliable avec les paramètres et sous-modes.

    Returns:
        dmc.Accordion: Accordéon Mantine contenant tous les modes configurables.
    """
    items = [
        dmc.AccordionItem(
            [dmc.AccordionControl(_mode_header(m)), dmc.AccordionPanel(_mode_body(m))],
            value=f"mode-{i}",
        )
        for i, m in enumerate(MOCK_MODES)
    ]
    return dmc.Accordion(
        children=items,
        multiple=True,
        value=[],
        chevronPosition="right",
        chevronSize=18,
        variant="separated",
        radius="md",
        styles={"control": {"paddingTop": 8, "paddingBottom": 8}},
    )


def TransportModesInputs(id_prefix="tm"):
    """Construit le panneau principal "MODES DE TRANSPORT".

    Ce composant est un accordéon englobant la liste complète des modes
    et permet à l'utilisateur d'activer, désactiver ou ajuster les paramètres
    de chaque mode.

    Args:
        id_prefix (str, optional): Préfixe d'identifiants pour les callbacks Dash. 
            Par défaut "tm".

    Returns:
        dmc.Accordion: Accordéon principal contenant tous les contrôles des modes.
    """
    return dmc.Accordion(
        children=[
            dmc.AccordionItem(
                [
                    dmc.AccordionControl(
                        dmc.Group(
                            [dmc.Text("TRANSPORT MODES", fw=700), html.Div(style={"flex": 1})],
                            align="center",
                        )
                    ),
                    dmc.AccordionPanel(_modes_list()),
                ],
                value="tm-root",
            )
        ],
        multiple=True,
        value=[],
        chevronPosition="right",
        chevronSize=18,
        variant="separated",
        radius="lg",
        styles={"control": {"paddingTop": 10, "paddingBottom": 10}},
    )
