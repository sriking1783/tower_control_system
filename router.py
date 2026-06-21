from typing import List, Dict, Optional
from models import AirportNetwork, AirportNode, Flight

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
        
        for node in options:
            current_occupancy = len(live_registry[node.name])
            max_capacity = node.max_capacity
            
            if current_occupancy >= max_capacity:
                continue
                
            # Load balancing heuristic: Pick the gate with the absolute fewest planes
            if current_occupancy < lowest_load:
                lowest_load = current_occupancy
                best_node = node
        
        # Fallback Strategy: If all forward gates/routes are entirely full, 
        # return None to trigger the plane's brake mechanism.
        return best_node.name if best_node else None
        
        
        
    