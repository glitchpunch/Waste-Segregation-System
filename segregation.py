import matplotlib.pyplot as plt
import matplotlib.animation as animation
from IPython.display import HTML
import random
from collections import defaultdict
from typing import Dict, Optional
import matplotlib.pyplot as plt
import csv
import json
import sqlite3
from datetime import datetime
import os
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt


class WasteTruck:

    def __init__(self, truck_id, capacity_tons=10):
        self.truck_id = truck_id
        self.capacity = capacity_tons  
        self.zone_assigned = None
        self.destination_unit = None
        self.current_load = 0

    def assign_zone(self, zone):
        self.zone_assigned = zone

    def load_waste(self, amount):
        if self.current_load + amount > self.capacity:
            print(f"Truck {self.truck_id}: Overload! Cannot load {amount} tons.")
        else:
            self.current_load += amount
            print(f"Truck {self.truck_id} loaded {amount} tons.")

    def send_to_unit(self, unit):
        self.destination_unit = unit
        print(f"Truck {self.truck_id} is going to {unit} unit.")

    def unload(self):
        print(f"Truck {self.truck_id} unloaded {self.current_load} tons at {self.destination_unit}.")
        self.current_load = 0

class Zone:
    def __init__(self, name, population, area, income_level):
        self.name = name
        self.population = population
        self.area = area
        self.income_level = income_level
        self.daily_waste = 0
        self.composition_dict = {}
    
    def __repr__(self):
        return self.name

    def set_waste_generation(self, random_factor=1.0, per_person_kg=0.55):
        self.daily_waste = round(self.population * per_person_kg * random_factor, 2)
        return self.daily_waste

    def set_waste_composition(self, composition_dict):
        if sum(composition_dict.values()) != 100:
            raise ValueError("Composition percentages must total 100.")
        self.composition_dict = composition_dict

    def get_waste_breakdown(self):
        breakdown = {}
        for wtype, percent in self.composition_dict.items():
            breakdown[wtype] = round((percent / 100) * self.daily_waste, 2)
        return breakdown

    def plot_waste_breakdown(self):
        breakdown = self.get_waste_breakdown()

        waste_types = list(breakdown.keys())
        quantities = list(breakdown.values())

        plt.figure(figsize=(8, 5))
        plt.title(f"Waste Breakdown for {self.name}")
        plt.xlabel("Waste Types")
        plt.ylabel("Waste (kg)")
        plt.tight_layout()

        waste_types = list(breakdown.keys())
        quantities = list(breakdown.values())

        plt.pie(quantities, labels=waste_types, autopct='%1.1f%%')

    def display(self):
        print(f"\n---Zone Report : {self.name}---")
        print(f"Population     : {self.population}")
        print(f"Area           : {self.area} sq.km")
        print(f"Income Level   : {self.income_level}")
        print(f"Daily Waste    : {self.daily_waste} kg")

        if self.composition_dict:
            print("\nWaste Breakdown:")
            breakdown = self.get_waste_breakdown()
            for w, qty in breakdown.items():
                print(f"  {w}: {qty} kg")

        print("-------------------------------------\n")

    def animate_waste_breakdown(self):
        breakdown = self.get_waste_breakdown()
        waste_types = list(breakdown.keys())
        values = list(breakdown.values())

        fig, ax = plt.subplots(figsize=(8, 5))

        bars = ax.bar(waste_types, [0]*len(values))
        ax.set_ylim(0, max(values) + 20)
        ax.set_title(f"Waste Breakdown Animation - {self.name}")
        ax.set_xlabel("Waste Types")
        ax.set_ylabel("Waste (kg)")

        def update(frame):
            for bar, height in zip(bars, values):
                bar.set_height(height * (frame / 100))
            return bars

        ani = animation.FuncAnimation(
            fig, update, frames=100, interval=50, blit=False
        )

        plt.close(fig)
        return HTML(ani.to_jshtml())
 
    def simulate_step_generate(self, steps_per_day=24):
        """
        Simulates waste generation for one step out of 'steps_per_day'.
        Example: If steps_per_day = 24 → generates hourly waste.
        """

        if self.daily_waste == 0:
            raise ValueError("Daily waste not set. Call set_waste_generation() first.")

        step_waste = round(self.daily_waste / steps_per_day, 2)

        breakdown = {}
        for wtype, percent in self.get_waste_breakdown().items():
            breakdown[wtype] = round(step_waste * (percent / 100), 2)

        return step_waste

