import sys
import time
import shutil
import gc
import psutil
import os
from pathlib import Path
from mobility.set_params import set_params

# Add app to path
sys.path.append(str(Path(__file__).resolve().parents[0]))

from app.services.scenario_service import get_scenario

# List of LAU codes (cities) to precalculate
# [MVP] Reduced list to prevent WSL crashing
CITIES_TO_PRECALC = {
    "75101": "Paris"
}
# Optimized radii list to cover small, medium, and large scales without excessive build time
# REDUCED to 15km to verify build stability (avoid OOM during build)
RADII_TO_PRECALC = [5.0]

def run_precalc():
    # CRITICAL: Nuclear cleanup of the projects directory to clear ALL hidden caches/flags
    data_dir = Path(os.environ.get("MOBILITY_PACKAGE_DATA_FOLDER", "/home/mambauser/.mobility/data"))
    projects_dir = data_dir / "projects"
    building_dir = data_dir / "buildings"
    if projects_dir.exists():
        print(f"Nuclear Cleanup: Removing all existing project data at {projects_dir}...")
        # We don't delete the root projects dir but its contents
        for item in projects_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    
    # Re-ensure the projects directory exists (it might have been deleted if it was empty)
    projects_dir.mkdir(parents=True, exist_ok=True)
    
    # Enable debug for better R logs
    set_params(debug=True)

    total_tasks = len(CITIES_TO_PRECALC) * len(RADII_TO_PRECALC)
    print(f"--- Starting Precalculation for {len(CITIES_TO_PRECALC)} cities x {len(RADII_TO_PRECALC)} radii ---")
    print(f"Total scenarios to run: {total_tasks}\n")
    
    start_time = time.time()
    count = 0
    
    for lau, name in CITIES_TO_PRECALC.items():
        print(f"=== Processing City: {name} ({lau}) ===")
        # [NEW] Clear city-specific building data if it exists (handles partial corrupt results)
        building_city_dir = building_dir / f"fr-{lau}"
        if building_city_dir.exists():
            print(f"  Removing existing building data for {name}...")
            shutil.rmtree(building_city_dir)

        for r in RADII_TO_PRECALC:
            count += 1
            step_start = time.time()
            print(f"[{count}/{total_tasks}] Running {name} - Radius {int(r)}km...", end=" ", flush=True)
            try:
                # Triggers downloading and processing
                get_scenario(local_admin_unit_id=lau, radius=r)
                elapsed = time.time() - step_start
                print(f"DONE in {elapsed:.1f}s")
            except Exception as e:
                print(f"FAILED: {e}")
            
            # CRITICAL: Clean up memory after each task
            gc.collect()
            mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
            print(f"Memory: {mem:.1f} MB")

    total_time = time.time() - start_time
    print(f"\n--- All Precalculations Finished in {total_time:.1f}s ---")
    print("Precalculated data is stored in ~/.mobility/data")

if __name__ == "__main__":
    run_precalc()
