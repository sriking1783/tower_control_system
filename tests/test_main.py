import pytest

from models import Flight, FlightState, AircraftType, Gate, ResourceType, Runway
from main import acquire_graph_resources
import state
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_acquire_graph_resources_not_occupied_gate():
    
    state.registry.clear()
    mock_gate_c4 = MagicMock(spec=Gate)
    mock_gate_c4.name = "Gate_C4"
    mock_gate_c4.max_capacity = 1
    mock_gate_c4.passenger_count = 200
    mock_gate_c4.resource_type = ResourceType.PIPELINE
    state.registry["Gate_C4"] = []

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

    mock_incoming_flight = MagicMock(flight_id="DELTA_101")
    result = await acquire_graph_resources(mock_incoming_flight, "Gate_C4")
    assert result == False


@pytest.mark.asyncio
async def test_acquire_graph_resources_occupied_runway():
    
    state.registry.clear()
    mock_gate_c4 = MagicMock(spec=Runway)
    mock_gate_c4.name = "Runway_09R"
    mock_gate_c4.max_capacity = 1
    mock_gate_c4.resource_type = ResourceType.MONOLITHIC
    state.registry["Runway_09R"] = ["HAWAIIAN_50"]

    mock_incoming_flight = MagicMock(flight_id="DELTA_101")
    result = await acquire_graph_resources(mock_incoming_flight, "Runway_09R")
    assert result == False

@pytest.mark.asyncio
async def test_acquire_graph_resources_not_occupied_runway():
    
    state.registry.clear()
    mock_gate_c4 = MagicMock(spec=Runway)
    mock_gate_c4.name = "Runway_09R"
    mock_gate_c4.max_capacity = 1
    mock_gate_c4.resource_type = ResourceType.MONOLITHIC
    state.registry["Runway_09R"] = []

    mock_incoming_flight = MagicMock(flight_id="DELTA_101")
    result = await acquire_graph_resources(mock_incoming_flight, "Runway_09R")
    assert result == True


    