class WasteItem:
    def __init__(self, item_id, weight_kg, image_path=None):
        self.item_id = item_id
        self.weight_kg = weight_kg
        self.image_path = image_path
        self.predicted_type = None  

    def __repr__(self):
        return f"{self.item_id} ({self.weight_kg} kg → {self.predicted_type})"

class SegregationUnit:
    def __init__(self, unit_id, capacity_kg=None, random_seed=42):
        self.unit_id = unit_id
        self.capacity_kg = capacity_kg
        random.seed(random_seed)

    def segregate(self, items):
        raise NotImplementedError("Use RuleBasedSegregationUnit")

class RuleBasedSegregationUnit(SegregationUnit):

    DEFAULT_TYPES = ["Organic", "Plastic", "Paper", "Glass", "Metal", "E-Waste", "Hazardous"]

    def __init__(self, unit_id, capacity_kg=None, rules=None, random_seed=42):
        super().__init__(unit_id, capacity_kg, random_seed)

        self.rules = rules or {
            "Organic": 0.40,
            "Plastic": 0.22,
            "Paper": 0.14,
            "Glass": 0.08,
            "Metal": 0.07,
            "E-Waste": 0.05,
            "Hazardous": 0.04
        }

        total = sum(self.rules.values())
        self.prob = {t: p / total for t, p in self.rules.items()}

        cum = 0
        self.dist = []
        for t, p in self.prob.items():
            cum += p
            self.dist.append((cum, t))

    def _keyword_hint(self, image_path):
        if not image_path:
            return None

        fname = image_path.lower()

        hints = {
            "Organic": ["banana", "food", "fruit", "veg", "peel"],
            "Plastic": ["plastic", "bottle", "wrapper"],
            "Paper": ["paper", "cardboard", "news"],
            "Glass": ["glass", "jar"],
            "Metal": ["metal", "tin", "can"],
            "E-Waste": ["phone", "pcb", "circuit", "battery"],
            "Hazardous": ["chem", "acid", "paint"]
        }

        for label, keys in hints.items():
            if any(k in fname for k in keys):
                return label
        return None

    def _sample_type(self):
        r = random.random()
        for cum, t in self.dist:
            if r <= cum:
                return t
        return "Organic"

    def segregate(self, items):
        result = defaultdict(list)

        total_weight = sum(it.weight_kg for it in items)

        for it in items:
            base_class = self._sample_type()            
            hint_class = self._keyword_hint(it.image_path)   

            if hint_class and random.random() < 0.20:
                final_type = hint_class
            else:
                final_type = base_class

            it.predicted_type = final_type
            result[final_type].append(it)

        if self.capacity_kg and total_weight > self.capacity_kg:
            overflow = []
            accepted = defaultdict(list)
            running = 0

            for t, lst in result.items():
                for it in lst:
                    if running + it.weight_kg <= self.capacity_kg:
                        accepted[t].append(it)
                        running += it.weight_kg
                    else:
                        overflow.append(it)

            if overflow:
                accepted["OVERFLOW"] = overflow

            return dict(accepted)

        return dict(result)

DEFAULT_RECYCLING_SAVINGS_PER_KG = {
    "Plastic": 0.75,    
    "Paper": 1.20,    
    "Glass": 0.25,
    "Metal": 2.50,
    "E-Waste": 1.50,
    "Organic": 0.15,  
    "Hazardous": 0.0
}

DEFAULT_LANDFILL_EMISSION_PER_KG = 0.6

DEFAULT_ENERGY_RECOVERY_PER_KG = {
    "Organic_biogas": 0.3,   # kWh per kg 
    "Incineration": 0.5      # kWh per kg 
}

