"""
Devices API - Device connection information
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class PortInfo(BaseModel):
    """Port information"""
    type: str
    label: str
    specs: Optional[dict] = None


class DeviceConnections(BaseModel):
    """Device connection information"""
    device_id: str
    name: str
    manufacturer: str
    ports: List[PortInfo]
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "digitakt-ii",
                "name": "Digitakt II",
                "manufacturer": "Elektron",
                "ports": [
                    {
                        "type": "midi_in",
                        "label": "MIDI IN",
                        "specs": {"channels": "1-16"}
                    },
                    {
                        "type": "midi_out",
                        "label": "MIDI OUT",
                        "specs": {"channels": "1-16"}
                    },
                    {
                        "type": "audio_out_left",
                        "label": "MAIN OUT L",
                        "specs": {"impedance": "100 ohms"}
                    },
                    {
                        "type": "audio_out_right",
                        "label": "MAIN OUT R",
                        "specs": {"impedance": "100 ohms"}
                    }
                ]
            }
        }


@router.get("/devices/{device_id}/connections", response_model=DeviceConnections)
async def get_device_connections(device_id: str):
    """
    Get structured connection information for a device
    
    Args:
        device_id: Device identifier (e.g., 'digitakt-ii')
        
    Returns:
        Device connection information with all ports
    """
    logger.info(f"Fetching connections for device: {device_id}")
    
    # TODO: Query from OpenSPG knowledge graph
    
    # Mock data for common devices
    device_mock_data = {
        "digitakt-ii": DeviceConnections(
            device_id="digitakt-ii",
            name="Digitakt II",
            manufacturer="Elektron",
            ports=[
                PortInfo(type="midi_in", label="MIDI IN", specs={"channels": "1-16"}),
                PortInfo(type="midi_out", label="MIDI OUT", specs={"channels": "1-16"}),
                PortInfo(type="audio_out_left", label="MAIN OUT L", specs={"impedance": "100 ohms"}),
                PortInfo(type="audio_out_right", label="MAIN OUT R", specs={"impedance": "100 ohms"}),
                PortInfo(type="usb", label="USB", specs={"type": "USB 2.0"}),
            ]
        )
    }
    
    if device_id not in device_mock_data:
        raise HTTPException(
            status_code=404,
            detail=f"Device '{device_id}' not found in knowledge base"
        )
    
    return device_mock_data[device_id]


@router.get("/devices")
async def list_devices(
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    limit: int = Query(50, description="Number of devices to return", ge=1, le=100)
):
    """
    List available devices in knowledge base
    
    Args:
        manufacturer: Filter by manufacturer
        device_type: Filter by device type
        limit: Number of results
        
    Returns:
        List of devices
    """
    # TODO: Query from OpenSPG
    
    return {
        "devices": [],
        "total": 0,
        "manufacturer": manufacturer,
        "device_type": device_type,
        "limit": limit
    }


@router.get("/devices/{device_id}")
async def get_device_info(device_id: str):
    """
    Get detailed device information
    
    Args:
        device_id: Device identifier
        
    Returns:
        Device details
    """
    logger.info(f"Fetching info for device: {device_id}")
    
    # TODO: Query from OpenSPG
    
    return {
        "device_id": device_id,
        "name": device_id.replace("-", " ").title(),
        "manufacturer": "Unknown",
        "type": "unknown",
        "documentation_available": False
    }
