"""Tests for the select platform."""

import logging
from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from msmart.device import AirConditioner as AC
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.midea_ac.const import DOMAIN
from custom_components.midea_ac.coordinator import MideaDeviceUpdateCoordinator

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)


async def test_fresh_air_fan_speed_select(
        hass: HomeAssistant,
        entity_registry: er.EntityRegistry,
        mock_config_entry: MockConfigEntry,
) -> None:
    """Test an AC device that supports fresh air creates a fan speed select."""

    mock_config_entry.mock_state(hass, ConfigEntryState.LOADED)
    mock_config_entry.add_to_hass(hass)

    # Create a dummy AC device and force fresh air support
    mock_device = AC("0.0.0.0", 0, 0)
    mock_device._online = True
    mock_device.power_state = True
    mock_device._capabilities.set(AC.Capability.FRESH_AIR, True)

    # Create a mock coordinator
    coordinator = MagicMock(spec=MideaDeviceUpdateCoordinator)
    coordinator.device = mock_device
    coordinator.apply = AsyncMock()

    # Store coordinator in global data
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coordinator

    # Setup climate (to name the device) and select platforms
    await hass.config_entries.async_forward_entry_setups(
        mock_config_entry, [Platform.CLIMATE]
    )
    await hass.async_block_till_done()

    await hass.config_entries.async_forward_entry_setups(
        mock_config_entry, [Platform.SELECT]
    )
    await hass.async_block_till_done()

    # Verify the fresh air fan speed select exists
    entity_id = "select.midea_ac_0_fresh_air_fan_speed"
    state = hass.states.get(entity_id)
    assert state

    # OFF is excluded; the dedicated switch handles on/off
    assert state.attributes["options"] == [
        "low", "medium", "high", "boost"]
    # Default speed is medium
    assert state.state == "medium"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == "0-fresh_air_fan_speed"

    # Selecting an option should set the device property and apply
    await hass.services.async_call(
        Platform.SELECT, "select_option",
        {"entity_id": entity_id, "option": "high"}, blocking=True
    )
    assert mock_device.fresh_air_fan_speed == AC.FreshAirFanSpeed.HIGH
    coordinator.apply.assert_awaited()