class ReportGenerator:
    def __init__(
        self,
        recycling_savings_per_kg: Optional[Dict[str, float]] = None,
        landfill_emission_per_kg: Optional[float] = None,
        energy_recovery_per_kg: Optional[Dict[str, float]] = None
    ):
        self.recycling_savings_per_kg = recycling_savings_per_kg or DEFAULT_RECYCLING_SAVINGS_PER_KG
        self.landfill_emission_per_kg = landfill_emission_per_kg or DEFAULT_LANDFILL_EMISSION_PER_KG
        self.energy_recovery_per_kg = energy_recovery_per_kg or DEFAULT_ENERGY_RECOVERY_PER_KG

    def calculate_recycling_rate(self, processed_summary: Dict[str, float], total_collected_kg: float) -> float:
        """
        Recycling rate = (mass recycled) / (total collected) * 100
        We treat categories Plastic, Paper, Glass, Metal, E-Waste as 'recycled' by default.
        Organic is counted as 'composted' (not traditional recycling) so not included in recycled mass here.
        """
        if total_collected_kg <= 0:
            return 0.0

        recycled_keys = ["Plastic", "Paper", "Glass", "Metal", "E-Waste"]
        recycled_mass = _safe_sum(processed_summary, recycled_keys)
        rate = (recycled_mass / total_collected_kg) * 100.0
        return round(rate, 2)

    def calculate_landfill_reduction(self, processed_summary: Dict[str, float], total_collected_kg: float, incinerated_kg: float = 0.0) -> float:
        """
        Landfill reduction = (diverted mass) / total_collected * 100
        Diverged mass = recycled + composted + incinerated (i.e., anything not sent to landfill)
        """
        if total_collected_kg <= 0:
            return 0.0

        diverted_keys = ["Plastic", "Paper", "Glass", "Metal", "E-Waste", "Organic"]
        diverted_mass = _safe_sum(processed_summary, diverted_keys) + float(incinerated_kg)
        rate = (diverted_mass / total_collected_kg) * 100.0
        return round(rate, 2)

    def calculate_co2_saved(
        self,
        processed_summary: Dict[str, float],
        total_collected_kg: float,
        incinerated_kg: float = 0.0
    ) -> float:
        """
        CO2 saved estimation = (sum over categories: mass * recycling_saving_per_kg)
                                + avoided landfill emissions for diverted mass
        - recycling_savings_per_kg: benefit per kg for recycling/composting vs virgin production
        - landfill_emission_per_kg: emissions saved per kg diverted from landfill
        """
        # Savings from recycling/composting/ewaste processing
        saving_from_processing = 0.0
        for mat, mass in processed_summary.items():
            coef = self.recycling_savings_per_kg.get(mat, 0.0)
            saving_from_processing += coef * mass

        # Avoided landfill emissions for diverted mass (recycled+composted+incinerated)
        diverted_keys = ["Plastic", "Paper", "Glass", "Metal", "E-Waste", "Organic"]
        diverted_mass = _safe_sum(processed_summary, diverted_keys) + float(incinerated_kg)
        avoided_landfill = diverted_mass * self.landfill_emission_per_kg

        total_saved = saving_from_processing + avoided_landfill

        # rounding to 2 decimals
        return round(total_saved, 2)

    # energy recovered
    def calculate_energy_recovered(
        self,
        processed_summary: Dict[str, float],
        incinerated_kg: float = 0.0
    ) -> float:
        """
        Estimate kWh energy recovered:
        - from organic -> biogas (if applicable)
        - from incineration (if incinerated_kg provided)
        Returns estimated kWh recovered (rounded)
        """
        organic_kg = float(processed_summary.get("Organic", 0.0))
        biogas_kwh = organic_kg * self.energy_recovery_per_kg.get("Organic_biogas", 0.0)
        incineration_kwh = float(incinerated_kg) * self.energy_recovery_per_kg.get("Incineration", 0.0)
        total_kwh = biogas_kwh + incineration_kwh
        return round(total_kwh, 2)

    def generate_report(
        self,
        processed_summary: Dict[str, float],
        total_collected_kg: float,
        incinerated_kg: float = 0.0,
        show_plots: bool = True
    ) -> Dict[str, float]:
        """
        Generates KPIs and (optionally) plots to visualize results.
        Returns a dictionary with numeric KPIs.
        """

        total_processed = sum(processed_summary.values())
        unaccounted = max(0.0, total_collected_kg - total_processed)

        recycling_rate = self.calculate_recycling_rate(processed_summary, total_collected_kg)
        landfill_reduction = self.calculate_landfill_reduction(processed_summary, total_collected_kg, incinerated_kg)
        co2_saved_kg = self.calculate_co2_saved(processed_summary, total_collected_kg, incinerated_kg)
        energy_kwh = self.calculate_energy_recovered(processed_summary, incinerated_kg)

        report = {
            "total_collected_kg": round(total_collected_kg, 2),
            "total_processed_kg": round(total_processed, 2),
            "unaccounted_kg": round(unaccounted, 2),
            "recycling_rate_percent": recycling_rate,
            "landfill_reduction_percent": landfill_reduction,
            "co2_saved_kg": co2_saved_kg,
            "energy_recovered_kwh": energy_kwh
        }

        if show_plots:
            self._plot_material_pie(processed_summary)
            self._plot_kpi_bars(report)

        return report

    def _plot_material_pie(self, processed_summary: Dict[str, float]):
        labels = []
        sizes = []
        for k, v in processed_summary.items():
            if v <= 0:
                continue
            labels.append(k)
            sizes.append(v)

        if not sizes:
            print("No processed material data to plot.")
            return

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title("Processed Waste Composition (kg)")
        ax.axis("equal")
        plt.show()

    def _plot_kpi_bars(self, report_dict: Dict[str, float]):
        labels = ["Recycling Rate (%)", "Landfill Reduction (%)", "CO2 Saved (kg)", "Energy Recovered (kWh)"]
        values = [
            report_dict.get("recycling_rate_percent", 0.0),
            report_dict.get("landfill_reduction_percent", 0.0),
            report_dict.get("co2_saved_kg", 0.0),
            report_dict.get("energy_recovered_kwh", 0.0)
        ]

        fig, ax = plt.subplots(figsize=(8, 4))
        bars = ax.bar(labels, values)
        ax.set_title("Key KPIs")
        ax.set_ylabel("Value")
        ax.set_xticklabels(labels, rotation=15, ha="right")

        # Add numeric labels above bars
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h:.2f}", xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points", ha="center", va="bottom")

        plt.tight_layout()
        plt.show()

