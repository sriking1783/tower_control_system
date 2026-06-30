from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

class FlightState(str, Enum):
    AIRSPACE = "AIRSPACE" # En route in the sky
    HOLDING = "HOLDING" # In a holding pattern loop
    LANDING = "LANDING" # Touching down on the inbound runway
    TAXI_TO_GATE = "TAXI_TO_GATE" # Navigating taxiways toward terminal
    GATE_DEPLANING = "GATE_DEPLANING" # UNLOADING arriving passengers (New)
    GATE_BOARDING = "GATE_BOARDING"  # LOADING departing passengers (New)
    TAXI_TO_RUNWAY = "TAXI_TO_RUNWAY" # Navigating taxiways toward departure runway
    TAKEOFF = "TAKEOFF" # Blasting off into the sky


class AircraftType(str, Enum):
    LIGHT_PROP = "LIGHT_PROP"
    REGIONAL_JET = "REGIONAL_JET"
    NARROW_BODY = "NARROW_BODY"
    WIDE_BODY = "WIDE_BODY"
    
AIRCRAFT_CAPACITY_MAP = {
    AircraftType.LIGHT_PROP: 5,
    AircraftType.REGIONAL_JET: 50,
    AircraftType.NARROW_BODY: 200,
    AircraftType.WIDE_BODY: 500,
}

class GlobalSimulationState:
    def __init__(self):
        # Tracks aircraft locations
        self.registry = {
            "Airspace_Alpha": [], "Gate_C4": [], "Gate_E1": [], 
            "Taxiway_Zulu": [], "Runway_09L": [], "Departure_Hub": []
        }
        self.active_flights = {}
        
        # NEW: Tracks how many passengers are sitting in the chairs at each gate lounge
        self.gate_passenger_pool = {
            "Gate_C4": 120,   # 120 passengers waiting at C4
            "Gate_E1": 15     # Only 15 passengers waiting at E1 (this one will stall!)
        }


class Flight(BaseModel):
    flight_id: str
    aircraft_type: AircraftType
    current_location: str
    state: FlightState = FlightState.AIRSPACE
    passengers_onboard: int = 0
    
    # You can compute max_capacity automatically on initialization
    max_capacity: int = 0

    def model_post_init(self, __context):
        # Automatically set capacity after the model initializes
        self.max_capacity = AIRCRAFT_CAPACITY_MAP[self.aircraft_type]


class ResourceType(Enum):
    PIPELINE = auto()  # Can hold multiple aircraft sequentially (taxiways)
    MONOLITHIC = auto() # Exclusive lock required (runways, gates)


class AirportNode:
    def __init__(self, name: str, max_capacity: int, resource_type: ResourceType):
        self.name = name
        self.max_capacity = max_capacity
        self.resource_type = resource_type
        self.destinations = []
        self.supports_fallback_queuing = False # Gates allow planes to stack up behind them
        
    def add_connection(self, target_node: 'AirportNode'):
        """Adds a valid one-way movement path from this node to another."""
        if target_node not in self.destinations:
            self.destinations.append(target_node)
    
    def calculate_routing_score(self, live_registry: Dict[str, List[str]]) -> float:
        """
        Base heuristic: Lower score is better. 
        If full, return infinity to block routing.
        """
        current_occupancy = len(live_registry[self.name])
        if current_occupancy >= self.max_capacity and self.resource_type == ResourceType.MONOLITHIC:
            return float("inf")
        
        return float(current_occupancy)
    
    def get_fallback_priority(self) -> float:
        """Higher return value means higher priority when queuing in gridlock."""
        return 0.0

    def __repr__(self):
        return f"<Node: {self.name}>"

class Gate(AirportNode):
    # This attribute ONLY exists on Gates!
    def __init__(self, name: str, max_capacity: int, resource_type: ResourceType, passenger_count: int):
        self.name = name
        self.max_capacity = max_capacity
        self.resource_type = resource_type
        self.destinations = []
        self.passenger_count = passenger_count
        self.supports_fallback_queuing = True # Gates allow planes to stack up behind them
        
    
    def calculate_routing_score(self, live_registry: Dict[str, List[str]]) -> float:
        """
        Gate Override: Considers both plane occupancy and passenger demand.
        """
        current_occupancy = len(live_registry[self.name])
        if current_occupancy >= self.max_capacity:
            return float("inf")
        if self.passenger_count == 0:
            return float("inf")
        
        return float(current_occupancy) - (self.passenger_count * 0.1)
    
    def get_fallback_priority(self) -> float:
        # Gates prioritize their fallback queue by passenger bottleneck size
        return float(self.passenger_count)

@dataclass
class Runway(AirportNode):
    # You can add Runway-specific properties here later (like wind directions, length, etc.)
    pass 


# Added to models.py
class AirportNetwork:
    def __init__(self, nodes: Dict[str, AirportNode] = None):
        if nodes is not None:
            # If we pass a custom graph (like in tests), use it!
            self.nodes = nodes
        else:
            self.nodes: Dict[str, AirportNode] = {
                "Airspace_Alpha": AirportNode(name="Airspace_Alpha", resource_type=ResourceType.PIPELINE, max_capacity=999),
                "Runway_09R":     AirportNode(name="Runway_09R",     resource_type=ResourceType.MONOLITHIC, max_capacity=1),
                "Gate_C4":        Gate(name="Gate_C4",        resource_type=ResourceType.MONOLITHIC, max_capacity=1, passenger_count=250),
                "Gate_E1":        Gate(name="Gate_E1",        resource_type=ResourceType.MONOLITHIC, max_capacity=1, passenger_count=200),
                "Taxiway_Zulu":   AirportNode(name="Taxiway_Zulu",   resource_type=ResourceType.PIPELINE, max_capacity=3),
                "Runway_09L":     AirportNode(name="Runway_09L",     resource_type=ResourceType.MONOLITHIC, max_capacity=1),
                "Departure_Hub":  AirportNode(name="Departure_Hub",  resource_type=ResourceType.PIPELINE, max_capacity=999)
            }
            
            # Wire the Directed Graph Connections
            self.nodes["Airspace_Alpha"].add_connection(self.nodes["Runway_09R"])
            self.nodes["Runway_09R"].add_connection(self.nodes["Gate_C4"])
            self.nodes["Runway_09R"].add_connection(self.nodes["Gate_E1"])
            self.nodes["Gate_C4"].add_connection(self.nodes["Taxiway_Zulu"])
            self.nodes["Gate_E1"].add_connection(self.nodes["Taxiway_Zulu"])
            self.nodes["Taxiway_Zulu"].add_connection(self.nodes["Runway_09L"])
            self.nodes["Runway_09L"].add_connection(self.nodes["Departure_Hub"])
        
    

    
    