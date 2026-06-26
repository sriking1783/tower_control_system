import pytest
from unittest.mock import MagicMock
from router import Router
from models import Flight, AircraftType, AirportNetwork, AirportNode, ResourceType, Gate, Runway
from typing import Dict, List
from main import acquire_graph_resources
import state


def test_no_destination():
    flight = Flight("UAL-001", AircraftType.LIGHT_PROP, "Airspace_Alpha")
    start = AirportNode("Airspace", ResourceType.PIPELINE, 999)
    runway = AirportNode("Runway", ResourceType.MONOLITHIC, 1)
    custom_nodes = {"Airspace": start, "Runway": runway}
    
    # Inject it!
    test_network = AirportNetwork(nodes=custom_nodes)
    registry: Dict[str, List[str]] = {node_name: [] for node_name in test_network.nodes}
    with pytest.raises(ValueError) as exc_info:
        Router.select_optimal_next_node(flight, [], registry)
        
def test_one_option():
    flight = Flight("UAL-001", AircraftType.LIGHT_PROP, "Airspace_Alpha")
    start = AirportNode("Airspace", ResourceType.PIPELINE, 999)
    runway = AirportNode("Runway", ResourceType.MONOLITHIC, 1)
    start.add_connection(runway)
    custom_nodes = {"Airspace": start, "Runway": runway}
    
    # Inject it!
    test_network = AirportNetwork(nodes=custom_nodes)
    registry: Dict[str, List[str]] = {node_name: [] for node_name in test_network.nodes}
    destinations = Router.get_valid_next_options(test_network, "Airspace")
    assert "Runway" == Router.select_optimal_next_node(flight, destinations, registry)


@pytest.mark.asyncio
async def test_two_options():
    # 1. Arrange
    state.global_simulation_state.registry.clear()
    
    # Configure Gate C4 (Full)
    mock_gate_c4 = MagicMock(spec=Gate)
    mock_gate_c4.name = "Gate_C4"
    mock_gate_c4.max_capacity = 1
    mock_gate_c4.passenger_count = 450
    mock_gate_c4.resource_type = ResourceType.PIPELINE
    state.global_simulation_state.registry["Gate_C4"] = ["HAWAIIAN_50"] # Occupied

    # Configure Gate E1 (Available)
    mock_gate_e1 = MagicMock(spec=Gate)
    mock_gate_e1.name = "Gate_E1"
    mock_gate_e1.max_capacity = 1
    mock_gate_e1.passenger_count = 350  # Fixed typo here!
    mock_gate_e1.resource_type = ResourceType.PIPELINE
    state.global_simulation_state.registry["Gate_E1"] = [] # Empty
    
    # Mock Flight
    mock_incoming_flight = MagicMock()
    mock_incoming_flight.flight_id = "DELTA_101"
    
    destinations = [mock_gate_c4, mock_gate_e1]
    
    # 2. Act
    selected_node = Router.select_optimal_next_node(
        mock_incoming_flight, 
        destinations, 
        state.global_simulation_state.registry
    )
    
    # 3. Assert
    assert selected_node == "Gate_E1"


    
@pytest.mark.asyncio
async def test_two_options_queue():
    # 1. Clear out the global tracking registry cleanly
    state.global_simulation_state.registry.clear()
    mock_gate_c4 = MagicMock(spec=Gate)
    mock_gate_c4.name = "Gate_C4"
    mock_gate_c4.max_capacity = 1
    mock_gate_c4.passenger_count = 200
    mock_gate_c4.resource_type = ResourceType.PIPELINE
    
    state.global_simulation_state.registry["Gate_C4"] = ["HAWAIIAN_50"]

    mock_incoming_flight = MagicMock(flight_id="DELTA_101")
    result = await acquire_graph_resources(mock_incoming_flight, "Gate_C4")
    mock_runway = MagicMock()
    mock_runway.name = "Runway"
    mock_runway.max_capacity = 1
    mock_runway.resource_type = ResourceType.MONOLITHIC

    mock_gate_e1 = MagicMock(spec=Gate)
    mock_gate_e1.name = "Gate_E1"
    mock_gate_e1.max_capacity = 1
    mock_gate_e1.resource_type = ResourceType.PIPELINE
    mock_gate_e1.passenger_count = 250
    state.global_simulation_state.registry["Gate_E1"] = ["DELTA_65"]

    result = await acquire_graph_resources(mock_incoming_flight, "Gate_E1")

    mock_runway.destinations = [mock_gate_c4, mock_gate_e1]
    
    state.airport_network.nodes = {"Gate_E1": mock_gate_e1, "Gate_C4": mock_gate_c4, "Runway": mock_runway}
    
    destinations = [mock_gate_c4, mock_gate_e1]

    assert "Gate_C4" == Router.select_optimal_next_node(mock_incoming_flight, destinations, state.global_simulation_state.registry)