import pytest

from models import Flight, FlightState, AircraftType, Gate, ResourceType, Runway
from main import acquire_graph_resources
import state
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def setup_isolated_state():
    """
    Runs automatically before EVERY test. 
    Clears out the global registry and injects a clean network instance.
    """
    # 1. Clear out global registry tracking
    state.registry.clear()
    
    # 2. Instantiate a completely fresh network 
    # (Using the custom empty nodes dictionary we designed earlier!)
    fresh_network = state.AirportNetwork(nodes={})
    
    # 3. Overwrite the global state's network attribute dynamically
    state.airport_network = fresh_network
    
    yield  # The test runs here
    
@pytest.mark.asyncio
async def test_acquire_graph_resources_not_occupied_gate():
    
    state.registry.clear()
    mock_gate_c4 = MagicMock(spec=Gate)
    mock_gate_c4.name = "Gate_C4"
    mock_gate_c4.max_capacity = 1
    mock_gate_c4.passenger_count = 200
    mock_gate_c4.resource_type = ResourceType.PIPELINE
    state.registry["Gate_C4"] = []
    state.airport_network.nodes["Gate_C4"] = mock_gate_c4

    mock_incoming_flight = MagicMock(flight_id="DELTA_101")
    result = await acquire_graph_resources(mock_incoming_flight, "Gate_C4")
    assert result == True

@pytest.mark.asyncio
async def test_acquire_graph_resources_already_occupied_gate():
    
    state.registry.clear()
    mock_gate_c4 = MagicMock(spec=Gate)
    mock_gate_c4.name = "Gate_C4"
    mock_gate_c4.max_capacity = 1
    mock_gate_c4.passenger_count = 200
    mock_gate_c4.resource_type = ResourceType.PIPELINE
    state.registry["Gate_C4"] = ["HAWAIIAN_50"]
    state.airport_network.nodes["Gate_C4"] = mock_gate_c4

    mock_incoming_flight = MagicMock(flight_id="DELTA_101")
    result = await acquire_graph_resources(mock_incoming_flight, "Gate_C4")
    assert result == False


@pytest.mark.asyncio
async def test_acquire_graph_resources_occupied_runway():
    
    mock_runway = MagicMock(spec=Runway)
    mock_runway.name = "Runway_09R"
    mock_runway.max_capacity = 1
    mock_runway.resource_type = ResourceType.MONOLITHIC
    
    state.registry["Runway_09R"] = ["HAWAIIAN_50"] # Occupied!
    
    # CRITICAL FIX: Inject the mock node into your fresh network dictionary
    state.airport_network.nodes["Runway_09R"] = mock_runway

    mock_incoming_flight = MagicMock()
    mock_incoming_flight.flight_id = "DELTA_101"
    
    result = await acquire_graph_resources(mock_incoming_flight, "Runway_09R")
    
    assert result is False

@pytest.mark.asyncio
async def test_acquire_graph_resources_not_occupied_runway():
    
    state.registry.clear()
    
    # 2. Setup an empty, available Runway
    mock_runway = MagicMock(spec=Runway)
    mock_runway.name = "Runway_09R"
    mock_runway.max_capacity = 1
    mock_runway.resource_type = ResourceType.MONOLITHIC
    
    # CRITICAL: Explicitly state there are no downstream blocks choking it
    mock_runway.destinations = [] 
    
    # Register the runway as empty in the system registry
    state.registry["Runway_09R"] = []
    
    # Inject it into your mocked network state
    state.airport_network.nodes["Runway_09R"] = mock_runway

    # 3. Setup incoming flight mock correctly
    mock_incoming_flight = MagicMock()
    mock_incoming_flight.flight_id = "DELTA_101"
    
    # 4. Act
    result = await acquire_graph_resources(mock_incoming_flight, "Runway_09R")
    
    # 5. Assert
    assert result is True
    # Verify the flight was actually added to the runway
    assert "DELTA_101" in state.registry["Runway_09R"]


    

