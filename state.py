# state.py
from typing import Dict, List
from models import Flight, AirportNetwork

# Instantiate the Master Topology Graph ONCE
airport_network = AirportNetwork()

# Shared state track structures
active_flights: Dict[str, Flight] = {}
registry: Dict[str, List[str]] = {node_name: [] for node_name in airport_network.nodes} # registry holds the information of airlines at places like Runway, Gate, etc 