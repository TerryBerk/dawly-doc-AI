"""
Tests for PDF ingestion pipeline
"""

import pytest
from pathlib import Path
from app.ingestion.pdf_scanner import PDFScanner
from app.ingestion.pdf_reader import PDFReader, PDFPage
from app.ingestion.text_chunker import TextChunker
from app.ingestion.entity_extractor import EntityExtractor


def test_pdf_scanner_init():
    """Test PDFScanner initialization"""
    scanner = PDFScanner("./test_docs")
    assert scanner.docs_directory == Path("./test_docs")
    assert ".pdf" in scanner.supported_extensions


def test_pdf_scanner_validate():
    """Test PDF validation"""
    scanner = PDFScanner()
    
    # Valid PDF path (mocked)
    # In real tests, you'd use a fixture PDF file
    # For now, just test the validation logic
    assert scanner.supported_extensions == [".pdf"]


def test_pdf_reader_init():
    """Test PDFReader initialization"""
    reader = PDFReader(preserve_tables=True)
    assert reader.preserve_tables is True
    
    reader_no_tables = PDFReader(preserve_tables=False)
    assert reader_no_tables.preserve_tables is False


def test_text_chunker_init():
    """Test TextChunker initialization"""
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    assert chunker.chunk_size == 1000
    assert chunker.chunk_overlap == 200


def test_text_chunker_simple():
    """Test chunking simple text"""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    
    text = "This is a test. " * 20  # 320 characters
    chunks = chunker.chunk(text, page_number=1, doc_id="test-doc")
    
    assert len(chunks) > 0
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert all(chunk.chunk_id.startswith("test-doc-p1") for chunk in chunks)


def test_text_chunker_overlap():
    """Test chunk overlap"""
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    
    text = "A" * 100
    chunks = chunker.chunk(text, page_number=1, doc_id="test")
    
    assert len(chunks) >= 2
    # Check that chunks have reasonable sizes
    for chunk in chunks:
        assert len(chunk.text) <= 60  # chunk_size + some buffer


def test_entity_extractor_init():
    """Test EntityExtractor initialization"""
    extractor = EntityExtractor(use_llm=True)
    assert extractor.use_llm is True


def test_entity_extractor_ports():
    """Test port extraction"""
    extractor = EntityExtractor(use_llm=False)
    
    text = """
    The device has the following connections:
    - MIDI IN on the back panel
    - MIDI OUT next to MIDI IN
    - AUDIO OUTPUT L on the left
    - AUDIO OUTPUT R on the right
    - USB PORT for computer connection
    """
    
    ports = extractor.extract_ports(text, page_number=1)
    
    assert len(ports) > 0
    # Should find MIDI IN, MIDI OUT, USB
    port_types = [p["type"] for p in ports]
    assert "midi_in" in port_types or "midi_out" in port_types


def test_entity_extractor_procedures():
    """Test procedure extraction"""
    extractor = EntityExtractor(use_llm=False)
    
    text = """
    To connect your device:
    1. Connect the MIDI cable from MIDI OUT to your interface
    2. Connect the audio cables to AUDIO OUT L and R
    3. Power on the device
    Follow these steps carefully.
    """
    
    procedures = extractor.extract_procedures(text, page_number=1)
    
    assert len(procedures) > 0
    # Should extract steps
    if procedures:
        assert "steps" in procedures[0]


def test_entity_extractor_specifications():
    """Test specification extraction"""
    extractor = EntityExtractor(use_llm=False)
    
    text = """
    Technical specifications:
    - Power: 12V DC
    - Output impedance: 100 ohms
    - Sample rate: 48 kHz
    - Bit depth: 24 bit
    """
    
    specs = extractor.extract_specifications(text, page_number=1)
    
    assert specs["page_number"] == 1
    # Should extract at least some specs
    # (depends on regex matching)


def test_entity_extractor_all():
    """Test extracting all entity types"""
    extractor = EntityExtractor(use_llm=False)
    
    text = """
    Digitakt II User Manual
    
    MIDI IN and MIDI OUT connections are located on the back panel.
    To connect:
    1. Connect MIDI cable
    2. Power on
    
    Specifications: 100 ohms impedance, 12V power
    """
    
    result = extractor.extract_all(text, page_number=5)
    
    assert "devices" in result
    assert "ports" in result
    assert "procedures" in result
    assert "specifications" in result


def test_text_chunker_empty_text():
    """Test chunking empty text"""
    chunker = TextChunker()
    chunks = chunker.chunk("", page_number=1, doc_id="test")
    assert len(chunks) == 0


def test_text_chunker_metadata():
    """Test chunk metadata"""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    text = "Test text " * 20
    
    chunks = chunker.chunk(text, page_number=3, doc_id="my-doc")
    
    assert len(chunks) > 0
    chunk = chunks[0]
    
    assert chunk.chunk_id.startswith("my-doc-p3-c")
    assert chunk.page_number == 3
    assert "doc_id" in chunk.metadata
    assert chunk.metadata["doc_id"] == "my-doc"
