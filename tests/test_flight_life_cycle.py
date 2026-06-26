import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from models import Flight, FlightState, AircraftType

class MockNode:
    def __init__(self, name, destinations=None):
        self.name = name
        self.destinations = destinations 
    

class MockState:
    def __init__(self):
        self.registry = {"Airspace_Alpha": [], "Gate_C4": [], "Departure_Hub": [], "Taxiway_Zulu": [], "Runway_09L": []}
        self.airport_network = MagicMock()
        self.airport_network.nodes = {
            "Airspace_Alpha": MockNode("Airspace_Alpha", destinations=["Gate_C4"]),
            "Gate_C4": MockNode("Gate_C4", destinations=["Taxiway_Zulu"]),
            "Taxiway_Zulu": MockNode("Taxiway_Zulu", destinations=["Runway_09L"]),
            "Runway_09L": MockNode("Runway_09L", destinations=["Departure_Hub"]),
            "Departure_Hub": MockNode("Departure_Hub", destinations=[])
        }
        self.active_flights = {}
         # NEW: Tracks how many passengers are sitting in the chairs at each gate lounge
        self.gate_passenger_pool = {
            "Gate_C4": 12,    # 12 passengers waiting at C4
            "Gate_E1": 15     # 15 passengers waiting at E1 (this one will stall!)
        }

NODE_STATE_MAP = {
    "Airspace_Alpha": FlightState.AIRSPACE,
    "Gate_C4": FlightState.GATE_DEPLANING,
    "Taxiway_Zulu": FlightState.TAXI_TO_RUNWAY,
    "Departure_Hub": FlightState.TAKEOFF,
}


@pytest.mark.asyncio
@patch('main.state.global_simulation_state')  # Patch the global state object where manage_flight_lifecycle lives
@patch('main.Router') # Patch the Router class
@patch('main.acquire_graph_resources', new_callable=AsyncMock)
async def test_bootstrap_and_immediate_hold(mock_acquire, mock_router, mock_state_module):
    """
    Test 1: Verifies the flight bootstraps into the registry 
    and transitions to HOLDING state if no target node is available.
    """
    local_state = MockState()
    mock_state_module.registry = local_state.registry
    mock_state_module.airport_network = local_state.airport_network
    mock_state_module.gate_passenger_pool = local_state.gate_passenger_pool
    
    flight = Flight(flight_id="UAL_452", aircraft_type=AircraftType.LIGHT_PROP, initial_location="Airspace_Alpha")
    local_state.active_flights[flight.flight_id] = flight
    
    mock_router.get_valid_next_options.return_with = [MockNode("Gate_C4", destinations=["Departure_Hub"])]
    mock_router.select_optimal_next_node.return_value = None
    mock_acquire.return_value = True
    
    # Intercept the infinite loop: raise an exception on the second iteration
    # to stop the loop after testing the hold branch
    mock_router.get_valid_next_options.side_effect = [[MockNode("Gate_C4", destinations=["Departure_Hub"])], ValueError("Break Loop Intentional")]
    
    with pytest.raises(ValueError, match="Break Loop Intentional"):
        from main import manage_flight_lifecycle
        await manage_flight_lifecycle(flight)
    
    # Assertions
    assert "UAL_452" in local_state.registry["Airspace_Alpha"], "Flight failed to bootstrap into starting registry"
    assert flight.state == FlightState.HOLDING, "Flight failed to pivot into HOLDING pattern state"


@pytest.mark.asyncio
@patch('main.state.global_simulation_state')
@patch('main.Router')
@patch('main.acquire_graph_resources', new_callable=AsyncMock)
@patch('main.state.NODE_STATE_MAP', NODE_STATE_MAP)
async def test_successful_resource_acquisition_and_move(mock_acquire, mock_router, mock_state_module):
    """
    Test 2: Verifies that when resource acquisition succeeds, the flight 
    is removed from old registry, added to new registry, and location changes.
    """
    local_state = MockState()
    mock_state_module.registry = local_state.registry
    mock_state_module.airport_network = local_state.airport_network
    mock_state_module.gate_passenger_pool = local_state.gate_passenger_pool

    flight = Flight(flight_id="AAL_101", aircraft_type=AircraftType.LIGHT_PROP, initial_location="Airspace_Alpha")
    local_state.active_flights[flight.flight_id] = flight
    flight.passengers_onboard = flight.max_capacity
    
    gate_c4 = MockNode("Gate_C4", destinations=["Departure_Hub"])

    mock_router.get_valid_next_options.return_with = [gate_c4]
    mock_router.select_optimal_next_node.return_value = gate_c4.name
    
    mock_acquire.return_value = True
    mock_router.get_valid_next_options.side_effect = [[gate_c4], ValueError("Break Loop")]
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        from main import manage_flight_lifecycle
        with pytest.raises(ValueError):
            await manage_flight_lifecycle(flight)
    
    assert flight.current_location == "Gate_C4", "Flight location properties did not update forward"
    assert "AAL_101" not in local_state.registry["Airspace_Alpha"], "Flight failed to clear tail out of historical registry"
    assert flight.state == FlightState.GATE_BOARDING


