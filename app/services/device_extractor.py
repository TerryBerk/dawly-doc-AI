"""
Device metadata extraction service
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ConnectionSpec:
    """Connection specification"""
    type: str  # MIDI, Audio, Power
    ports_in: int
    ports_out: int
    specifications: Dict[str, str]


@dataclass
class DeviceInfo:
    """Device information extracted from PDF"""
    device_id: str
    name: str
    manufacturer: str
    model: Optional[str]
    device_type: Optional[str]
    connections: List[ConnectionSpec]
    technical_specs: Dict[str, str]
    filename: str


class DeviceExtractor:
    """Extract device specifications from PDFs"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Patterns for connection sections
        self.connection_patterns = {
            'midi': [
                r'midi\s+connection',
                r'midi\s+in\/?out',
                r'midi\s+specification',
                r'midi\s+ports?',
                r'connecting\s+via\s+midi'
            ],
            'audio': [
                r'audio\s+connection',
                r'audio\s+in\/?out',
                r'audio\s+specification',
                r'audio\s+ports?',
                r'connecting\s+audio',
                r'output\s+specification'
            ],
            'power': [
                r'power\s+supply',
                r'power\s+specification',
                r'power\s+connection',
                r'voltage',
                r'power\s+requirements?'
            ]
        }
        
        # Patterns for technical specs
        self.spec_patterns = {
            'sample_rate': r'sample\s+rate.*?(\d+\.?\d*\s*kHz)',
            'bit_depth': r'bit\s+depth.*?(\d+)\s*bit',
            'polyphony': r'polyphony.*?(\d+)\s*voice',
            'tracks': r'(\d+)\s*track',
            'memory': r'memory.*?(\d+)\s*(MB|GB)',
        }
    
    def extract_device_info(
        self,
        text: str,
        filename: str,
        device_name: str,
        manufacturer: str
    ) -> DeviceInfo:
        """
        Extract device specifications from PDF text
        
        Args:
            text: Full document text
            filename: PDF filename
            device_name: Device name (from user input)
            manufacturer: Manufacturer name (from user input)
            
        Returns:
            DeviceInfo object
        """
        self.logger.info(f"Extracting device info for {device_name}")
        
        # Generate device_id
        device_id = self._generate_device_id(device_name, manufacturer)
        
        # Extract model if present in text
        model = self._extract_model(text, device_name)
        
        # Detect device type
        device_type = self._detect_device_type(text, device_name)
        
        # Extract connections
        connections = self._extract_connections(text)
        
        # Extract technical specifications
        technical_specs = self._extract_technical_specs(text)
        
        device_info = DeviceInfo(
            device_id=device_id,
            name=device_name,
            manufacturer=manufacturer,
            model=model,
            device_type=device_type,
            connections=connections,
            technical_specs=technical_specs,
            filename=filename
        )
        
        self.logger.info(f"Extracted device info: {device_id}")
        return device_info
    
    def _generate_device_id(self, device_name: str, manufacturer: str) -> str:
        """
        Generate device_id from device_name
        
        Examples:
            Digitakt II, Elektron -> elektron-digitakt-ii
            Analog Four MKII, Elektron -> elektron-analog-four-mkii
        """
        # Combine manufacturer and device name
        combined = f"{manufacturer} {device_name}"
        
        # Convert to lowercase
        device_id = combined.lower()
        
        # Replace spaces and special characters with hyphens
        device_id = re.sub(r'[^a-z0-9]+', '-', device_id)
        
        # Remove leading/trailing hyphens
        device_id = device_id.strip('-')
        
        # Remove duplicate hyphens
        device_id = re.sub(r'-+', '-', device_id)
        
        return device_id
    
    def _extract_model(self, text: str, device_name: str) -> Optional[str]:
        """Try to extract model number from text"""
        # Common model patterns
        patterns = [
            rf'{re.escape(device_name)}\s+([A-Z0-9\-]+)',
            r'Model\s*:?\s*([A-Z0-9\-]+)',
            r'Product\s+Code\s*:?\s*([A-Z0-9\-]+)',
        ]
        
        text_sample = text[:5000]  # Check first 5000 chars
        
        for pattern in patterns:
            match = re.search(pattern, text_sample, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _detect_device_type(self, text: str, device_name: str) -> Optional[str]:
        """Detect device type from text or name"""
        device_types = {
            'synthesizer': ['synth', 'synthesizer', 'analog', 'digital synth'],
            'drum-machine': ['drum machine', 'drum computer', 'rhythm', 'beats'],
            'sampler': ['sampler', 'sampling'],
            'sequencer': ['sequencer'],
            'groovebox': ['groovebox', 'groove box'],
            'effects': ['effects', 'reverb', 'delay', 'processor'],
            'mixer': ['mixer'],
            'controller': ['controller', 'keyboard'],
        }
        
        text_sample = (device_name + " " + text[:2000]).lower()
        
        for device_type, keywords in device_types.items():
            for keyword in keywords:
                if keyword in text_sample:
                    return device_type
        
        return None
    
    def _extract_connections(self, text: str) -> List[ConnectionSpec]:
        """Extract connection specifications"""
        connections = []
        
        # Search for MIDI connections
        midi_spec = self._extract_midi_connections(text)
        if midi_spec:
            connections.append(midi_spec)
        
        # Search for Audio connections
        audio_spec = self._extract_audio_connections(text)
        if audio_spec:
            connections.append(audio_spec)
        
        # Search for Power specifications
        power_spec = self._extract_power_spec(text)
        if power_spec:
            connections.append(power_spec)
        
        return connections
    
    def _extract_midi_connections(self, text: str) -> Optional[ConnectionSpec]:
        """Extract MIDI connection details"""
        # Find MIDI sections
        midi_text = self._extract_section_text(text, self.connection_patterns['midi'])
        
        if not midi_text:
            return None
        
        # Count MIDI IN/OUT ports
        midi_in_count = len(re.findall(r'MIDI\s+IN', midi_text, re.IGNORECASE))
        midi_out_count = len(re.findall(r'MIDI\s+OUT', midi_text, re.IGNORECASE))
        
        # Default to 1 if found mentions but no count
        if 'midi' in midi_text.lower():
            midi_in_count = midi_in_count or 1
            midi_out_count = midi_out_count or 1
        
        specs = {}
        
        # Extract MIDI channels
        channels_match = re.search(r'(\d+)\s*channels?', midi_text, re.IGNORECASE)
        if channels_match:
            specs['channels'] = channels_match.group(1)
        
        # Extract MIDI type (DIN, USB, etc.)
        if 'USB' in midi_text or 'usb' in midi_text.lower():
            specs['type'] = 'USB MIDI + DIN'
        elif '5-pin' in midi_text or 'DIN' in midi_text:
            specs['type'] = 'DIN 5-pin'
        
        return ConnectionSpec(
            type='MIDI',
            ports_in=midi_in_count,
            ports_out=midi_out_count,
            specifications=specs
        )
    
    def _extract_audio_connections(self, text: str) -> Optional[ConnectionSpec]:
        """Extract Audio connection details"""
        audio_text = self._extract_section_text(text, self.connection_patterns['audio'])
        
        if not audio_text:
            return None
        
        # Count audio outputs
        outputs = len(re.findall(r'output', audio_text, re.IGNORECASE))
        inputs = len(re.findall(r'input', audio_text, re.IGNORECASE))
        
        # Default to stereo (2 outputs) if outputs mentioned
        if outputs > 0 and outputs < 10:
            pass
        elif 'stereo' in audio_text.lower():
            outputs = 2
        elif 'mono' in audio_text.lower():
            outputs = 1
        
        specs = {}
        
        # Extract connector type
        if '1/4' in audio_text or 'TRS' in audio_text or 'jack' in audio_text.lower():
            specs['connector'] = '1/4" TRS'
        elif 'XLR' in audio_text:
            specs['connector'] = 'XLR'
        
        # Extract sample rate
        sample_rate_match = re.search(r'(\d+\.?\d*)\s*kHz', audio_text)
        if sample_rate_match:
            specs['sample_rate'] = f"{sample_rate_match.group(1)} kHz"
        
        # Extract bit depth
        bit_match = re.search(r'(\d+)\s*bit', audio_text)
        if bit_match:
            specs['bit_depth'] = f"{bit_match.group(1)} bit"
        
        return ConnectionSpec(
            type='Audio',
            ports_in=inputs,
            ports_out=outputs,
            specifications=specs
        )
    
    def _extract_power_spec(self, text: str) -> Optional[ConnectionSpec]:
        """Extract Power specifications"""
        power_text = self._extract_section_text(text, self.connection_patterns['power'])
        
        if not power_text:
            return None
        
        specs = {}
        
        # Extract voltage
        voltage_match = re.search(r'(\d+\.?\d*)\s*V(?:olts?)?', power_text, re.IGNORECASE)
        if voltage_match:
            specs['voltage'] = f"{voltage_match.group(1)}V"
        
        # Extract current
        current_match = re.search(r'(\d+\.?\d*)\s*m?A(?:mps?)?', power_text, re.IGNORECASE)
        if current_match:
            specs['current'] = current_match.group(0)
        
        # Extract power consumption
        watt_match = re.search(r'(\d+\.?\d*)\s*W(?:atts?)?', power_text, re.IGNORECASE)
        if watt_match:
            specs['power'] = f"{watt_match.group(1)}W"
        
        # Detect power type
        if 'DC' in power_text or 'd.c.' in power_text.lower():
            specs['type'] = 'DC'
        elif 'AC' in power_text or 'a.c.' in power_text.lower():
            specs['type'] = 'AC'
        
        return ConnectionSpec(
            type='Power',
            ports_in=1,
            ports_out=0,
            specifications=specs
        )
    
    def _extract_section_text(self, text: str, patterns: List[str], context_chars: int = 1000) -> str:
        """Extract text around section matching patterns"""
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                start = max(0, match.start() - context_chars // 2)
                end = min(len(text), match.end() + context_chars)
                return text[start:end]
        
        return ""
    
    def _extract_technical_specs(self, text: str) -> Dict[str, str]:
        """Extract technical specifications"""
        specs = {}
        
        # Use spec patterns to extract values
        for spec_name, pattern in self.spec_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                specs[spec_name] = match.group(1) if match.lastindex else match.group(0)
        
        return specs
    
    def to_dict(self, device_info: DeviceInfo) -> Dict:
        """Convert DeviceInfo to dictionary"""
        data = asdict(device_info)
        # Convert ConnectionSpec objects to dicts
        data['connections'] = [asdict(conn) for conn in device_info.connections]
        return data

