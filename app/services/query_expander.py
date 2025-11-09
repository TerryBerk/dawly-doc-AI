"""
Query Expansion Service - Expands queries with synonyms and related terms
"""

from typing import List, Set
import re


class QueryExpander:
    """
    Expands search queries with synonyms and related terms
    to improve recall, especially for technical terminology
    """
    
    # Audio/Music production synonyms
    SYNONYMS = {
        # MIDI terms
        'midi': ['musical instrument digital interface', 'din', 'midi cable'],
        'cc': ['control change', 'continuous controller'],
        'pc': ['program change'],
        'sysex': ['system exclusive', 'sys ex'],
        
        # CV/Modular terms
        'cv': ['control voltage', 'voltage control'],
        'gate': ['trigger', 'pulse'],
        'clock': ['tempo', 'sync', 'timing'],
        'lfo': ['low frequency oscillator', 'modulation'],
        'vco': ['voltage controlled oscillator', 'oscillator'],
        'vcf': ['voltage controlled filter', 'filter'],
        'vca': ['voltage controlled amplifier', 'amplifier'],
        'adsr': ['attack decay sustain release', 'envelope'],
        'eg': ['envelope generator', 'envelope'],
        
        # Audio terms
        'audio': ['sound', 'signal'],
        'stereo': ['dual', 'two channel', 'left right'],
        'mono': ['single', 'one channel'],
        'balanced': ['differential', 'xlr'],
        'unbalanced': ['single ended', 'ts', 'tr'],
        
        # Connection terms
        'input': ['in', 'receive'],
        'output': ['out', 'send'],
        'thru': ['through', 'pass'],
        'mult': ['multiple', 'splitter'],
        
        # Power terms
        'power': ['supply', 'voltage', 'current'],
        'ma': ['milliamp', 'milliampere'],
        'v': ['volt', 'voltage'],
        'hp': ['horizontal pitch', 'width', 'module width'],
        
        # Effect terms
        'reverb': ['reverb', 'room', 'hall', 'plate'],
        'delay': ['echo', 'repeat'],
        'chorus': ['doubling', 'ensemble'],
        'distortion': ['overdrive', 'fuzz', 'saturation'],
        
        # Common abbreviations
        'daw': ['digital audio workstation', 'sequencer', 'host'],
        'usb': ['universal serial bus'],
        'xlr': ['cannon', 'balanced connector'],
        'trs': ['tip ring sleeve', 'balanced'],
        'ts': ['tip sleeve', 'unbalanced'],
        'rca': ['phono', 'cinch'],
    }
    
    # Technical expansions
    EXPANSIONS = {
        # Voltage ranges
        '5v': ['5 volt', 'five volt', '+5v', '0-5v'],
        '10v': ['10 volt', 'ten volt', '+10v', '-10v', '+/-10v'],
        
        # Common specs
        '1v/oct': ['1 volt per octave', 'v/oct', 'volt per octave'],
        '48v': ['phantom power', '48 volt'],
        '12v': ['twelve volt', '+12v', '-12v'],
        
        # Frequencies
        'hz': ['hertz', 'cycles per second'],
        'khz': ['kilohertz', 'thousand hertz'],
        
        # Time
        'ms': ['millisecond', 'milliseconds'],
        's': ['second', 'seconds'],
        'bpm': ['beats per minute', 'tempo'],
    }
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self._abbreviation_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in self.SYNONYMS.keys()) + r')\b',
            re.IGNORECASE
        )
    
    def expand_query(
        self,
        query: str,
        max_expansions: int = 3,
    ) -> str:
        """
        Expand query with synonyms and related terms
        
        Args:
            query: Original search query
            max_expansions: Maximum number of synonyms to add per term
            
        Returns:
            Expanded query string
        """
        query_lower = query.lower()
        expanded_terms: Set[str] = {query}
        
        # Find and expand abbreviations/technical terms
        for term, synonyms in self.SYNONYMS.items():
            if term in query_lower:
                # Add up to max_expansions synonyms
                for synonym in synonyms[:max_expansions]:
                    expanded_terms.add(
                        query_lower.replace(term, synonym)
                    )
        
        # Find and expand technical specs
        for spec, expansions in self.EXPANSIONS.items():
            if spec in query_lower:
                for expansion in expansions[:max_expansions]:
                    expanded_terms.add(
                        query_lower.replace(spec, expansion)
                    )
        
        # Join all expanded terms with OR
        return ' OR '.join(expanded_terms)
    
    def get_synonyms(self, term: str) -> List[str]:
        """Get synonyms for a specific term"""
        term_lower = term.lower()
        
        # Check direct match
        if term_lower in self.SYNONYMS:
            return self.SYNONYMS[term_lower]
        
        # Check expansions
        if term_lower in self.EXPANSIONS:
            return self.EXPANSIONS[term_lower]
        
        return []
    
    def add_synonym(self, term: str, synonyms: List[str]):
        """Add custom synonym mapping"""
        self.SYNONYMS[term.lower()] = synonyms
        
        # Recompile pattern
        self._abbreviation_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in self.SYNONYMS.keys()) + r')\b',
            re.IGNORECASE
        )
    
    def extract_technical_terms(self, text: str) -> List[str]:
        """Extract technical terms from text"""
        terms = []
        
        # Find abbreviations
        for term in self.SYNONYMS.keys():
            if re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE):
                terms.append(term)
        
        # Find specs
        for spec in self.EXPANSIONS.keys():
            if spec in text.lower():
                terms.append(spec)
        
        return list(set(terms))

