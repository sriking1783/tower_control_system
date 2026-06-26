# state.py
from typing import Dict, List
from models import Flight, AirportNetwork, FlightState, GlobalSimulationState

# Instantiate the Master Topology Graph ONCE
airport_network = AirportNetwork()

# Shared state track structures

NODE_STATE_MAP = {
    "Airspace_Alpha": FlightState.AIRSPACE,
    "Runway_09R":     FlightState.LANDING,
    "Gate_C4":        FlightState.GATE_DEPLANING,
    "Gate_E1":        FlightState.GATE_DEPLANING,
    "Taxiway_Zulu":   FlightState.TAXI_TO_RUNWAY,
    "Runway_09L":     FlightState.TAKEOFF,
    "Departure_Hub":  FlightState.TAKEOFF,
}

global_simulation_state = GlobalSimulationState()