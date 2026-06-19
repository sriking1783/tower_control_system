import asyncio
from typing import Dict, List, Optional
from models import Flight, FlightState
from engine import flight_generator_worker

# Shared state memory tracking all active flights in our sky/ground network
active_flights: Dict[str, Flight] = {}

STATE_MAP = {
    0: FlightState.AIRSPACE,
    1: FlightState.HOLDING,
    2: FlightState.LANDING,
    3: FlightState.TAXI_TO_GATE,
    4: FlightState.GATE_DEPLANING,
    5: FlightState.TAXI_TO_RUNWAY,
    6: FlightState.TAKEOFF
}

RESOURCE_CONFIGS = {
    "Airspace_Alpha": {"max_capacity": 999, "type": "PIPELINE"},
    "Holding_Pattern_North": {"max_capacity": 999, "type": "PIPELINE"},
    "Runway_09R": {"max_capacity": 1, "type": "MONOLITHIC"},
    "Taxiway_Kilo": {"max_capacity": 3, "type": "PIPELINE"},
    "Gate_C4": {"max_capacity": 1, "type": "MONOLITHIC"},
    "Taxiway_Zulu": {"max_capacity": 3, "type": "PIPELINE"},
    "Runway_09L": {"max_capacity": 1, "type": "MONOLITHIC"},
    "Departure_Corridor": {"max_capacity": 999, "type": "PIPELINE"},
}

# The active global tracking registry containing lists of flight IDs currently in those nodes
registry: Dict[str, List[str]] = {node: [] for node in RESOURCE_CONFIGS}

async def acquire_spatial_resources(flight: Flight, current_idx: int, next_idx: int) -> bool:
    route = flight.assigned_route
    next_node = route[next_idx]
    
    # Verify if the immediate target node has open capacity
    if len(registry[next_node]) >= RESOURCE_CONFIGS[next_node]["max_capacity"]:
        return False
    
    # APPROACH B (Moving Bubble look-ahead): If entering a high-speed resource (Runway),
    # check if the segment *after* that is also clear to preserve deceleration/acceleration length.
    if RESOURCE_CONFIGS[next_node]["type"] == "MONOLITHIC" and (next_idx + 1) < len(route):
        lookahead_node = route[next_idx + 1]
        if len(registry[lookahead_node]) >= RESOURCE_CONFIGS[lookahead_node]["max_capacity"]:
            return False
    
    # All checks passed! Execute transaction bookings
    registry[next_node].append(flight.flight_id)
    return True



async def manage_flight_lifecycle(flight: Flight):
    """
    Simulates the physical movement and behavior of a single aircraft
    stepping linearly through its track route.
    """
    flight_id = flight.flight_id
    route = flight.assigned_route
    
    # Bootstrap entry: Pre-seed the initial spawn node ("Airspace_Alpha")
    registry[route[0]].append(flight_id)
    
    
    while flight.current_node_index < len(flight.assigned_route):
        current_node = flight.assigned_route[flight.current_node_index]
        next_node_index = flight.current_node_index + 1
        
        # Determine if we have another node to step onto
        if next_node_index < len(route):
            next_node = route[next_node_index]
            
            # Async Spin-Lock / Auto-Brake loop: Pause execution safely until path is acquired
            while not await acquire_spatial_resources(flight, flight.current_node_index, next_node_index):
                await asyncio.sleep(0.5) # Yield core back to event loop, wait 500ms, retry
            
            # Two-Phase Lock Step: We have booked the next node! Now we clear out of the previous one
            if flight_id in registry[current_node]:
                registry[current_node].remove(flight_id)
            
            # Physically advance index position
            flight.current_node_index = next_node_index
            current_node = next_node
        else:
            if flight_id in registry[current_node]:
                registry[current_node].remove(flight_id)
            break
        
        # State updates
        # 1. Update state classification based on track positioning
        if flight.current_node_index in STATE_MAP:
            # Only skip mapping if we are sitting at the Gate node (Index 4) 
            # so our custom Deplaning -> Boarding split can run uninterrupted
            if flight.state != FlightState.GATE_BOARDING:
                flight.state = STATE_MAP[flight.current_node_index]
        
        
        print(f"[{flight_id}] Status: {flight.state.name} | Location: {current_node}")
        
        # 2. Simulate node action overhead (Time spent consuming the sector resource)
        if flight.state == FlightState.GATE_DEPLANING:
            # Simulate passenger turnaround
            await asyncio.sleep(2.0)
            flight.state = FlightState.GATE_BOARDING
            print(f"[{flight_id}] Status: {flight.state.name} | Location: {current_node} (Turnaround complete)")
            await asyncio.sleep(2.0)
        else:
            # General transit time through basic airspace/taxi segments
            await asyncio.sleep(1.5)
        
    
    # 4. Cleanup flight upon leaving the final segment ("Departure_Corridor")
    if flight_id in active_flights:
        del active_flights[flight_id]
    
    print(f"[{flight_id}] Has cleared the departure corridor. Purged from memory. Active pool size: {len(active_flights)}")


async def engine_orchestrator(queue: asyncio.Queue):
    """
    Pulls raw entities off the streaming network ingestion queue and hands
    them off immediately to concurrent runtime processes.
    """
    while True:
        # Blocks until a new flight payload enters the shared ingestion queue
        new_flight: Flight = await queue.get()
        
        # Register flight to active memory tracking table
        active_flights[new_flight.flight_id] = new_flight
        
        # Fire-and-forget: Spin up a lightweight concurrent green-thread for this plane
        asyncio.create_task(manage_flight_lifecycle(new_flight))
        
        # Signal queue that processing initialization has completed successfully
        queue.task_done()
    

async def main():
    # Central communications queue connecting the spawner to the runtime orchestrator
    flight_ingestion_queue = asyncio.Queue()
    
    print("[SYSTEM] Booting Air Traffic Operations Control Engine Hub...")
    
    # Run the background generator and orchestrator side-by-side
    await asyncio.gather(
        flight_generator_worker(flight_ingestion_queue, spawn_rate_seconds=4.0),
        engine_orchestrator(flight_ingestion_queue)
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Air Traffic Control Engine safely shut down.")
        
        
        
        
        
            
            