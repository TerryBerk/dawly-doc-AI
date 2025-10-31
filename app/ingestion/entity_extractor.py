"""
Entity Extractor - Extracts structured entities from text using LLM
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional
from app.schemas.device_schema import (
    Device,
    ConnectionPort,
    ConnectionProcedure,
    DeviceType,
    PortType,
)

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Extracts structured entities from documentation text
    """
    
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        
    def extract_devices(self, text: str, page_number: int) -> List[Dict[str, Any]]:
        """
        Extract device mentions from text
        
        Args:
            text: Text to analyze
            page_number: Source page number
            
        Returns:
            List of device information dictionaries
        """
        devices = []
        
        # Pattern matching for device names (simplified)
        # Real implementation would use LLM for better extraction
        device_patterns = [
            r"(Digitakt\s*II?)",
            r"(Octatrack\s*MKII?)",
            r"(Analog\s*(?:Four|Rytm|Keys))",
        ]
        
        for pattern in device_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                device_name = match.group(1)
                devices.append({
                    "name": device_name,
                    "page_number": page_number,
                    "context": text[max(0, match.start()-50):match.end()+50]
                })
        
        return devices
    
    def extract_ports(self, text: str, page_number: int) -> List[Dict[str, Any]]:
        """
        Extract connection port information from text
        
        Args:
            text: Text to analyze
            page_number: Source page number
            
        Returns:
            List of port information dictionaries
        """
        ports = []
        
        # Pattern matching for ports
        port_patterns = {
            PortType.MIDI_IN: [r"MIDI\s+IN(?:PUT)?", r"MIDI\s+INPUT"],
            PortType.MIDI_OUT: [r"MIDI\s+OUT(?:PUT)?", r"MIDI\s+OUTPUT"],
            PortType.MIDI_THRU: [r"MIDI\s+THRU"],
            PortType.AUDIO_OUT_LEFT: [r"AUDIO\s+OUT(?:PUT)?\s+L(?:EFT)?", r"MAIN\s+OUT\s+L"],
            PortType.AUDIO_OUT_RIGHT: [r"AUDIO\s+OUT(?:PUT)?\s+R(?:IGHT)?", r"MAIN\s+OUT\s+R"],
            PortType.USB: [r"USB\s+(?:PORT|CONNECTION|INTERFACE)"],
        }
        
        for port_type, patterns in port_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    ports.append({
                        "type": port_type.value,
                        "label": match.group(0),
                        "page_number": page_number,
                        "context": text[max(0, match.start()-50):match.end()+50]
                    })
        
        return ports
    
    def extract_procedures(
        self,
        text: str,
        page_number: int
    ) -> List[Dict[str, Any]]:
        """
        Extract connection procedures from text
        
        Args:
            text: Text to analyze
            page_number: Source page number
            
        Returns:
            List of procedure information dictionaries
        """
        procedures = []
        
        # Look for numbered steps or procedure indicators
        procedure_indicators = [
            "to connect",
            "connection procedure",
            "setup",
            "follow these steps",
        ]
        
        text_lower = text.lower()
        
        for indicator in procedure_indicators:
            if indicator in text_lower:
                # Extract surrounding text
                start = text_lower.index(indicator)
                end = min(start + 500, len(text))
                
                procedure_text = text[start:end]
                
                # Extract steps (simplified)
                steps = self._extract_steps(procedure_text)
                
                if steps:
                    procedures.append({
                        "title": indicator.title(),
                        "steps": steps,
                        "page_number": page_number,
                        "text": procedure_text,
                    })
        
        return procedures
    
    def _extract_steps(self, text: str) -> List[str]:
        """Extract numbered or bulleted steps from text"""
        steps = []
        
        # Pattern for numbered steps: "1.", "1)", "Step 1:"
        numbered_pattern = r"(?:^|\n)(?:\d+[\.\)]\s*|\bStep\s+\d+:?\s*)(.*?)(?=\n\d+[\.\)]|\nStep\s+\d+|$)"
        matches = re.findall(numbered_pattern, text, re.MULTILINE | re.DOTALL)
        
        if matches:
            steps = [step.strip() for step in matches if step.strip()]
        
        return steps
    
    def extract_specifications(
        self,
        text: str,
        page_number: int
    ) -> Dict[str, Any]:
        """
        Extract technical specifications from text
        
        Args:
            text: Text to analyze
            page_number: Source page number
            
        Returns:
            Dictionary of specifications
        """
        specs = {
            "page_number": page_number,
            "voltage": None,
            "impedance": None,
            "sample_rate": None,
            "bit_depth": None,
        }
        
        # Pattern matching for specifications
        spec_patterns = {
            "voltage": r"(\d+(?:\.\d+)?\s*V)",
            "impedance": r"(\d+\s*(?:ohms?|Ω))",
            "sample_rate": r"(\d+\s*kHz)",
            "bit_depth": r"(\d+\s*bit)",
        }
        
        for spec_name, pattern in spec_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                specs[spec_name] = match.group(1)
        
        return specs
    
    def extract_all(
        self,
        text: str,
        page_number: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all entity types from text
        
        Args:
            text: Text to analyze
            page_number: Source page number
            
        Returns:
            Dictionary with all extracted entities
        """
        return {
            "devices": self.extract_devices(text, page_number),
            "ports": self.extract_ports(text, page_number),
            "procedures": self.extract_procedures(text, page_number),
            "specifications": self.extract_specifications(text, page_number),
        }
