from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Dict
from dataclasses import dataclass, field

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
    LIGHT_PROP = auto()
    REGIONAL_JET = auto()
    NARROW_BODY = auto()
    WIDE_BODY = auto()
    
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


class Flight:
    def __init__(self, flight_id: str, aircraft_type: AircraftType, initial_location: str):
        self.flight_id = flight_id
        self.aircraft_type = aircraft_type
        self.state = FlightState.AIRSPACE
        
        # Track position by the current node's string identifier key
        self.current_location: str = initial_location 
        self.max_capacity = AIRCRAFT_CAPACITY_MAP[aircraft_type]
        self.passengers_onboard = 0


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
                "Airspace_Alpha": AirportNode("Airspace_Alpha", ResourceType.PIPELINE, 999),
                "Runway_09R":     AirportNode("Runway_09R",     ResourceType.MONOLITHIC, 1),
                "Gate_C4":        Gate(name="Gate_C4",        resource_type=ResourceType.MONOLITHIC, max_capacity=1, passenger_count=250),
                "Gate_E1":        Gate(name="Gate_E1",        resource_type=ResourceType.MONOLITHIC, max_capacity=1, passenger_count=200),
                "Taxiway_Zulu":   AirportNode("Taxiway_Zulu",   ResourceType.PIPELINE, 3),
                "Runway_09L":     AirportNode("Runway_09L",     ResourceType.MONOLITHIC, 1),
                "Departure_Hub":  AirportNode("Departure_Hub",  ResourceType.PIPELINE, 999)
            }
            
            # Wire the Directed Graph Connections
            self.nodes["Airspace_Alpha"].add_connection(self.nodes["Runway_09R"])
            self.nodes["Runway_09R"].add_connection(self.nodes["Gate_C4"])
            self.nodes["Runway_09R"].add_connection(self.nodes["Gate_E1"])
            self.nodes["Gate_C4"].add_connection(self.nodes["Taxiway_Zulu"])
            self.nodes["Gate_E1"].add_connection(self.nodes["Taxiway_Zulu"])
            self.nodes["Taxiway_Zulu"].add_connection(self.nodes["Runway_09L"])
            self.nodes["Runway_09L"].add_connection(self.nodes["Departure_Hub"])
        
    

    
    