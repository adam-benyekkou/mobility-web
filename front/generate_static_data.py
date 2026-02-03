import os
import pathlib
import geopandas as gpd
import pandas as pd
import numpy as np
import mobility
from mobility.parsers.local_admin_units import LocalAdminUnits

def generate_city_data(city_name, lau_code, output_path):
    print(f"\n--- Generating data for {city_name.upper()} ({lau_code}) ---")
    
    # Setup mobility params
    os.environ["MOBILITY_PACKAGE_DATA_FOLDER"] = "/home/mambauser/.mobility/data"
    os.environ["MOBILITY_PROJECT_DATA_FOLDER"] = "/home/mambauser/.mobility/data/projects"
    
    # Get Geometries from LocalAdminUnits (BYPASS TransportZones/OSM)
    try:
        print(f"Fetching communal geometries from LocalAdminUnits for {lau_code}...")
        lau_parser = LocalAdminUnits()
        all_lau = lau_parser.get()
        
        # Find the center geometry
        center_zone = all_lau[all_lau["local_admin_unit_id"] == lau_code]
        if center_zone.empty:
            print(f"Center zone {lau_code} not found! Falling back to dept.")
            target_dep = lau_code[3:5] if lau_code.startswith("fr-") else lau_code[:2]
            zones = all_lau[all_lau["local_admin_unit_id"].str.contains(f"fr-{target_dep}")].copy().head(150)
        else:
            # 15km Radius Strategy (Metric Projection)
            # 1. Project to Lambert-93 (France standard metric) for accurate distance
            all_lau_metric = all_lau.to_crs(2154)
            center_metric = all_lau_metric[all_lau_metric["local_admin_unit_id"] == lau_code]
            
            # 2. Create 15km buffer (15000 meters)
            center_geom = center_metric.geometry.iloc[0]
            buffer_area = center_geom.buffer(15000) 
            
            # 3. Intersect
            # We want communes that are mostly within or touching? standard is intersects.
            mask = all_lau_metric.geometry.intersects(buffer_area)
            zones_metric = all_lau_metric[mask]
            
            # 4. Project back to WGS84
            zones = zones_metric.to_crs(4326).copy()
            
        print(f"Found {len(zones)} communes within 15km radius of {lau_code}")
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
    cities = [
        ("paris", "fr-75056"),
        ("marseille", "fr-13055"),
        ("lyon", "fr-69123"),
        ("toulouse", "fr-31555"),
        ("nice", "fr-06088"),
        ("nantes", "fr-44109"),
        ("montpellier", "fr-34172"),
        ("strasbourg", "fr-67482"),
        ("bordeaux", "fr-33063"),
        ("lille", "fr-59350")
    ]
    
    base_dir = "front/app/data/precompiled"
    for name, lau in cities:
        output = f"{base_dir}/{name}_{lau.replace('fr-', '')}_static.gpkg"
        generate_city_data(name, lau, output)
