"""
Tests for SPG device schema
"""

import pytest
from datetime import datetime
from app.schemas.device_schema import (
    Device,
    ConnectionPort,
    Documentation,
    ConnectionProcedure,
    DeviceType,
    PortType,
    PortSpecifications,
    is_port_compatible,
)


def test_device_creation():
    """Test creating a valid device"""
    device = Device(
        device_id="test-device",
        name="Test Synth",
        manufacturer="Test Corp",
        model="TS-1",
        type=DeviceType.SYNTHESIZER,
        release_year=2024,
    )
    
    assert device.device_id == "test-device"
    assert device.name == "Test Synth"
    assert device.type == DeviceType.SYNTHESIZER
    assert isinstance(device.created_at, datetime)


def test_device_with_ports():
    """Test device with connection ports"""
    port = ConnectionPort(
        port_id="test-midi-in",
        type=PortType.MIDI_IN,
        label="MIDI IN",
        specifications=PortSpecifications(
            midi_channels=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
        ),
    )
    
    device = Device(
        device_id="test-device",
        name="Test Synth",
        manufacturer="Test Corp",
        model="TS-1",
        type=DeviceType.SYNTHESIZER,
        ports=[port],
    )
    
    assert len(device.ports) == 1
    assert device.ports[0].type == PortType.MIDI_IN


def test_connection_port_validation():
    """Test port validation"""
    port = ConnectionPort(
        port_id="test-midi-out",
        type=PortType.MIDI_OUT,
        label="MIDI OUT",
        position="back",
    )
    
    assert port.port_id == "test-midi-out"
    assert port.type == PortType.MIDI_OUT


def test_documentation_creation():
    """Test documentation entity"""
    doc = Documentation(
        doc_id="test-doc",
        title="Test Manual",
        pdf_path="/docs/test.pdf",
        page_count=50,
        device_ids=["test-device"],
    )
    
    assert doc.doc_id == "test-doc"
    assert doc.page_count == 50
    assert "test-device" in doc.device_ids


def test_connection_procedure():
    """Test connection procedure entity"""
    procedure = ConnectionProcedure(
        procedure_id="test-proc",
        title="MIDI Setup",
        steps=["Step 1", "Step 2", "Step 3"],
        requirements=["MIDI cable"],
        device_id="test-device",
    )
    
    assert procedure.procedure_id == "test-proc"
    assert len(procedure.steps) == 3
    assert "MIDI cable" in procedure.requirements


def test_port_compatibility():
    """Test port compatibility checking"""
    # MIDI Out to MIDI In should be compatible
    assert is_port_compatible(PortType.MIDI_OUT, PortType.MIDI_IN) is True
    
    # Audio Out to Audio In should be compatible
    assert is_port_compatible(PortType.AUDIO_OUT_LEFT, PortType.AUDIO_IN_LEFT) is True
    
    # MIDI to Audio should not be compatible
    assert is_port_compatible(PortType.MIDI_OUT, PortType.AUDIO_IN_LEFT) is False


def test_device_validation_empty_name():
    """Test that empty names are rejected"""
    with pytest.raises(ValueError):
        Device(
            device_id="test",
            name="",
            manufacturer="Test",
            model="TS-1",
            type=DeviceType.SYNTHESIZER,
        )


def test_device_validation_empty_manufacturer():
    """Test that empty manufacturer is rejected"""
    with pytest.raises(ValueError):
        Device(
            device_id="test",
            name="Test",
            manufacturer="",
            model="TS-1",
            type=DeviceType.SYNTHESIZER,
        )


def test_device_type_enum():
    """Test device type enumeration"""
    assert DeviceType.SYNTHESIZER.value == "synthesizer"
    assert DeviceType.DRUM_MACHINE.value == "drum_machine"
    assert DeviceType.AUDIO_INTERFACE.value == "audio_interface"


def test_port_type_enum():
    """Test port type enumeration"""
    assert PortType.MIDI_IN.value == "midi_in"
    assert PortType.AUDIO_OUT_LEFT.value == "audio_out_left"
    assert PortType.CV_IN.value == "cv_in"


def test_real_world_example_digitakt():
    """Test with real-world example: Elektron Digitakt II"""
    device = Device(
        device_id="digitakt-ii",
        name="Digitakt II",
        manufacturer="Elektron",
        model="Digitakt II",
        type=DeviceType.DRUM_MACHINE,
        release_year=2024,
        description="Advanced drum computer and sampler",
        ports=[
            ConnectionPort(
                port_id="digitakt-ii-midi-in",
                type=PortType.MIDI_IN,
                label="MIDI IN",
                position="back",
                specifications=PortSpecifications(
                    midi_channels=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                    connector_type="5-pin DIN",
                ),
            ),
            ConnectionPort(
                port_id="digitakt-ii-midi-out",
                type=PortType.MIDI_OUT,
                label="MIDI OUT",
                position="back",
            ),
            ConnectionPort(
                port_id="digitakt-ii-audio-out-l",
                type=PortType.AUDIO_OUT_LEFT,
                label="MAIN OUT L",
                position="back",
                specifications=PortSpecifications(
                    impedance="100 ohms",
                    connector_type="6.35mm TRS",
                ),
            ),
            ConnectionPort(
                port_id="digitakt-ii-audio-out-r",
                type=PortType.AUDIO_OUT_RIGHT,
                label="MAIN OUT R",
                position="back",
            ),
        ],
    )
    
    assert device.device_id == "digitakt-ii"
    assert device.manufacturer == "Elektron"
    assert len(device.ports) == 4
    assert device.ports[0].type == PortType.MIDI_IN
    assert device.ports[2].specifications.impedance == "100 ohms"
