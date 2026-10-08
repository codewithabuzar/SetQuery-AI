import time

from analysis_router import run_routed_analysis

start_time = time.perf_counter()

routed = run_routed_analysis(
    latitude=25.54244,
    longitude=84.85161,
    before_date="2022-09-15",
    after_date="2025-09-15",
    radius_km=1,
)

elapsed = time.perf_counter() - start_time

print("Mode:", routed["mode"])
print("Has burn_evidence key:", "burn_evidence" in routed)
print("Has vegetation_stress key:", "vegetation_stress" in routed)

if routed["burn_evidence"]:
    print("Mean dNBR:", round(routed["burn_evidence"]["mean_dnbr"], 4))

if routed["vegetation_stress"]:
    print("Mean NDVI change:", round(routed["vegetation_stress"]["mean_ndvi_change"], 4))

print(f"Total time: {elapsed:.1f} seconds")