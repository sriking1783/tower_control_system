from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Dict

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


class ResourceType(Enum):
    PIPELINE = auto()  # Can hold multiple aircraft sequentially (taxiways)
    MONOLITHIC = auto() # Exclusive lock required (runways, gates)

class AirportNode:
    def __init__(self, name: str, resource_type: ResourceType, max_capacity: int):
        self.name: str = name
        self.resource_type: ResourceType = resource_type
        self.max_capacity: int = max_capacity
        
        # Graph connections: Edges out of this node to other node objects
        self.destinations: List['AirportNode'] = []
        
    def add_connection(self, target_node: 'AirportNode'):
        """Adds a valid one-way movement path from this node to another."""
        if target_node not in self.destinations:
            self.destinations.append(target_node)

    def __repr__(self):
        return f"<Node: {self.name}>"


# Added to models.py
class AirportNetwork:
    def __init__(self):
        self.nodes: Dict[str, AirportNode] = {
            "Airspace_Alpha": AirportNode("Airspace_Alpha", ResourceType.PIPELINE, 999),
            "Runway_09R":     AirportNode("Runway_09R",     ResourceType.MONOLITHIC, 1),
            "Gate_C4":        AirportNode("Gate_C4",        ResourceType.MONOLITHIC, 1),
            "Gate_E1":        AirportNode("Gate_E1",        ResourceType.MONOLITHIC, 1),
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
        
    

    
    