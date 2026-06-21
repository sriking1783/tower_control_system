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
    LIGHT_PROP = auto()
    REGIONAL_JET = auto()
    NARROW_BODY = auto()
    WIDE_BODY = auto()
    



class Flight:
    def __init__(self, flight_id: str, aircraft_type: AircraftType, initial_location: str):
        self.flight_id = flight_id
        self.aircraft_type = aircraft_type
        self.state = FlightState.AIRSPACE
        
        # Track position by the current node's string identifier key
        self.current_location: str = initial_location 


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
    def __init__(self, nodes: Dict[str, AirportNode] = None):
        if nodes is not None:
            # If we pass a custom graph (like in tests), use it!
            self.nodes = nodes
        else:
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
        
    

    
    