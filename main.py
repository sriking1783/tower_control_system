import asyncio
from typing import Dict, List, Optional
from models import Flight, FlightState, AirportNetwork, ResourceType, AIRCRAFT_CAPACITY_MAP, GlobalSimulationState
from engine import flight_generator_worker
from router import Router
import state
import random

async def acquire_graph_resources(flight: Flight, target_node_name: str) -> bool:
    """
    Evaluates real-time node availability.
    Implements Approach B (Moving Bubble) for monolithic runway segments:
    Looks ahead at downstream destinations to prevent gridlock or high-speed collisions.
    """
    target_node = state.airport_network.nodes[target_node_name]
   
    # Rule 1: Verify immediate capacity limits
    if len(state.global_simulation_state.registry[target_node_name]) >= target_node.max_capacity:
        return False
    
    # Rule 2: Moving Bubble look-ahead safety buffer
    # If stepping onto a landing or takeoff runway, check if the paths exiting it are completely locked up
    if target_node.resource_type == ResourceType.MONOLITHIC and "Runway" in target_node_name:
        downstream_options = target_node.destinations
        downstream_runways = [
            opt for opt in downstream_options 
            if "Runway" in opt.name or opt.resource_type == ResourceType.MONOLITHIC
        ]
        # If all paths leading out of this runway are completely backed up to maximum capacity, 
        # deny permission to enter the runway block to prevent gridlock.
        if downstream_runways and all(len(state.global_simulation_state.registry[opt.name]) >= opt.max_capacity for opt in downstream_runways):
            return False
    
    state.global_simulation_state.registry[target_node_name].append(flight.flight_id)
    return True
        

async def passenger_loader_worker(boarding_rate_seconds: float = 0.2):
    """
    Background daemon that continuously monitors flights at gates 
    and streams passengers onto them until they reach max capacity.
    """
    print("[Passenger Loader] Worker engine started.")
    while True:
        active_flights = list(state.global_simulation_state.active_flights.values())
        for flight in active_flights:
            gate_name = flight.current_location
            if "Gate" in flight.current_location and flight.state == FlightState.GATE_BOARDING:
                available_at_gate = state.global_simulation_state.gate_passenger_pool.get(gate_name, 0)
                remaining_seats = flight.max_capacity - flight.passengers_onboard
                if remaining_seats > 0 and available_at_gate > 0:
                    # The absolute maximum we can board is bounded by the lounge population!
                    group_size = min(random.randint(5, 15), remaining_seats, available_at_gate)
                    
                    # Transaction: Move passengers from the lounge room onto the aircraft
                    state.global_simulation_state.gate_passenger_pool[gate_name] -= group_size
                    flight.passengers_onboard += group_size
                    
                    print(f"[Gate Agent] Boarded {group_size} from {gate_name} pool. "
                          f"Plane: {flight.passengers_onboard}/{flight.max_capacity} | "
                          f"Lounge Remaining: {state.global_simulation_state.gate_passenger_pool[gate_name]}")
                          
                elif available_at_gate == 0 and remaining_seats > 0:
                    print(f"[WARNING] Boarding stalled for [{flight.flight_id}] at {gate_name}! "
                          f"The gate lounge is completely EMPTY, but the plane still needs {remaining_seats} passengers.")
        # Yield control to allow the lifecycle loops to process updates
        await asyncio.sleep(boarding_rate_seconds)
    

