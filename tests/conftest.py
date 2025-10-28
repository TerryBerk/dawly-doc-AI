"""
Pytest configuration and shared fixtures
"""

import pytest
import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory"""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def sample_device_data():
    """Sample device data for testing"""
    return {
        "name": "Digitakt II",
        "manufacturer": "Elektron",
        "model": "DIGITAKT-II",
        "type": "drum_machine",
        "release_year": 2024,
        "description": "16-voice digital drum computer",
        "ports": [
            {
                "id": "midi-in-1",
                "type": "midi_in",
                "label": "MIDI In",
                "location": "rear"
            },
            {
                "id": "midi-out-1",
                "type": "midi_out",
                "label": "MIDI Out",
                "location": "rear"
            },
            {
                "id": "audio-out-l",
                "type": "audio_out_balanced",
                "label": "Main Out L",
                "location": "rear"
            },
            {
                "id": "audio-out-r",
                "type": "audio_out_balanced",
                "label": "Main Out R",
                "location": "rear"
            }
        ]
    }


@pytest.fixture
def mock_kag_response():
    """Mock KAG query response"""
    return {
        "answer": "The Digitakt II features MIDI In and Out ports on the rear panel. "
                 "Connect your MIDI controller to MIDI In, and sync other devices via MIDI Out. "
                 "Use standard 5-pin DIN MIDI cables.",
        "sources": [
            {
                "title": "Digitakt II Manual - Connections",
                "page": 12,
                "relevance": 0.95
            }
        ],
        "confidence": 0.9
    }


@pytest.fixture
def api_client():
    """FastAPI test client"""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def pytest_configure(config):
    """Configure pytest environment"""
    # Set test environment variable
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"
