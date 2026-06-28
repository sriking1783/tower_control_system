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
        fallback_options = []
        lowest_score = float("inf")
        
        for node in options:
            score = node.calculate_routing_score(live_registry)
            # Track full gates for fallback evaluation
            if score == float("inf") and node.supports_fallback_queuing:
                fallback_options.append(node)
                continue
            if score < lowest_score:
                lowest_score = score
                best_node = node
                
        # Rule A: Return clearest path
        if best_node and lowest_score != float("inf"):
            return best_node.name
            
        # Rule B: Fallback - If all options are packed, pick the gate with the highest passenger bottleneck
        if fallback_options:
            fallback_options.sort(key=lambda g: g.passenger_count, reverse=True)
            return fallback_options[0].name

        return None
        
        
        
    