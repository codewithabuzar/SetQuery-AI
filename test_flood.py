import time

from flood_analysis import analyze_flood_evidence

start_time = time.perf_counter()

result = analyze_flood_evidence(
    latitude=26.7333,
    longitude=67.6333,
    before_date="2022-05-01",
    after_date="2022-08-30",
    radius_km=5,
)

elapsed = time.perf_counter() - start_time

print("Method:", result["method"])
print("Orbit matched:", result["orbit_matched"])
print("Before observations:", result["before_observations"])
print("After observations:", result["after_observations"])
print()
print("Before mean VV (dB):", round(result["before_mean_vv_db"], 3))
print("After mean VV (dB):", round(result["after_mean_vv_db"], 3))
print("Mean VV difference (dB):", round(result["mean_vv_difference_db"], 3))
print("Otsu threshold (dB):", round(result["otsu_threshold_db"], 3))
print()
print("New water area km2:", round(result["new_water_area_km2"], 4))
print("Valid area km2:", round(result["valid_area_km2"], 4))
print("New water % of valid area:", round(result["new_water_percent_of_valid_area"], 2))
print()
print("Warnings:")
for warning in result["warnings"]:
    print(" -", warning)
print()
print(f"Time: {elapsed:.1f} seconds")