from segregation import *

zone1 = Zone("Sector 12", 50000, 6.5, "Middle Income")

zone1.set_waste_generation(per_person_kg=0.6)

zone1.set_waste_composition({
    "Organic": 50,
    "Plastic": 20,
    "Paper": 15,
    "Metal": 10,
    "E-Waste": 5
})

truck1 = WasteTruck(truck_id="T-101")

truck1.assign_zone(zone1)
truck1.load_waste(5)
truck1.send_to_unit("Composting Plant")
truck1.unload()

# # ---------------------------
# # RUNNING THE ANIMATION
# # ---------------------------

# zone1 = Zone("Sector 12", 50000, 6.5, "Middle Income")

# zone1.set_waste_generation(per_person_kg=0.6)

# zone1.set_waste_composition({
#     "Organic": 50,
#     "Plastic": 20,
#     "Paper": 15,
#     "Metal": 10,
#     "E-Waste": 5
# })

# zone1.display = lambda: None  # (Remove display print for animation cell)

# zone1.animate_waste_breakdown()

sample_items = []
names = [
    "banana_peel.jpg", "plastic_bottle.png", "newspaper.jpeg", "glass_jar.jpg",
    "tin_can.png", "old_phone.png", "paint_container.jpg", "food_waste.png",
    "wrapper.jpeg", "metal_scrap.jpg", "fruit_leftovers.jpeg", "circuit_board.png",
    "battery.png", "plastic_bag.jpeg", "broken_glass.png", "cardboard.jpeg",
    "mixed_food.jpeg", "iron_piece.jpg", "newspaper2.jpeg", "kitchen_waste.jpeg"
]

for i in range(20):
    w = round(random.uniform(0.1, 1.2), 2)  # random weight 0.1–1.2 kg
    sample_items.append(WasteItem(item_id=f"Item-{i+1}", weight_kg=w, image_path=names[i]))

unit = RuleBasedSegregationUnit("SegUnit-1")
output = unit.segregate(sample_items)

print("\n=== SEGREGATION OUTPUT ===")
for category, items in output.items():
    total_w = round(sum(it.weight_kg for it in items), 2)
    print(f"\n{category}  ->  {total_w} kg")
    for it in items:
        print("   ", it)


DEFAULT_RECYCLING_SAVINGS_PER_KG = {
    "Plastic": 0.75,    # kg CO2e saved per kg plastic recycled (approx)
    "Paper": 1.20,      # paper recycling saves more due to pulp saving
    "Glass": 0.25,
    "Metal": 2.50,
    "E-Waste": 1.50,
    "Organic": 0.15,    # composting avoids some emissions vs landfilling
    "Hazardous": 0.0
}

# Emission factor for waste *if left in landfill* (kg CO2e per kg). This is the avoided:
# when you divert 1 kg from landfill you avoid `LANDFILL_EMISSION_PER_KG` of CO2e (methane, transport, etc.)
# Default is conservative; replace with locally-sourced factor if you have it.
DEFAULT_LANDFILL_EMISSION_PER_KG = 0.6

# Energy recovery estimates (kWh recovered per kg) for certain treatments (optional)
DEFAULT_ENERGY_RECOVERY_PER_KG = {
    "Organic_biogas": 0.3,   # kWh per kg organic when converted to biogas (example)
    "Incineration": 0.5      # kWh per kg when incinerated with energy recovery (example)
}

# Sample processed summary (kg) from segregation unit(s)
processed_summary_example = {
    "Organic": 1250.0,
    "Plastic": 720.5,
    "Paper": 410.0,
    "Glass": 210.0,
    "Metal": 150.0,
    "E-Waste": 35.0,
    "Hazardous": 10.0
}

total_collected_example = 3000.0   # kg of mixed waste collected citywide that day
incinerated_example = 80.0         # kg sent to incineration (energy recovery)

rg = ReportGenerator()  # use default coefficients
report = rg.generate_report(processed_summary_example, total_collected_example, incinerated_example, show_plots=True)

print("\n=== NUMERIC KPI REPORT ===")
for k, v in report.items():
    print(f"{k:25s} : {v}")
