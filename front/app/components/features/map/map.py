import json
import pydeck as pdk
import dash_deck
from dash import html
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from app.scenario.scenario_001_from_docs import load_scenario


# ---------- CONSTANTES ----------
CARTO_POSITRON_GL = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
FALLBACK_CENTER = (2.2137, 46.2276)  # France (approx. center)


# ---------- HELPERS ----------

def _centroids_lonlat(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calcule les centroides en coordonnées géographiques (lon/lat)."""
    g = gdf.copy()
    if g.crs is None:
        g = g.set_crs(4326, allow_override=True)
    g_m = g.to_crs(3857)
    pts_m = g_m.geometry.centroid
    pts_ll = gpd.GeoSeries(pts_m, crs=g_m.crs).to_crs(4326)
    g["lon"] = pts_ll.x.astype("float64")
    g["lat"] = pts_ll.y.astype("float64")
    return g


def _fmt_num(v, nd=1):
    try:
        return f"{round(float(v), nd):.{nd}f}"
    except Exception:
        return "N/A"


def _fmt_pct(v, nd=1):
    try:
        return f"{round(float(v) * 100.0, nd):.{nd}f} %"
    except Exception:
        return "N/A"


def _polygons_for_layer(zones_gdf: gpd.GeoDataFrame):
    """
    Prépare les polygones pour Deck.gl :
    - geometry / fill_rgba : nécessaires au rendu
    - champs “métier” (INSEE/Zone/Temps/Niveau + stats & parts modales) : pour le tooltip
    """
    g = zones_gdf
    if g.crs is None or getattr(g.crs, "to_epsg", lambda: None)() != 4326:
        g = g.to_crs(4326)

    polygons = []
    for _, row in g.iterrows():
        geom = row.geometry
        zone_id = row.get("transport_zone_id", "Zone inconnue")
        insee = row.get("local_admin_unit_id", "N/A")
        travel_time = _fmt_num(row.get("average_travel_time", np.nan), 1)
        legend = row.get("__legend", "")

        # Stats “par personne et par jour”
        total_dist_km = _fmt_num(row.get("total_dist_km", np.nan), 1)
        total_time_min = _fmt_num(row.get("total_time_min", np.nan), 1)

        # Parts modales
        share_car = _fmt_pct(row.get("share_car", np.nan), 1)
        share_bicycle = _fmt_pct(row.get("share_bicycle", np.nan), 1)
        share_walk = _fmt_pct(row.get("share_walk", np.nan), 1)

        color = row.get("__color", [180, 180, 180, 160])

        if isinstance(geom, Polygon):
            rings = [list(geom.exterior.coords)]
        elif isinstance(geom, MultiPolygon):
            rings = [list(p.exterior.coords) for p in geom.geoms]
        else:
            continue

        for ring in rings:
            polygons.append({
                # ⚙️ Champs techniques pour le rendu
                "geometry": [[float(x), float(y)] for x, y in ring],
                "fill_rgba": color,
                # ✅ Champs métier visibles dans le tooltip (clés FR)
                "INSEE Unit": str(insee),
                "Zone ID": str(zone_id),
                "Avg. Travel Time (min)": travel_time,
                "Accessibility Level": legend,
                "Total Distance (km/day)": total_dist_km,
                "Total Travel Time (min/day)": total_time_min,
                "Car Share (%)": share_car,
                "Cycling Share (%)": share_bicycle,
                "Walking Share (%)": share_walk,
            })
    return polygons


# ---------- DECK FACTORY ----------

def _deck_json():
    layers = []
    lon_center, lat_center = FALLBACK_CENTER

    # Initial Empty Map - waiting for user selection
    # No layers, just the base map centered on France
    pass

    # Vue centrée
    view_state = pdk.ViewState(
        longitude=lon_center,
        latitude=lat_center,
        zoom=5,
        pitch=0,
        bearing=0,
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_provider="carto",
        map_style=CARTO_POSITRON_GL,
        views=[pdk.View(type="MapView", controller=True)],
    )

    return deck.to_json()


# ---------- DASH COMPONENT ----------

def Map():
    deckgl = dash_deck.DeckGL(
        id="deck-map",
        data=_deck_json(),
        # Tooltip personnalisé (aucun champ technique)
        tooltip={
            "html": (
                "<div style='font-family:Arial, sans-serif;'>"
                "<b style='font-size:14px;'>Study Area</b><br>"
                "<b>INSEE Unit:</b> {INSEE Unit}<br/>"
                "<b>Zone ID:</b> {Zone ID}<br/><br/>"
                "<b style='font-size:13px;'>Average Mobility</b><br>"
                "Avg. Travel Time: <b>{Avg. Travel Time (min)}</b> min/day<br>"
                "Total Distance: <b>{Total Distance (km/day)}</b> km/day<br>"
                "Accessibility Level: <b>{Accessibility Level}</b><br/><br/>"
                "<b style='font-size:13px;'>Modal Split</b><br>"
                "Car Share: <b>{Car Share (%)}</b><br>"
                "Cycling Share: <b>{Cycling Share (%)}</b><br>"
                "Walking Share: <b>{Walking Share (%)}</b>"
                "</div>"
            ),
            "style": {
                "backgroundColor": "rgba(255,255,255,0.9)",
                "color": "#111",
                "fontSize": "12px",
                "padding": "8px",
                "borderRadius": "6px",
            },
        },
        mapboxKey="",
        style={"position": "absolute", "inset": 0},
    )

    return html.Div(
        deckgl,
        style={
            "position": "relative",
            "width": "100%",
            "height": "100%",
            "background": "#fff",
        },
    )
