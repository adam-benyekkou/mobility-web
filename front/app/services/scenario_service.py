"""
scenario_service.py
===================

Service de construction de scénarios de mobilité (zones, parts modales, indicateurs).

Principes :
- Tente d’utiliser le module externe **`mobility`** pour générer des zones réalistes.
- Fournit un **fallback** déterministe Toulouse–Blagnac si `mobility` est indisponible.
- Crée systématiquement toutes les colonnes de parts (voiture, vélo, marche, covoiturage,
  transports en commun + sous-modes TC).
- Renormalise les parts sur les **modes actifs uniquement**.
- Recalcule un **temps moyen de trajet** sensible aux variables de coût par mode.
- Met à disposition un **cache LRU** pour les scénarios sans paramètres de modes.

Sortie principale (dict):
    - `zones_gdf` (GeoDataFrame, WGS84): zones avec géométries et indicateurs.
    - `flows_df` (DataFrame): tableau des flux (vide par défaut).
    - `zones_lookup` (GeoDataFrame, WGS84): points de référence des zones.
"""

from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point

# ------------------------------------------------------------
# Helpers & fallback
# ------------------------------------------------------------
def _to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Assure que le GeoDataFrame est en WGS84 (EPSG:4326).

    - Si le CRS est absent, le définit à 4326 (allow_override=True).
    - Si le CRS n’est pas 4326, reprojette en 4326.
    """
    if gdf.crs is None:
        return gdf.set_crs(4326, allow_override=True)
    try:
        epsg = gdf.crs.to_epsg()
    except Exception:
        epsg = None
    return gdf if epsg == 4326 else gdf.to_crs(4326)


# ------------------------------------------------------------
# In-memory global cache for precompiled cities to save RAM/CPU I/O
# ------------------------------------------------------------
_STATIC_GDF_CACHE: Dict[str, gpd.GeoDataFrame] = {}


def _load_static_fallback(lau: str, radius: float, params: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    """Tente de charger un fichier pré-calculé statique si présent et adapte selon les modes actifs."""
    base_path = Path(__file__).resolve().parents[1] / "data" / "precompiled"
    
    # Map normalized LAU to city filenames
    city_map = {
        "fr-75056": "paris_75056_static.gpkg",
        "fr-13055": "marseille_13055_static.gpkg",
        "fr-69123": "lyon_69123_static.gpkg",
        "fr-31555": "toulouse_31555_static.gpkg",
        "fr-06088": "nice_06088_static.gpkg",
        "fr-44109": "nantes_44109_static.gpkg",
        "fr-34172": "montpellier_34172_static.gpkg",
        "fr-67482": "strasbourg_67482_static.gpkg",
        "fr-33063": "bordeaux_33063_static.gpkg",
        "fr-59350": "lille_59350_static.gpkg"
    }
    
    filename = city_map.get(lau)
    if not filename:
        return None
        
    static_file = base_path / filename
    
    if static_file.exists():
        try:
            # Check Memory Cache First
            if filename in _STATIC_GDF_CACHE:
                gdf = _STATIC_GDF_CACHE[filename].copy()
                print(f"[SCENARIO] Using MEMORY CACHE for {lau}")
            else:
                print(f"[SCENARIO] Loading PRECOMPILED static data for {lau}: {static_file}")
                gdf = gpd.read_file(static_file)
                _STATIC_GDF_CACHE[filename] = gdf.copy()
            
            # Recalculate based on active modes
            if params:
                modes_map = {
                    "car": "car",
                    "bicycle": "bicycle",
                    "walk": "walk",
                    "carpool": "carpool",
                    "pt_walk": "pt_walk",
                    "pt_car": "pt_car",
                    "pt_bicycle": "pt_bicycle"
                }
                
                # Public transport submodes logic
                pt_active = bool(params.get("public_transport", {}).get("active", True))
                active_flags = {
                    "car": bool(params.get("car", {}).get("active", True)),
                    "bicycle": bool(params.get("bicycle", {}).get("active", True)),
                    "walk": bool(params.get("walk", {}).get("active", True)),
                    "carpool": bool(params.get("carpool", {}).get("active", True)),
                    "pt_walk": pt_active and bool(params.get("public_transport", {}).get("pt_walk", True)),
                    "pt_car": pt_active and bool(params.get("public_transport", {}).get("pt_car", True)),
                    "pt_bicycle": pt_active and bool(params.get("public_transport", {}).get("pt_bicycle", True)),
                }

                # Filter shares and recalculate average_travel_time
                active_modes = [m for m, active in active_flags.items() if active]
                
                if active_modes:
                    # Sum of shares of active modes
                    share_sum = gdf[[f"share_{m}" for m in active_modes]].sum(axis=1)
                    
                    # Prevent div by zero
                    share_sum = share_sum.replace(0, np.nan)
                    
                    # New weighted average travel time
                    weighted_time = sum(gdf[f"time_{m}"] * gdf[f"share_{m}"] for m in active_modes)
                    gdf["average_travel_time"] = weighted_time / share_sum
                    
                    # Update shares columns to reflect the filter (renormalized)
                    # This makes the summary panel / charts correct
                    for m in modes_map.keys():
                        if m in active_modes:
                            gdf[f"share_{m}"] = gdf[f"share_{m}"] / share_sum
                        else:
                            gdf[f"share_{m}"] = 0.0
                            
                    # Update display share_public_transport
                    gdf["share_public_transport"] = gdf[["share_pt_walk", "share_pt_car", "share_pt_bicycle"]].sum(axis=1)
                    
                    # Update other metrics (simplified)
                    weighted_dist = sum(gdf.get(f"dist_{m}", gdf["total_dist_km"]) * gdf[f"share_{m}"] for m in active_modes)
                    gdf["total_dist_km"] = weighted_dist
                    gdf["total_time_min"] = gdf["average_travel_time"] * 1.2
                    
            # Format attendu par le reste de l'app
            return {
                "zones_gdf": _to_wgs84(gdf),
                "flows_df": pd.DataFrame(columns=["from", "to", "flow_volume"]),
                "zones_lookup": _to_wgs84(gdf[["transport_zone_id", "geometry"]].copy()),
            }
        except Exception as e:
            print(f"[SCENARIO] Failed to load static precompiled data for {lau}: {e}")
    return None


def _fallback_scenario() -> Dict[str, Any]:
    """Scénario de secours (Paris) avec toutes les colonnes de parts (y compris TC)."""
    # Paris Center
    paris = (2.3522, 48.8566)
    
    pts = gpd.GeoDataFrame(
        {"transport_zone_id": ["paris"], "geometry": [Point(*paris)]},
        geometry="geometry",
        crs=4326,
    )

    zones = pts.to_crs(3857)
    zones["geometry"] = zones.geometry.buffer(5000)  # 5 km circle for dummy
    zones = zones.to_crs(4326)

    zones["average_travel_time"] = [25.0]
    zones["total_dist_km"] = [12.0]

    # Dummy Modal Share (Paris-like)
    zones["share_car"] = [0.20]
    zones["share_bicycle"] = [0.10]
    zones["share_walk"] = [0.40]
    zones["share_carpool"] = [0.05]

    zones["share_pt_walk"] = [0.15]
    zones["share_pt_car"] = [0.05]
    zones["share_pt_bicycle"] = [0.05]
    zones["share_public_transport"] = zones[["share_pt_walk", "share_pt_car", "share_pt_bicycle"]].sum(axis=1)
    
    zones["local_admin_unit_id"] = ["fr-75056"]

    empty_flows = pd.DataFrame(columns=["from", "to", "flow_volume"])
    return {"zones_gdf": _to_wgs84(zones), "flows_df": empty_flows, "zones_lookup": _to_wgs84(pts)}


def _normalize_lau_code(code: str) -> str:
    """Normalise un code INSEE/LAU au format `fr-xxxxx` si nécessaire."""
    s = str(code).strip().lower()
    if s.startswith("fr-"):
        return s
    if s.isdigit() and len(s) == 5:
        return f"fr-{s}"
    return s


# ------------------------------------------------------------
# Param helpers
# ------------------------------------------------------------
def _safe_cost_of_time(v_per_hour: float):
    """Objet léger pour compatibilité (valeur du temps en €/h)."""
    # On garde la présence de cette fonction pour compatibilité,
    # mais on n’instancie pas de modèles lourds ici.
    class _COT:
        def __init__(self, v): self.value_per_hour = float(v)
    return _COT(v_per_hour)


def _extract_vars(d: Dict[str, Any], defaults: Dict[str, float]) -> Dict[str, float]:
    """Récupère cost_constant / cost_of_time_eur_per_h / cost_of_distance_eur_per_km avec défauts."""
    return {
        "cost_constant": float((d or {}).get("cost_constant", defaults["cost_constant"])),
        "cost_of_time_eur_per_h": float((d or {}).get("cost_of_time_eur_per_h", defaults["cost_of_time_eur_per_h"])),
        "cost_of_distance_eur_per_km": float((d or {}).get("cost_of_distance_eur_per_km", defaults["cost_of_distance_eur_per_km"])),
    }


def _mode_cost_to_weight(vars_: Dict[str, float], base_minutes: float) -> float:
    """Convertit des variables de coût d’un mode en un poids-temps synthétique (minutes).

    Plus les coûts sont élevés, plus le "poids" est haut (→ augmente average_travel_time si
    la part du mode est forte). Transformation simple, stable et déterministe.
    """
    cc = vars_["cost_constant"]                # €
    cot = vars_["cost_of_time_eur_per_h"]      # €/h
    cod = vars_["cost_of_distance_eur_per_km"] # €/km
    return (
        base_minutes
        + 0.6 * (cot)          # €/h → ~impact direct
        + 4.0 * (cod)          # €/km → faible
        + 0.8 * (cc)           # €
    )


# ------------------------------------------------------------
# Core computation (robuste aux modes manquants)
# ------------------------------------------------------------
def _compute_scenario(
    local_admin_unit_id: str = "75101",
    radius: float = 15.0,
    transport_modes_params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Calcule un scénario, remplit les parts des modes actifs, renormalise et dérive les indicateurs."""
    # --- NEW: Check for precompiled static data FIRST to bypass heavy R/Osmium
    lau_norm = _normalize_lau_code(local_admin_unit_id or "75101")
    static = _load_static_fallback(lau_norm, float(radius), transport_modes_params)
    if static:
        return static

    try:
        import mobility
    except Exception as e:
        print(f"[SCENARIO] fallback (mobility indisponible): {e}")
        return _fallback_scenario()

    p = transport_modes_params or {}
    # états d’activation des modes principaux
    active = {
        "car": bool(p.get("car", {}).get("active", True)),
        "bicycle": bool(p.get("bicycle", {}).get("active", True)),
        "walk": bool(p.get("walk", {}).get("active", True)),
        "carpool": bool(p.get("carpool", {}).get("active", True)),
        "public_transport": bool(p.get("public_transport", {}).get("active", True)),
    }
    # états des sous-modes TC
    pt_sub = {
        "walk_pt": bool((p.get("public_transport", {}) or {}).get("pt_walk", True)),
        "car_pt": bool((p.get("public_transport", {}) or {}).get("pt_car", True)),
        "bicycle_pt": bool((p.get("public_transport", {}) or {}).get("pt_bicycle", True)),
    }

    # Variables des modes (avec défauts souhaités : 12€/h ; 0.01€/km ; 1€)
    defaults = {"cost_constant": 1.0, "cost_of_time_eur_per_h": 12.0, "cost_of_distance_eur_per_km": 0.01}
    vars_car      = _extract_vars(p.get("car"), defaults)
    vars_bicycle  = _extract_vars(p.get("bicycle"), defaults)
    vars_walk     = _extract_vars(p.get("walk"), defaults)
    vars_carpool  = _extract_vars(p.get("carpool"), defaults)
    vars_pt       = _extract_vars(p.get("public_transport"), defaults)  # appliqué au bloc TC

    # Zones issues de mobility (géométrie réaliste) — sans lancer de modèles
    lau_norm = _normalize_lau_code(local_admin_unit_id or "75101")
    
    import os
    mobility.set_params(
        debug=True, 
        r_packages=False, # Disable R package check as they are pre-installed in Docker
        r_packages_download_method="auto",
        package_data_folder_path=os.environ.get("MOBILITY_PACKAGE_DATA_FOLDER"),
        project_data_folder_path=os.environ.get("MOBILITY_PROJECT_DATA_FOLDER")
    )
    tz = mobility.TransportZones(local_admin_unit_id=lau_norm, radius=float(radius), level_of_detail=0)
    try:
        zones = tz.get()[["transport_zone_id", "geometry", "local_admin_unit_id"]].copy()
    except Exception as e:
        print(f"[SCENARIO] Error during transport zones calculation for {lau_norm} @ {radius}km: {e}")
        # Fallback to dummy data if calculation fails
        return _fallback_scenario()

    zones_gdf = gpd.GeoDataFrame(zones, geometry="geometry")
    n = len(zones_gdf)

    # --- Initialisation TOUTES parts à 0
    for col in [
        "share_car", "share_bicycle", "share_walk", "share_carpool",
        "share_pt_walk", "share_pt_car", "share_pt_bicycle", "share_public_transport"
    ]:
        zones_gdf[col] = 0.0

    # --- Assigner des parts uniquement pour ce qui est actif (RNG déterministe)
    rng = np.random.default_rng(42)
    if active["car"]:
        zones_gdf["share_car"] = rng.uniform(0.25, 0.65, n)
    if active["bicycle"]:
        zones_gdf["share_bicycle"] = rng.uniform(0.05, 0.25, n)
    if active["walk"]:
        zones_gdf["share_walk"] = rng.uniform(0.05, 0.30, n)
    if active["carpool"]:
        zones_gdf["share_carpool"] = rng.uniform(0.03, 0.20, n)

    if active["public_transport"]:
        if pt_sub["walk_pt"]:
            zones_gdf["share_pt_walk"] = rng.uniform(0.03, 0.15, n)
        if pt_sub["car_pt"]:
            zones_gdf["share_pt_car"] = rng.uniform(0.02, 0.12, n)
        if pt_sub["bicycle_pt"]:
            zones_gdf["share_pt_bicycle"] = rng.uniform(0.01, 0.08, n)
        zones_gdf["share_public_transport"] = zones_gdf[["share_pt_walk", "share_pt_car", "share_pt_bicycle"]].sum(axis=1)

    # --- Renormalisation : uniquement sur les colonnes présentes/actives
    cols_all = [
        "share_car", "share_bicycle", "share_walk", "share_carpool",
        "share_pt_walk", "share_pt_car", "share_pt_bicycle"
    ]
    active_cols = []
    if active["car"]: active_cols.append("share_car")
    if active["bicycle"]: active_cols.append("share_bicycle")
    if active["walk"]: active_cols.append("share_walk")
    if active["carpool"]: active_cols.append("share_carpool")
    if active["public_transport"] and pt_sub["walk_pt"]: active_cols.append("share_pt_walk")
    if active["public_transport"] and pt_sub["car_pt"]: active_cols.append("share_pt_car")
    if active["public_transport"] and pt_sub["bicycle_pt"]: active_cols.append("share_pt_bicycle")

    if not active_cols:
        # Rien d'actif → fallback
        return _fallback_scenario()

    total = zones_gdf[active_cols].sum(axis=1).replace(0, np.nan)
    for col in cols_all:
        if col in zones_gdf.columns:
            zones_gdf[col] = zones_gdf[col] / total
    zones_gdf = zones_gdf.fillna(0.0)
    zones_gdf["share_public_transport"] = zones_gdf[["share_pt_walk", "share_pt_car", "share_pt_bicycle"]].sum(axis=1)

    # --- Recalcul average_travel_time sensible aux variables (Option B)
    base_minutes = {
        "car": 20.0, "bicycle": 15.0, "walk": 25.0, "carpool": 18.0, "public_transport": 22.0
    }
    W = {
        "car": _mode_cost_to_weight(vars_car, base_minutes["car"]),
        "bicycle": _mode_cost_to_weight(vars_bicycle, base_minutes["bicycle"]),
        "walk": _mode_cost_to_weight(vars_walk, base_minutes["walk"]),
        "carpool": _mode_cost_to_weight(vars_carpool, base_minutes["carpool"]),
        "public_transport": _mode_cost_to_weight(vars_pt, base_minutes["public_transport"]),
    }
    zones_gdf["average_travel_time"] = (
        zones_gdf["share_car"] * W["car"]
        + zones_gdf["share_bicycle"] * W["bicycle"]
        + zones_gdf["share_walk"] * W["walk"]
        + zones_gdf["share_carpool"] * W["carpool"]
        + zones_gdf["share_public_transport"] * W["public_transport"]
    )

    # --- Autres indicateurs synthétiques (déterministes et sans RNG)
    # Distance "typique" proportionnelle à la racine de la surface (km).
    zones_gdf["total_dist_km"] = zones_gdf.geometry.area ** 0.5 / 1000

    # Types cohérents & WGS84
    zones_gdf["transport_zone_id"] = zones_gdf["transport_zone_id"].astype(str)
    zones_lookup = gpd.GeoDataFrame(
        zones[["transport_zone_id", "geometry"]].astype({"transport_zone_id": str}),
        geometry="geometry",
        crs=zones_gdf.crs,
    )

    return {
        "zones_gdf": _to_wgs84(zones_gdf),
        "flows_df": pd.DataFrame(columns=["from", "to", "flow_volume"]),
        "zones_lookup": _to_wgs84(zones_lookup),
    }


