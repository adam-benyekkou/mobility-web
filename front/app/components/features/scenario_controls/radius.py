import dash_mantine_components as dmc

def RadiusControl(
    id_prefix: str,
    *,
    min_radius: int = 15,
    max_radius: int = 50,
    step: int = 5,
    default: int | float = 40,
):
    """Crée un contrôle de sélection du rayon d’analyse (en kilomètres).

    Ce composant combine un **slider** et un **champ numérique synchronisé** 
    pour ajuster le rayon d’un scénario (ex. rayon d’étude autour d’une commune).
    Les identifiants Dash sont conservés pour assurer la compatibilité avec
    les callbacks existants.

    - Le slider permet une sélection visuelle du rayon.
    - Le `NumberInput` permet une saisie précise de la valeur.
    - Les deux sont alignés horizontalement et liés via leur `id_prefix`.

    Args:
        id_prefix (str): Préfixe pour les identifiants Dash.  
            Les IDs générés sont :
            - `"{id_prefix}-radius-slider"`
            - `"{id_prefix}-radius-input"`
        min_radius (int, optional): Valeur minimale du rayon (en km).  
            Par défaut `10`.
        max_radius (int, optional): Valeur maximale du rayon (en km).  
            Par défaut `50`.
        step (int, optional): Pas d’incrémentation pour le slider et l’input.  
            Par défaut `10`.
        default (int | float, optional): Valeur initiale du rayon (en km).  
            Par défaut `40`.

    Returns:
        dmc.Group: Composant Mantine contenant le label, le slider et le champ numérique.
    """
    return dmc.Group(
        [
            dmc.Text("Radius (15km)", fw=600, w=120, ta="right"),
            dmc.Slider(
                id=f"{id_prefix}-radius-slider",
                min=15,
                max=15,
                step=1,
                value=15,
                # marks=[{"value": 15, "label": "15km"}], # Removed as requested
                disabled=True,  # Lock it for MVP
                mb="xl",
            ),

        ],
        gap="md",
        align="center",
        justify="flex-start",
        wrap=False,
    )
