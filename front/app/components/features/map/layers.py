from typing import List, Dict
import pandas as pd
import numpy as np
import pydeck as pdk
import geopandas as gpd

from .geo_utils import ensure_wgs84, as_polygon_rings, fmt_num, fmt_pct

# ColorScale est supposé fourni ailleurs (fit_color_scale), injecté via deck_factory
# Ici, on ne change pas la palette : on utilise le champ "average_travel_time".


def _polygons_records(zones_gdf: gpd.GeoDataFrame, scale) -> List[Dict]:
    g = ensure_wgs84(zones_gdf)
    out = []
    for _, row in g.iterrows():
        rings = as_polygon_rings(row.geometry)
        if not rings:
            continue

        zone_id = row.get("transport_zone_id", "Zone inconnue")
        insee = row.get("local_admin_unit_id", "N/A")

        avg_tt = pd.to_numeric(row.get("average_travel_time", np.nan), errors="coerce")
        total_dist_km = pd.to_numeric(row.get("total_dist_km", np.nan), errors="coerce")
        total_time_min = pd.to_numeric(row.get("total_time_min", np.nan), errors="coerce")

        share_car = pd.to_numeric(row.get("share_car", np.nan), errors="coerce")
        share_bicycle = pd.to_numeric(row.get("share_bicycle", np.nan), errors="coerce")
        share_walk = pd.to_numeric(row.get("share_walk", np.nan), errors="coerce")
        share_carpool = pd.to_numeric(row.get("share_carpool", np.nan), errors="coerce")
        share_pt = pd.to_numeric(row.get("share_public_transport", np.nan), errors="coerce")

        for ring in rings:
            out.append(
                {
                    "geometry": [[float(x), float(y)] for x, y in ring],
                    "fill_rgba": scale.rgba(avg_tt),
                    "INSEE Unit": str(insee),
                    "Zone ID": str(zone_id),
                    "Avg. Travel Time (min)": fmt_num(avg_tt, 1),
                    "Accessibility Level": scale.legend(avg_tt),
                    "Total Distance (km/day)": fmt_num(total_dist_km, 1),
                    "Total Travel Time (min/day)": fmt_num(total_time_min, 1),
                    "Car Share (%)": fmt_pct(share_car, 1),
                    "Cycling Share (%)": fmt_pct(share_bicycle, 1),
                    "Walking Share (%)": fmt_pct(share_walk, 1),
                    "Carpool Share (%)": fmt_pct(share_carpool, 1),
                    "Public Transport Share (%)": fmt_pct(share_pt, 1),
                }
            )
    return out


def build_zones_layer(zones_gdf: gpd.GeoDataFrame, scale) -> pdk.Layer | None:
    polys = _polygons_records(zones_gdf, scale)
    if not polys:
        return None
    return pdk.Layer(
        "PolygonLayer",
        data=polys,
        get_polygon="geometry",
        get_fill_color="fill_rgba",
        pickable=True,
        filled=True,
        stroked=True,
        get_line_color=[0, 0, 0, 80],
        lineWidthMinPixels=1.5,
        elevation_scale=0,
        opacity=0.4,
        auto_highlight=True,
    )
