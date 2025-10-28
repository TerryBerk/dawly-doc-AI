"""
SPG Schema for Music Hardware Devices

Defines entity types, relations, and constraints for the Knowledge Graph.
Based on OpenSPG framework and kag_config.yaml specification.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class DeviceType(str, Enum):
    """Device types supported by Dawly"""
    SYNTHESIZER = "synthesizer"
    DRUM_MACHINE = "drum_machine"
    AUDIO_INTERFACE = "audio_interface"
    EURORACK_MODULE = "eurorack_module"
    CONTROLLER = "controller"
    EFFECT = "effect"
    MIXER = "mixer"
    MONITOR = "monitor"


class PortType(str, Enum):
    """Connection port types"""
    MIDI_IN = "midi_in"
    MIDI_OUT = "midi_out"
    MIDI_THRU = "midi_thru"
    AUDIO_IN_LEFT = "audio_in_left"
    AUDIO_IN_RIGHT = "audio_in_right"
    AUDIO_OUT_LEFT = "audio_out_left"
    AUDIO_OUT_RIGHT = "audio_out_right"
    POWER = "power"
    CV_IN = "cv_in"
    CV_OUT = "cv_out"
    GATE_IN = "gate_in"
    GATE_OUT = "gate_out"
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"
    USB = "usb"
    ETHERNET = "ethernet"


class PortSpecifications(BaseModel):
    """Port-specific specifications"""
    voltage: Optional[str] = None
    impedance: Optional[str] = None
    midi_channels: Optional[List[int]] = None
    sample_rate: Optional[str] = None
    bit_depth: Optional[str] = None
    max_current: Optional[str] = None
    connector_type: Optional[str] = None


class ConnectionPort(BaseModel):
    """
    SPG Entity: ConnectionPort
    
    Represents a physical connection port on a music device.
    """
    port_id: str = Field(..., description="Unique port identifier")
    type: PortType = Field(..., description="Type of connection port")
    label: str = Field(..., description="Human-readable port label")
    position: Optional[str] = Field(None, description="Physical position on device (front/back/side)")
    specifications: Optional[PortSpecifications] = Field(None, description="Technical specifications")
    
    # SPG Relations
    device_id: Optional[str] = Field(None, description="Parent device ID (has_port relation)")
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "port_id": "digitakt-ii-midi-in",
                "type": "midi_in",
                "label": "MIDI IN",
                "position": "back",
                "specifications": {
                    "midi_channels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                    "connector_type": "5-pin DIN"
                }
            }
        }


class Device(BaseModel):
    """
    SPG Entity: Device
    
    Represents a music production hardware device.
    """
    device_id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Device name")
    manufacturer: str = Field(..., description="Manufacturer name")
    model: str = Field(..., description="Model number/name")
    type: DeviceType = Field(..., description="Device type")
    release_year: Optional[int] = Field(None, ge=1950, le=2100, description="Release year")
    description: Optional[str] = Field(None, description="Device description")
    
    # Relations
    ports: List[ConnectionPort] = Field(default_factory=list, description="Device ports (has_port relation)")
    documentation_ids: List[str] = Field(default_factory=list, description="Related documentation IDs (documented_in relation)")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('name', 'manufacturer', 'model')
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "device_id": "digitakt-ii",
                "name": "Digitakt II",
                "manufacturer": "Elektron",
                "model": "Digitakt II",
                "type": "drum_machine",
                "release_year": 2024,
                "description": "Advanced drum computer and sampler with 16 tracks",
                "ports": [
                    {
                        "port_id": "digitakt-ii-midi-in",
                        "type": "midi_in",
                        "label": "MIDI IN"
                    }
                ]
            }
        }


class Documentation(BaseModel):
    """
    SPG Entity: Documentation
    
    Represents device documentation (PDF manuals).
    """
    doc_id: str = Field(..., description="Unique documentation identifier")
    title: str = Field(..., description="Documentation title")
    pdf_path: str = Field(..., description="Path to PDF file")
    version: Optional[str] = Field(None, description="Documentation version")
    page_count: Optional[int] = Field(None, ge=1, description="Number of pages")
    language: str = Field(default="en", description="Documentation language")
    
    # Relations
    device_ids: List[str] = Field(default_factory=list, description="Related device IDs (documented_in relation)")
    
    # Metadata
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = Field(default=False, description="Whether PDF has been processed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "digitakt-ii-manual-v1",
                "title": "Digitakt II User Manual",
                "pdf_path": "/docs_data/Digitakt_II_Manual.pdf",
                "version": "1.0",
                "page_count": 120,
                "language": "en",
                "device_ids": ["digitakt-ii"]
            }
        }


class ConnectionProcedure(BaseModel):
    """
    SPG Entity: ConnectionProcedure
    
    Represents step-by-step connection procedures extracted from documentation.
    """
    procedure_id: str = Field(..., description="Unique procedure identifier")
    title: str = Field(..., description="Procedure title")
    steps: List[str] = Field(..., min_items=1, description="Step-by-step instructions")
    requirements: Optional[List[str]] = Field(default_factory=list, description="Required equipment/cables")
    warnings: Optional[List[str]] = Field(default_factory=list, description="Safety warnings or important notes")
    
    # Relations
    device_id: Optional[str] = Field(None, description="Related device ID (procedure_for relation)")
    source_doc_id: Optional[str] = Field(None, description="Source documentation ID")
    source_page: Optional[int] = Field(None, description="Source page number")
    
    # Port relationships
    involves_port_ids: List[str] = Field(default_factory=list, description="Ports involved in procedure (involves_ports relation)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "procedure_id": "digitakt-ii-midi-sync",
                "title": "MIDI Clock Sync Setup",
                "steps": [
                    "Connect MIDI cable from master device MIDI OUT to Digitakt II MIDI IN",
                    "Press FUNC + SYSTEM to enter Settings",
                    "Navigate to MIDI CONFIG",
                    "Set CLOCK RECEIVE to ON",
                    "Set TRANSPORT RECEIVE to ON"
                ],
                "requirements": ["MIDI cable", "Master clock device"],
                "warnings": ["Ensure both devices are powered off before connecting cables"],
                "device_id": "digitakt-ii",
                "involves_port_ids": ["digitakt-ii-midi-in"]
            }
        }


# SPG Relation Types (for reference, actual implementation in KAG)
class RelationType(str, Enum):
    """Relation types in the knowledge graph"""
    HAS_PORT = "has_port"  # Device → ConnectionPort
    DOCUMENTED_IN = "documented_in"  # Device → Documentation
    CONNECTS_TO = "connects_to"  # ConnectionPort → ConnectionPort
    PROCEDURE_FOR = "procedure_for"  # ConnectionProcedure → Device
    INVOLVES_PORTS = "involves_ports"  # ConnectionProcedure → ConnectionPort


class ConnectionRelation(BaseModel):
    """
    Represents a connection between two ports
    """
    source_port_id: str
    target_port_id: str
    cable_type: Optional[str] = None
    compatibility: Optional[str] = Field(None, description="Compatibility notes or warnings")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_port_id": "digitakt-ii-midi-out",
                "target_port_id": "audio-interface-midi-in",
                "cable_type": "MIDI 5-pin DIN",
                "compatibility": "Supports full MIDI 1.0 specification"
            }
        }


# Helper functions for schema validation and conversion

def validate_device(device_data: Dict[str, Any]) -> Device:
    """Validate and parse device data"""
    return Device(**device_data)


def validate_port(port_data: Dict[str, Any]) -> ConnectionPort:
    """Validate and parse port data"""
    return ConnectionPort(**port_data)


def validate_documentation(doc_data: Dict[str, Any]) -> Documentation:
    """Validate and parse documentation data"""
    return Documentation(**doc_data)


def validate_procedure(procedure_data: Dict[str, Any]) -> ConnectionProcedure:
    """Validate and parse procedure data"""
    return ConnectionProcedure(**procedure_data)


# Port compatibility matrix (for validation)
PORT_COMPATIBILITY_MATRIX = {
    PortType.MIDI_OUT: [PortType.MIDI_IN],
    PortType.MIDI_THRU: [PortType.MIDI_IN],
    PortType.AUDIO_OUT_LEFT: [PortType.AUDIO_IN_LEFT],
    PortType.AUDIO_OUT_RIGHT: [PortType.AUDIO_IN_RIGHT],
    PortType.CV_OUT: [PortType.CV_IN],
    PortType.GATE_OUT: [PortType.GATE_IN],
    PortType.CLOCK_OUT: [PortType.CLOCK_IN],
}


def is_port_compatible(source_type: PortType, target_type: PortType) -> bool:
    """Check if two port types are compatible for connection"""
    compatible_targets = PORT_COMPATIBILITY_MATRIX.get(source_type, [])
    return target_type in compatible_targets