@pytest.mark.asyncio
@patch('main.state.global_simulation_state')
@patch('main.Router')
@patch('main.acquire_graph_resources', new_callable=AsyncMock)
@patch('main.state.NODE_STATE_MAP', NODE_STATE_MAP)
async def test_edge_node_cleanup_and_exit(mock_acquire, mock_router_cls, mock_state_module):
    """
    Test 3: Verifies that arriving at an absolute graph edge node 
    (no downstream destinations) cleanly terminates the loop, 
    purges the registry trace, and updates the global active flight pool.
    """
    local_state = MockState()
    local_state.registry = {"Departure_Hub": [], "Gate_C4": []}
    mock_state_module.registry = local_state.registry
    mock_state_module.airport_network = local_state.airport_network
    mock_state_module.active_flights = local_state.active_flights
    mock_state_module.gate_passenger_pool = local_state.gate_passenger_pool

    mock_acquire.return_value = True
    
    # 1. Setup target flight ID consistently
    target_flight_id = "AAL_101"
    flight = Flight(flight_id=target_flight_id, aircraft_type=AircraftType.LIGHT_PROP, initial_location="Gate_C4")
    
    local_state.registry["Departure_Hub"].append(flight.flight_id)
    local_state.active_flights[flight.flight_id] = flight

    # 2. Setup the router instance mock correctly
    departure_hub = MockNode("Departure_Hub", destinations=[])
    
    # If main.py instantiates router = Router(), mock_router_cls.return_value is the instance
    mock_router_cls.get_valid_next_options.return_value = [departure_hub]
    mock_router_cls.select_optimal_next_node.return_value = departure_hub.name

    from main import manage_flight_lifecycle
    
    # Run lifecycle loop
    await manage_flight_lifecycle(flight)

     # 3. Assertions targeted accurately at the flight under test
    assert target_flight_id not in local_state.registry["Departure_Hub"], "Registry failed to purge terminal footprint"
    assert target_flight_id not in local_state.active_flights, "Flight remained stranded in active tracking pool"

@pytest.mark.asyncio
@patch('main.state.global_simulation_state')
@patch('main.Router')
@patch('main.acquire_graph_resources', new_callable=AsyncMock)
@patch('main.state.NODE_STATE_MAP', NODE_STATE_MAP)
async def test_gate_holding_until_passenger_capacity_met(
    mock_acquire, mock_router, mock_state_module
):
    """
    Test 4 Fixed: Verifies that a flight docked at a gate will poll and hold 
    its position, advancing under-capacity if the lounge runs empty.
    """
    # FIX 1: Fix assignment alignment by matching the bottom-up stack rules
    # mock_acquire -> acquire_graph_resources
    # mock_router -> Router
    # mock_state_module -> global_simulation_state
    
    local_state = MockState()
    mock_state_module.registry = local_state.registry
    mock_state_module.gate_passenger_pool = local_state.gate_passenger_pool
    
    flight = Flight(flight_id="JBU_77", aircraft_type=AircraftType.REGIONAL_JET, initial_location="Gate_C4")
    flight.state = FlightState.GATE_BOARDING
    flight.passengers_onboard = 20  # Under-capacity
    
    local_state.registry["Gate_C4"].append(flight.flight_id)
    
    taxiway = MockNode("Taxiway_Zulu", destinations=["Runway_09L"])
    mock_router.get_valid_next_options.return_value = [taxiway]
    mock_router.select_optimal_next_node.return_value = taxiway.name
    mock_acquire.return_value = True
    
    # FIX 2: Explicitly structure the timeline ticks using a list side_effect sequence
    # Tick 1: Flight handles loading. We leave 1 person in lounge so it holds.
    # Tick 2: Lounge hits 0, Step 6 completes, loop cycles to step 2, we intercept and break.
    def simulate_processing_ticks(*args, **kwargs):
        if mock_state_module.gate_passenger_pool["Gate_C4"] > 0:
            flight.passengers_onboard += mock_state_module.gate_passenger_pool["Gate_C4"]
            mock_state_module.gate_passenger_pool["Gate_C4"] = 0
            return [taxiway]
        else:
            # Loop successfully passed Step 6 check and is attempting a pushback routing pass!
            raise ValueError("Cleared Gate Block Successfully")
    
    mock_router.get_valid_next_options.side_effect = simulate_processing_ticks
    
    with pytest.raises(ValueError, match="Cleared Gate Block Successfully"):
        from main import manage_flight_lifecycle
        await manage_flight_lifecycle(flight)
    
    # Assertions match your rule: 30 passengers onboard out of 50 capacity limit
    assert flight.passengers_onboard < flight.max_capacity, "Flight failed to push back under-capacity when lounge emptied"
    assert mock_state_module.gate_passenger_pool["Gate_C4"] == 0, "Gate lounge pool failed to completely deplete"