# ------------------------------------------------------------
#  API public + cache
# ------------------------------------------------------------
def _normalized_key(local_admin_unit_id: str, radius: float) -> Tuple[str, float]:
    """Retourne la clé normalisée (LAU, rayon) pour le cache LRU."""
    lau = _normalize_lau_code(local_admin_unit_id or "75101")
    rad = round(float(radius), 4)
    return (lau, rad)


@lru_cache(maxsize=32)
def _get_scenario_cached(lau: str, rad: float) -> Dict[str, Any]:
    """Version mise en cache (pas de `transport_modes_params`)."""
    return _compute_scenario(local_admin_unit_id=lau, radius=rad, transport_modes_params=None)


def get_scenario(
    local_admin_unit_id: str = "75101",
    radius: float = 15.0,
    transport_modes_params: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """API principale : construit un scénario (avec cache si pas de params modes)."""
    lau, rad = _normalized_key(local_admin_unit_id, radius)
    if not transport_modes_params:
        return _get_scenario_cached(lau, rad)
    return _compute_scenario(local_admin_unit_id=lau, radius=rad, transport_modes_params=transport_modes_params)


def clear_scenario_cache() -> None:
    """Vide le cache LRU des scénarios sans paramètres de modes."""
    _get_scenario_cached.cache_clear()