async def manage_flight_lifecycle(flight: Flight):
    """
    Simulates the physical movement and behavior of a single aircraft
    stepping linearly through its track route.
    """
    flight_id = flight.flight_id
    # Bootstrap Entry: Place the flight onto its initial starting position
    if flight_id not in state.global_simulation_state.registry[flight.current_location]:
        state.global_simulation_state.registry[flight.current_location].append(flight_id)
    

    while True:
        current_node_name = flight.current_location
        current_node_obj = state.airport_network.nodes[current_node_name]
        # 1. Check for Absolute Edge Nodes (End of the entire Airport Graph)
        # We look at the static graph structure itself, NOT the live runtime options!
        if not current_node_obj.destinations:
            # We are at Departure_Hub. Clean up and exit.
            if flight_id in state.global_simulation_state.registry[current_node_name]:
                state.global_simulation_state.registry[current_node_name].remove(flight_id)
            break
        # 2. Query live options based on current runtime airport traffic
        forward_options = Router.get_valid_next_options(state.airport_network, current_node_name)
        target_node_name = Router.select_optimal_next_node(flight, forward_options, state.global_simulation_state.registry)
        # 3. Hold/Brake Lock: If forward options exist but are packed solid, wait.
        if target_node_name is None:
            if flight.state != FlightState.HOLDING and current_node_name == "Airspace_Alpha":
                flight.state = FlightState.HOLDING
                print(f"[{flight_id}] State: {flight.state.name:<15} | Location: {current_node_name:<22} | Pattern holding...")
            await asyncio.sleep(0.5)
            continue

        # 4. Atomic Two-Phase Lock Transaction Step
        if await acquire_graph_resources(flight, target_node_name):
            # Crucial: Remove yourself from the old node's registry array BEFORE updating your location
            if flight_id in state.global_simulation_state.registry[current_node_name]:
                state.global_simulation_state.registry[current_node_name].remove(flight_id)
            
            # Commit the step forward
            flight.current_location = target_node_name
            current_node_name = target_node_name
        else:
            # Back-off retry lock delay
            await asyncio.sleep(0.5)
            continue

        # 5. Continuous State Synchronization
        if current_node_name in state.NODE_STATE_MAP and flight.state != FlightState.GATE_BOARDING:
            flight.state = state.NODE_STATE_MAP[current_node_name]

        print(f"[{flight_id}] State: {flight.state.name:<15} | Location: {current_node_name:<22} | Line: {str(state.global_simulation_state.registry[current_node_name]):<25}")
        
        # 6. Operational Transit & Handling Delay Engine
        if "Gate" in current_node_name:
            # await asyncio.sleep(2.0)  # Deplaning operational delay
            if flight.state != FlightState.GATE_BOARDING:
                flight.state = FlightState.GATE_BOARDING
                print(f"[{flight_id}] State: {flight.state.name:<15} | Location: {current_node_name:<22} | Boarding Initialized.")
            
            print(f"[{flight_id}] State: {flight.state.name:<15} | Location: {current_node_name:<22} | Turnaround Complete")
            available_at_gate = state.global_simulation_state.gate_passenger_pool.get(current_node_name, 0)
            # Check conditions: Is the plane full, or is the gate empty
            print(flight.passengers_onboard, flight.max_capacity, available_at_gate)
            if flight.passengers_onboard >= flight.max_capacity or available_at_gate == 0:
                print(f"[{flight_id}] State: READY_FOR_PUSHBACK | Location: {current_node_name:<22} | Boarding concluded ({flight.passengers_onboard}/{flight.max_capacity}).")
                # Do NOT use 'continue' here! By hitting the end of this block, the loop cycles 
                # naturally to Step 2, querying the Router for "Taxiway_Zulu" options.
            else:
                # Still waiting for the background loader to feed passengers. 
                # Yield control for a brief tick and re-evaluate.
                await asyncio.sleep(0.2)
                continue
        elif flight.state == FlightState.TAKEOFF:
            await asyncio.sleep(1.0)  # High-speed runway run
        else:
            await asyncio.sleep(1.5)  # General taxiway taxiing speed delay

    # Final trace cleanup upon hitting absolute graph exit node boundary
    if flight_id in state.global_simulation_state.active_flights:
        del state.global_simulation_state.active_flights[flight_id]
    print(f"[{flight_id}] Cleared corridor. Active system pool size: {len(state.global_simulation_state.active_flights)}")
            
    


async def engine_orchestrator(queue: asyncio.Queue):
    """
    Pulls raw entities off the streaming network ingestion queue and hands
    them off immediately to concurrent runtime processes.
    """
    while True:
        # Blocks until a new flight payload enters the shared ingestion queue
        new_flight: Flight = await queue.get()
        
        # Register flight to active memory tracking table
        state.global_simulation_state.active_flights[new_flight.flight_id] = new_flight
        
        # Fire-and-forget: Spin up a lightweight concurrent green-thread for this plane
        asyncio.create_task(manage_flight_lifecycle(new_flight))
        
        # Signal queue that processing initialization has completed successfully
        queue.task_done()
    

async def main():
    # 1. Boot up the topology graph blueprint
    flight_ingestion_queue = asyncio.Queue()
    print("[SYSTEM] Booting Dynamic Graph Network Air Traffic Controller Engine...")
    
    # Run the background generator and orchestrator side-by-side
    await asyncio.gather(
        flight_generator_worker(flight_ingestion_queue, spawn_rate_seconds=2.5),
        engine_orchestrator(flight_ingestion_queue),
        passenger_loader_worker()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Air Traffic Control Engine safely shut down.")