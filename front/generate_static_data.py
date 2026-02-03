import os
import pathlib
import geopandas as gpd
import pandas as pd
import numpy as np
import mobility
from shapely.geometry import Point
from mobility.parsers.local_admin_units import LocalAdminUnits

# Hardcoded centers to ensure perfect 15km radius even if LAU codes are weird (e.g. Lyon arrondissements)
CITY_CENTERS = {
    "fr-75056": {"name": "Paris", "coords": (2.3522, 48.8566)},
    "fr-13055": {"name": "Marseille", "coords": (5.3698, 43.2965)},
    "fr-69123": {"name": "Lyon", "coords": (4.8357, 45.7640)},
    "fr-31555": {"name": "Toulouse", "coords": (1.4442, 43.6045)},
    "fr-06088": {"name": "Nice", "coords": (7.2620, 43.7102)},
    "fr-44109": {"name": "Nantes", "coords": (-1.5536, 47.2184)},
    "fr-34172": {"name": "Montpellier", "coords": (3.8767, 43.6108)},
    "fr-67482": {"name": "Strasbourg", "coords": (7.7521, 48.5734)},
    "fr-33063": {"name": "Bordeaux", "coords": (-0.5792, 44.8378)},
    "fr-59350": {"name": "Lille", "coords": (3.0573, 50.6292)}
}

def generate_city_data(city_name, lau_code, output_path):
    print(f"\n--- Generating data for {city_name.upper()} ({lau_code}) ---")
    
    # Setup mobility params
    os.environ["MOBILITY_PACKAGE_DATA_FOLDER"] = "/home/mambauser/.mobility/data"
    os.environ["MOBILITY_PROJECT_DATA_FOLDER"] = "/home/mambauser/.mobility/data/projects"
    
    try:
        print(f"Fetching all geometries from LocalAdminUnits...")
        lau_parser = LocalAdminUnits()
        all_lau = lau_parser.get()
        
        # 1. Project to Lambert-93 (France standard metric) for accurate 15km buffer
        all_lau_metric = all_lau.to_crs(2154)
        
        # 2. Get Center Point
        if lau_code in CITY_CENTERS:
            # Use reliable hardcoded coordinates
            lon, lat = CITY_CENTERS[lau_code]["coords"]
            # Create point in WGS84 then project
            center_pt = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(2154).iloc[0]
            print(f"Using hardcoded center for {city_name}: {lon}, {lat}")
        else:
            # Fallback to LAU geometry lookup
             center_zone = all_lau_metric[all_lau_metric["local_admin_unit_id"] == lau_code]
             if center_zone.empty:
                 print(f"CRITICAL: Center {lau_code} not found. Skipping.")
                 return
             center_pt = center_zone.geometry.centroid.iloc[0]

        # 3. Create 15km buffer (15000 meters) around the Point
        buffer_area = center_pt.buffer(15000)
        
        # 4. Intersect: Select communes that intersect with the buffer
        mask = all_lau_metric.geometry.intersects(buffer_area)
        zones_metric = all_lau_metric[mask]
        
        # 5. Project back to WGS84
        zones = zones_metric.to_crs(4326).copy()
            
        print(f"Found {len(zones)} contiguous communes within 15km radius of {city_name}")

    except Exception as e:
        print(f"Error fetching zones: {e}")
        return

    zones_gdf = gpd.GeoDataFrame(zones, geometry="geometry")
    zones_gdf = zones_gdf.to_crs(4326)
    n = len(zones_gdf)
    zones_gdf["transport_zone_id"] = zones_gdf["local_admin_unit_id"]
    
    # Add metrics
    np.random.seed(42)
    modes = ["car", "bicycle", "walk", "carpool", "pt_walk", "pt_car", "pt_bicycle"]
    
    for m in modes:
        if m == "car":
            zones_gdf[f"time_{m}"] = 10.0 + np.random.rand(n) * 15.0
            zones_gdf[f"dist_{m}"] = 8.0 + np.random.rand(n) * 15.0
            zones_gdf[f"share_{m}"] = 0.4 + np.random.rand(n) * 0.2
        elif m == "bicycle":
            zones_gdf[f"time_{m}"] = 20.0 + np.random.rand(n) * 15.0
            zones_gdf[f"dist_{m}"] = 5.0 + np.random.rand(n) * 10.0
            zones_gdf[f"share_{m}"] = 0.05 + np.random.rand(n) * 0.1
        elif m == "walk":
            zones_gdf[f"time_{m}"] = 30.0 + np.random.rand(n) * 40.0
            zones_gdf[f"dist_{m}"] = 1.0 + np.random.rand(n) * 3.0
            zones_gdf[f"share_{m}"] = 0.1 + np.random.rand(n) * 0.1
        elif m == "carpool":
            zones_gdf[f"time_{m}"] = 12.0 + np.random.rand(n) * 15.0
            zones_gdf[f"dist_{m}"] = 8.0 + np.random.rand(n) * 15.0
            zones_gdf[f"share_{m}"] = 0.05 + np.random.rand(n) * 0.05
        else: # PT variants
            zones_gdf[f"time_{m}"] = 25.0 + np.random.rand(n) * 20.0
            zones_gdf[f"dist_{m}"] = 7.0 + np.random.rand(n) * 15.0
            zones_gdf[f"share_{m}"] = 0.05 + np.random.rand(n) * 0.1

    share_cols = [f"share_{m}" for m in modes]
    row_sums = zones_gdf[share_cols].sum(axis=1)
    zones_gdf[share_cols] = zones_gdf[share_cols].div(row_sums, axis=0)
    
    zones_gdf["average_travel_time"] = sum(zones_gdf[f"time_{m}"] * zones_gdf[f"share_{m}"] for m in modes)
    zones_gdf["total_time_min"] = zones_gdf["average_travel_time"] * 1.2
    zones_gdf["total_dist_km"] = sum(zones_gdf[f"dist_{m}"] * zones_gdf[f"share_{m}"] for m in modes)
    zones_gdf["share_public_transport"] = zones_gdf["share_pt_walk"] + zones_gdf["share_pt_car"] + zones_gdf["share_pt_bicycle"]

    # Save with overwrite
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)
    zones_gdf.to_file(output_path, driver="GPKG")
    print(f"Successfully generated static data for {city_name} at {output_path}")

if __name__ == "__main__":
    base_dir = "front/app/data/precompiled"
    for lau, info in CITY_CENTERS.items():
        name = info["name"].lower()
        output = f"{base_dir}/{name}_{lau.replace('fr-', '')}_static.gpkg"
        generate_city_data(name, lau, output)
