import asyncio
import random
import string
from typing import List
from models import Flight, AircraftType, FlightState

MOCK_ROUTE: List[str] = [
    # ---- INBOUND LEG ----
    "Airspace_Alpha",        # Index 0: Spawn / Inbound flight
    "Holding_Pattern_North", # Index 1: Macro delay queue
    "Runway_09R",            # Index 2: Landing bottleneck
    "Taxiway_Kilo",          # Index 3: Inbound taxi track
    
    # ---- TERMINAL TURNAROUND ----
    "Gate_C4",               # Index 4: Deplaning & Boarding passengers
    
    # ---- OUTBOUND LEG ----
    "Taxiway_Zulu",          # Index 5: Outbound taxi track
    "Runway_09L",            # Index 6: Departure bottleneck
    "Departure_Corridor"     # Index 7: Takeoff / Exit simulation entirely
]

def generate_random_flight_id() -> str:
    """Generates an airline token like UAL-482 or AAL-910."""
    airline = random.choice(["UAL", "AAL", "DAL", "BAW", "FDX"])
    digits = "".join(random.choices(string.digits, k=3))
    return f"{airline}-{digits}"


async def flight_generator_worker(queue: asyncio.Queue, spawn_rate_seconds: float = 3.0):
    """
    Background worker that continuously streams new flights into the engine queue.
    Simulates the chaotic arrival of real-world air traffic.
    """
    print(f"[SYSTEM] Flight generator initialized. Spawning every {spawn_rate_seconds}s...")
    
    while True:
        flight_id = generate_random_flight_id()
        aircraft_type = random.choice(list(AircraftType))
        
        new_flight = Flight(
            flight_id = flight_id,
            aircraft_type = aircraft_type,
            state = FlightState.AIRSPACE,
            assigned_route=MOCK_ROUTE.copy(),
            current_node_index=0,
        )
        
        # Safely push the payload into the asyncio communication channel
        await queue.put(new_flight)
        print(f"[SPAWNER] New flight {new_flight.flight_id} ({new_flight.aircraft_type.name}) entered airspace. Fuel: {new_flight.fuel_remaining}%")
        await asyncio.sleep(spawn_rate_seconds)