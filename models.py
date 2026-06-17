from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

class FlightState(Enum):
    """The strict lifecycle states of an aircraft process."""
    
    AIRSPACE = auto()         # En route in the sky
    HOLDING = auto()          # In a holding pattern loop
    LANDING = auto()          # Touching down on the inbound runway
    TAXI_TO_GATE = auto()     # Navigating taxiways toward terminal
    GATE_DEPLANING = auto()   # UNLOADING arriving passengers (New)
    GATE_BOARDING = auto()    # LOADING departing passengers (New)
    TAXI_TO_RUNWAY = auto()   # Navigating taxiways toward departure runway
    TAKEOFF = auto()          # Blasting off into the sky


class AircraftType(Enum):
    LIGHT_PROP = 5       # 5-seater (e.g., Cessna, Piper) - Quick turnaround, low fuel requirements.
    REGIONAL_JET = 20    # 20-seater (e.g., Twin Otter, Jetstream) - Fast commuter hops.
    NARROW_BODY = 100    # 100-seater (e.g., Boeing 717, Embraer 190) - Standard commercial workhorse.
    WIDE_BODY = 500      # 500-seater (e.g., Airbus A380, Boeing 747) - High bottleneck risk, massive fuel load.



@dataclass
class Flight:
    flight_id: str
    aircraft_type: AircraftType
    state: FlightState 
    
    # Spatial Navigation Tracker
    # Represented as string node identifiers (e.g., ["Node_A", "Node_B", "Gate_3"])
    assigned_route: List[str]
    current_node_index: int
    
    # # Fuel Constraints (Acts as a priority weight in the system scheduler)
    # fuel_remaining: int = 100  # Percentage or units remaining
    
    @property
    def current_location(self):
        if not self.assigned_route:
            return "UNKNOWN"
        
        return self.assigned_route[self.current_node_index]
    

    
    