class DataManager:
    def __init__(self, db_name="waste_system.db"):
        self.db_name = db_name
        self._create_tables()

    def _create_tables(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_name TEXT,
            population INTEGER,
            daily_waste REAL,
            composition_json TEXT,
            timestamp TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS truck_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            truck_id TEXT,
            source_zone TEXT,
            destination TEXT,
            load REAL,
            timestamp TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS segregation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_name TEXT,
            plastic REAL,
            organic REAL,
            metal REAL,
            glass REAL,
            paper REAL,
            textile REAL,
            timestamp TEXT
        )
        """)

        conn.commit()
        conn.close()

    def save_zone_data(self, zone_obj):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save to SQLite
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO zones (zone_name, population, daily_waste, composition_json, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            zone_obj.name,
            zone_obj.population,
            zone_obj.daily_waste,
            json.dumps(zone_obj.composition),
            timestamp
        ))

        conn.commit()
        conn.close()

        # Save to JSON
        with open("zone_data.json", "a") as f:
            json.dump({
                "zone_name": zone_obj.name,
                "population": zone_obj.population,
                "daily_waste": zone_obj.daily_waste,
                "composition": zone_obj.composition,
                "timestamp": timestamp
            }, f)
            f.write("\n")

        # Save to CSV
        file_exists = os.path.isfile("zone_data.csv")
        with open("zone_data.csv", "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["zone_name", "population", "daily_waste", "composition", "timestamp"])
            writer.writerow([zone_obj.name, zone_obj.population, zone_obj.daily_waste,
                             json.dumps(zone_obj.composition), timestamp])


    #  SAVE TRUCK LOGS 
    def save_truck_logs(self, truck_id, source, destination, load):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # SQLite
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO truck_logs (truck_id, source_zone, destination, load, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (truck_id, source, destination, load, timestamp))
        conn.commit()
        conn.close()

        # JSON
        with open("truck_logs.json", "a") as f:
            json.dump({
                "truck_id": truck_id,
                "source_zone": source,
                "destination": destination,
                "load": load,
                "timestamp": timestamp
            }, f)
            f.write("\n")

        # CSV
        file_exists = os.path.isfile("truck_logs.csv")
        with open("truck_logs.csv", "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["truck_id", "source_zone", "destination", "load", "timestamp"])
            writer.writerow([truck_id, source, destination, load, timestamp])

    # 4. SAVE SEGREGATION RESULTS 
    def save_segregation_results(self, unit_name, result_dict):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # SQLite
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO segregation (unit_name, plastic, organic, metal, glass, paper, textile, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            unit_name,
            result_dict.get("plastic", 0),
            result_dict.get("organic", 0),
            result_dict.get("metal", 0),
            result_dict.get("glass", 0),
            result_dict.get("paper", 0),
            result_dict.get("textile", 0),
            timestamp
        ))

        conn.commit()
        conn.close()

        # JSON
        with open("segregation_results.json", "a") as f:
            json.dump(result_dict, f)
            f.write("\n")

        # CSV
        file_exists = os.path.isfile("segregation_results.csv")
        with open("segregation_results.csv", "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(
                    ["unit_name", "plastic", "organic", "metal", "glass", "paper", "textile", "timestamp"])
            writer.writerow([
                unit_name,
                result_dict.get("plastic", 0),
                result_dict.get("organic", 0),
                result_dict.get("metal", 0),
                result_dict.get("glass", 0),
                result_dict.get("paper", 0),
                result_dict.get("textile", 0),
                timestamp
            ])

    # 5. LOAD DATA (from SQLite)
    def load_data(self, table_name):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        data = cur.fetchall()
        conn.close()
        return data

class Predictor:
    def __init__(self, historical_data):
        """
        historical_data: list of daily total waste values
        Example: [120, 130, 128, 140, 150, 160]
        """
        self.historical_data = np.array(historical_data)
        self.model = LinearRegression()

    def train(self):
        """Train linear regression on historical waste"""
        X = np.arange(len(self.historical_data)).reshape(-1, 1)
        y = self.historical_data
        self.model.fit(X, y)

    def predict_next_days(self, days=30):
        """Predict waste for next N days"""
        future_x = np.arange(len(self.historical_data),
                             len(self.historical_data) + days).reshape(-1, 1)
        predictions = self.model.predict(future_x)
        return predictions

    def plot_forecast(self, prediction_days=30):
        """Shows a forecasting graph"""
        self.train()
        future = self.predict_next_days(prediction_days)

        plt.figure(figsize=(9, 5))
        plt.plot(self.historical_data, label="Historical Data")
        plt.plot(
            np.arange(len(self.historical_data),
                      len(self.historical_data) + prediction_days),
            future,
            label="Forecast"
        )
        plt.xlabel("Days")
        plt.ylabel("Waste Generated (kg)")
        plt.title("Waste Forecasting")
        plt.legend()
        plt.grid(True)
        plt.show()

class Optimizer:
    def __init__(self, segregation_capacity, truck_capacity, plant_capacity):
        """
        segregation_capacity: kg/day system can handle
        truck_capacity: total kg/day trucks can move
        plant_capacity: kg/day recycling plants can handle
        """
        self.segregation_capacity = segregation_capacity
        self.truck_capacity = truck_capacity
        self.plant_capacity = plant_capacity

    def analyze(self, predicted_waste):
        """Returns recommendations based on predicted data"""
        avg_future_waste = np.mean(predicted_waste)

        suggestions = []

        # --- Check Overload Conditions ---
        if avg_future_waste > self.segregation_capacity:
            suggestions.append(
                f"⚠ Add 1 new Segregation Unit (Overload: {avg_future_waste:.2f} kg/day > {self.segregation_capacity})"
            )

        if avg_future_waste > self.truck_capacity:
            suggestions.append(
                f"⚠ Add 2 new Waste Trucks (Overload: {avg_future_waste:.2f} kg/day > {self.truck_capacity})"
            )

        if avg_future_waste > self.plant_capacity:
            suggestions.append(
                f"⚠ Expand Recycling Plants (Overload: {avg_future_waste:.2f} kg/day > {self.plant_capacity})"
            )

        if not suggestions:
            suggestions.append("✓ System capacity is sufficient for next month.")

        return suggestions


def _safe_sum(d: Dict[str, float], keys=None) -> float:
    if keys is None:
        return sum(d.values())
    return sum(d.get(k, 0.0) for k in keys)
