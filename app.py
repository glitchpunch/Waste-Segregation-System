import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import random
import time
from collections import defaultdict

from segregation import Zone, WasteTruck, RuleBasedSegregationUnit, ReportGenerator 

def init_zones(default_n=6):
    zones = []
    for i in range(default_n):
        name = f"Zone-{i+1}"
        pop = random.randint(5000, 70000)
        area = round(random.uniform(2.0, 12.0), 2)
        inc = random.choice(["Low", "Middle", "High"])
        z = Zone(name=name, population=pop, area=area, income_level=inc)
        zones.append(z)
    return zones

def init_trucks(n_trucks=3):
    trucks = []
    for i in range(n_trucks):
        tid = f"T-{100+i}"
        t = WasteTruck(truck_id=tid, capacity_tons=10.0)
        trucks.append(t)
    return trucks

def run_simulation_step(sstate, step_fraction):
    """
    This function updates:
    - zones generate waste fraction
    - trucks pick up from assigned zones (or assigned automatically)
    - trucks unload to segregation unit and processed_summary is updated
    - total_collected updated
    """
    zones = sstate.zones
    trucks = sstate.trucks
    seg = sstate.seg_unit
    processed = sstate.processed_summary  
    total_col = sstate.total_collected

    for z in zones:
        z.set_waste_generation(random.randrange(6, 14, 1)/10)
        gen = z.simulate_step_generate() * step_fraction
        total_col += gen

    zone_list = [z for z in zones if z.daily_waste > 0.0]
    if not zone_list:
        sstate.total_collected = total_col
        return

    for i, t in enumerate(trucks):
        if t.zone_assigned is None:
            assign = zone_list[i % len(zone_list)]
            t.assign_zone(assign)

    for truck in trucks:
        zone = truck.zone_assigned
        if zone is None:
            continue  

        capacity_left = truck.capacity - truck.current_load
        if capacity_left <= 0:
            continue

        step_waste_kg = zone.simulate_step_generate()
        step_waste_tons = step_waste_kg / 1000.0

        load_amount = min(step_waste_tons, capacity_left)

        if load_amount <= 0:
            continue

        truck.load_waste(load_amount)

        truck.send_to_unit(seg.unit_id)

        mass_to_process_kg = load_amount * 1000.0  
        if hasattr(seg, "segregate_mass"):
            seg_result = seg.segregate_mass(mass_to_process_kg)

        else:
            parts = ["Organic", "Plastic", "Paper", "Glass", "Metal", "E-Waste", "Hazardous"]
            share = mass_to_process_kg / len(parts)
            seg_result = {p: round(share, 2) for p in parts}

        for waste_type, amount in seg_result.items():
            processed[waste_type] += amount

    sstate.processed_summary = processed
    sstate.total_collected = total_col

st.set_page_config(page_title="SmartCity Waste Simulation", layout="wide")
st.title("♻️ Smart City Waste Segregation — Simulation Dashboard")

st.sidebar.header("Simulation Controls")
n_zones = st.sidebar.slider("Number of Zones", 3, 12, 6)
n_trucks = st.sidebar.slider("Number of Trucks", 1, 8, 3)
step_fraction = st.sidebar.slider("Generation fraction per step (fraction of daily)", 0.05, 1.0, 0.1, 0.05)
step_delay = st.sidebar.slider("Step delay (seconds, when autoplay)", 0.0, 2.0, 0.5, 0.1)

if "zones" not in st.session_state or len(st.session_state.zones) != n_zones:
    print("reinit")
    st.session_state.zones = init_zones(n_zones)
if "trucks" not in st.session_state or len(st.session_state.trucks) != n_trucks:
    st.session_state.trucks = init_trucks(n_trucks)
if "seg_unit" not in st.session_state:
    st.session_state.seg_unit = RuleBasedSegregationUnit(69)
if "reportgen" not in st.session_state:
    st.session_state.reportgen = ReportGenerator()
if "processed_summary" not in st.session_state:
    st.session_state.processed_summary = defaultdict(float)
if "total_collected" not in st.session_state:
    st.session_state.total_collected = 0.0
if "autoplay" not in st.session_state:
    st.session_state.autoplay = False

col1, col2, col3, col4 = st.columns([1,1,1,1])
with col1:
    if st.button("Step ▶"):
        st.session_state.autoplay = False
        run_simulation_step(st.session_state, step_fraction)
with col2:
    if st.button("Auto ▶▶"):
        st.session_state.autoplay = True
with col3:
    if st.button("Pause ❚❚"):
        st.session_state.autoplay = False
with col4:
    if st.button("Reset ⟲"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("---")

left, right = st.columns([2, 3])

with left:
    st.subheader("City Zones")
    zones = st.session_state.zones

    if st.session_state.autoplay:
        run_simulation_step(st.session_state, step_fraction)
        time.sleep(step_delay)
        st.rerun()

    zone_rows = []
    for z in zones:
        zone_rows.append({
            "zone": z.name,
            "population": getattr(z, "population", "n/a"),
            "area_km2": getattr(z, "area", "n/a"),
            "income": getattr(z, "income_level", "n/a"),
            "daily_waste": getattr(z, "daily_waste", 0.0),
        })
    zdf = pd.DataFrame(zone_rows)
    st.table(zdf)

    st.markdown("**Zone Waste Heatmap (buffer kg)**")
    fig = px.bar(zdf, x="zone", y="daily_waste", color="daily_waste", labels={"daily_waste":"Daily Waste (kg)"})
    st.plotly_chart(fig, width='stretch')

with right:
    st.subheader("Trucks & Segregation")

    trucks = st.session_state.trucks
    t_rows = []
    for t in trucks:
        t_rows.append({
            "truck_id": t.truck_id,
            "capacity_kg": t.capacity,
            "current_load_kg": round(t.current_load,2),
            "assigned_zone": t.zone_assigned,
        })
        t.unload()
        t.zone_assigned = None
    tdf = pd.DataFrame(t_rows)
    st.table(tdf)

    st.markdown("**Segregation Composition (processed so far)**")
    processed = dict(st.session_state.processed_summary)
    if processed:
        keys = list(processed.keys())
        vals = [processed[k] for k in keys]
        fig2 = px.pie(names=keys, values=vals, title="Processed Waste Composition (kg)")
        st.plotly_chart(fig2, width='stretch')
    else:
        st.info("No processed waste yet. Run simulation steps to generate and process waste.")

st.markdown("---")
st.caption("Tip: set smaller generation fraction for finer-grained steps (e.g., 0.1 means 10% of daily generation per step).")