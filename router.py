from typing import List, Dict, Optional
from models import AirportNetwork, AirportNode, Flight, ResourceType, Gate

class Router:
    @staticmethod
    def get_valid_next_options(network: AirportNetwork, current_location: str) -> List[AirportNode]:
        if current_location in network.nodes:
            return network.nodes[current_location].destinations
        
        return []
    
    
    @staticmethod 
    def select_optimal_next_node(flight: Flight, options: List[AirportNode], live_registry: Dict[str, List[str]]) -> Optional[str]:
        """
        Applies load-balancing operational logic to select the most efficient 
        next node from an array of options.
        """
        if not options:
            raise ValueError(f"Aircraft {flight.flight_id} has hit a dead-end at {flight.current_location}!")
        
        if len(options) == 1:
            return options[0].name
        
        # Core Balancing Decision Matrix (e.g., branching out at Runway_09R to choose a gate)
        best_node = None
        lowest_load = float("inf")
        highest_passenger_gate = None
        max_passengers = -1
        
        for node in options:
            current_occupancy = len(live_registry[node.name])
            max_capacity = node.max_capacity
            if isinstance(node, Gate):
                if node.passenger_count > max_passengers:
                    max_passengers = node.passenger_count
                    highest_passenger_gate = node
 
            if current_occupancy >= max_capacity and node.resource_type == ResourceType.MONOLITHIC:
                continue
                
            # Load balancing heuristic: Pick the gate with the absolute fewest planes
            if current_occupancy < lowest_load:
                lowest_load = current_occupancy
                best_node = node
        
        # Rule A: If we found a valid, non-full node, route to it immediately!
        if best_node:
            return best_node.name
            
        # Rule B: Fallback Strategy - If ALL nodes are full, queue behind the gate clearing out the most people
        if highest_passenger_gate:
            return highest_passenger_gate.name
            
        # Rule C: If all choices are full and none are gates (e.g. all are full runways), activate brakes
        return None
        
        
        
    