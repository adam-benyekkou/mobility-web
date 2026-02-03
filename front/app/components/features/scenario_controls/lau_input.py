import dash_mantine_components as dmc

def LauInput(id_prefix: str, *, default_insee: str = "75056"):
    """Crée un champ de saisie pour la zone d’étude (code INSEE ou LAU).

    Ce composant permet à l’utilisateur d’indiquer le code de la commune ou
    unité administrative locale utilisée comme point de référence pour le scénario.
    Le champ est pré-rempli avec un code par défaut (par exemple, Toulouse : `31555`)
    et conserve les identifiants Dash existants pour compatibilité avec les callbacks.

    Args:
        id_prefix (str): Préfixe pour l’identifiant du composant Dash.  
            L’ID généré est de la forme `"{id_prefix}-lau-input"`.
        default_insee (str, optional): Code INSEE ou LAU affiché par défaut.  
            Par défaut `"31555"`.

    Returns:
        dmc.TextInput: Champ de saisie Mantine configuré pour l’entrée du code INSEE/LAU.
    """
    return dmc.Select(
        label="Select a City",
        # description="Choose a city for analysis",
        placeholder="Select one...",
        id=f"{id_prefix}-lau-input",
        value=default_insee,
        data=[
            {"label": "Paris", "value": "75056"},
            {"label": "Marseille", "value": "13055"},
            {"label": "Lyon", "value": "69123"},
            {"label": "Toulouse", "value": "31555"},
            {"label": "Nice", "value": "06088"},
            {"label": "Nantes", "value": "44109"},
            {"label": "Montpellier", "value": "34172"},
            {"label": "Strasbourg", "value": "67482"},
            {"label": "Bordeaux", "value": "33063"},
            {"label": "Lille", "value": "59350"},
        ],
        searchable=False,  # Prevent typing to avoid confusion
        clearable=False,
        mt="lg",
        mb="md",
        w=250,
        comboboxProps={"zIndex": 99999},
        style={"zIndex": 99999, "position": "relative"},
    )
