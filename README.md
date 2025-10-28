# Dawly Documentation AI

Knowledge-Augmented Generation (KAG) system for music hardware documentation powered by OpenSPG.

**Version:** 0.1.0 (MVP)  
**Status:** 🚧 In Development

---

## Overview

Intelligent documentation retrieval system for music production hardware using OpenSPG KAG framework. Provides accurate answers to technical questions about device connections, specifications, and setup procedures through multi-hop reasoning and hybrid retrieval.

## Features

- 🔍 **PDF Documentation Ingestion** - Process manufacturer manuals (Elektron, Arturia, Moog, etc.)
- 💬 **Natural Language Queries** - Ask questions in plain English  
- 🎹 **Connection-Focused** - Optimized for MIDI, Audio, Power, CV/Gate connection queries
- 🕸️ **Knowledge Graph** - Structured device specifications with relationships
- 🚀 **REST API** - FastAPI endpoints for Dawly platform integration
- 🧠 **Multi-Hop Reasoning** - Complex queries across multiple devices/docs
- 🎯 **High Accuracy** - Schema-constrained entity extraction

## Architecture

```
┌─────────────────────────────────────┐
│      dawly-doc-AI                   │
│                                     │
│  ┌──────────────────────────────┐  │
│  │   FastAPI REST API           │  │
│  └───────────┬──────────────────┘  │
│              │                      │
│  ┌───────────▼──────────────────┐  │
│  │     KAG Framework v0.8.0     │  │
│  │  ┌──────────┐  ┌──────────┐ │  │
│  │  │kg-builder│  │kg-solver │ │  │
│  │  └──────────┘  └──────────┘ │  │
│  └──────────────────────────────┘  │
│              │                      │
│  ┌───────────▼──────────────────┐  │
│  │   OpenSPG Engine             │  │
│  │ - PostgreSQL (Graph Storage) │  │
│  │ - ElasticSearch (Vectors)    │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- OpenAI API key (or local LLM setup)

### Installation

```bash
# Clone repository
git clone https://github.com/TerryBerk/dawly-doc-AI.git
cd dawly-doc-AI

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your OpenAI API key and settings

# Start OpenSPG services (PostgreSQL + ElasticSearch)
docker-compose up -d postgres elasticsearch

# Wait for services to be healthy
docker-compose ps

# Initialize database
python -m app.db.init

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

API will be available at: **http://localhost:8000**

### Docker (Full Stack)

```bash
# Build and start all services
docker-compose up --build

# API: http://localhost:8000
# PostgreSQL: localhost:5432
# ElasticSearch: http://localhost:9200
```

## API Endpoints

### Documentation Queries

**POST** `/api/v1/query`

Query device documentation with natural language.

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "digitakt-ii",
    "question": "How do I connect MIDI to my audio interface?"
  }'
```

Response:
```json
{
  "answer": "To connect Digitakt II MIDI to your audio interface...",
  "sources": [
    {"page": 42, "section": "MIDI Connections", "confidence": 0.92}
  ],
  "confidence": 0.89
}
```

### PDF Ingestion

**POST** `/api/v1/ingest`

Upload and process device manual.

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@Digitakt_II_Manual.pdf" \
  -F "device_name=Digitakt II" \
  -F "manufacturer=Elektron"
```

### Device Connection Info

**GET** `/api/v1/devices/{device_id}/connections`

Get structured connection information.

```bash
curl http://localhost:8000/api/v1/devices/digitakt-ii/connections
```

Response:
```json
{
  "device_id": "digitakt-ii",
  "ports": [
    {"type": "midi_in", "label": "MIDI IN", "specs": {"channels": "1-16"}},
    {"type": "midi_out", "label": "MIDI OUT", "specs": {"channels": "1-16"}},
    {"type": "audio_out_left", "label": "MAIN OUT L"},
    {"type": "audio_out_right", "label": "MAIN OUT R"}
  ]
}
```

### Health Check

**GET** `/health`

```bash
curl http://localhost:8000/health
```

## Configuration

### Environment Variables

See [.env.example](.env.example) for all configuration options:

- **KAG Configuration**: Project name, domain, language
- **Database**: PostgreSQL connection settings
- **ElasticSearch**: Vector store configuration
- **LLM**: OpenAI API key, model, temperature
- **Embedding**: Model for vector embeddings
- **Processing**: Chunk size, parallel processes

### KAG Config

Main configuration in [kag_config.yaml](kag_config.yaml):

- **SPG Schema**: Entity types (Device, ConnectionPort, Documentation)
- **kg-builder**: Ingestion pipeline settings
- **kg-solver**: Query processing and reasoning
- **Prompts**: LLM prompt templates

## Development

### GitFlow Workflow

```bash
# Create feature branch
git checkout -b feature/2-spg-schema

# Make changes, test

# Commit with conventional commits
git commit -m "feat(schema): define SPG schema for music devices"

# Push and create PR
git push -u origin feature/2-spg-schema
gh pr create --base develop --title "feat(schema): Define SPG schema"
```

### Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest --cov=app tests/

# Specific test
pytest tests/test_pdf_ingestion.py
```

### Code Quality

```bash
# Format code
black app/ tests/
ruff format app/ tests/

# Type check
mypy app/

# Linting
ruff check app/ tests/
```

## Project Structure

```
dawly-doc-AI/
├── app/
│   ├── api/              # FastAPI routes
│   ├── schemas/          # SPG schema definitions
│   ├── ingestion/        # PDF processing pipeline
│   ├── kag/              # KAG integration
│   ├── db/               # Database models
│   └── main.py           # FastAPI application
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── fixtures/         # Test data
├── docs_data/            # Uploaded PDFs
├── checkpoints/          # Processing checkpoints
├── docker-compose.yml    # Docker services
├── kag_config.yaml       # KAG configuration
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## SPG Schema

### Entity Types

- **Device**: Music hardware (synthesizer, drum machine, etc.)
- **ConnectionPort**: MIDI/Audio/Power/CV ports
- **Documentation**: PDF manuals, sections
- **ConnectionProcedure**: Setup steps and requirements

### Relations

- `has_port`: Device → ConnectionPort
- `documented_in`: Device → Documentation
- `connects_to`: ConnectionPort → ConnectionPort
- `procedure_for`: ConnectionProcedure → Device

See [kag_config.yaml](kag_config.yaml) for full schema definition.

## Roadmap

- [x] Issue #1: Setup KAG infrastructure
- [ ] Issue #2: Define SPG schema implementation
- [ ] Issue #3: Build REST API endpoints
- [ ] Issue #6: Implement PDF ingestion pipeline
- [ ] Issue #7: Multi-hop reasoning
- [ ] Issue #14: Docker deployment
- [ ] Issue #16: Integration tests

## Contributing

1. Fork repository
2. Create feature branch (`feature/<issue-number>-<name>`)
3. Make changes with tests
4. Submit PR to `develop` branch
5. Request review from `@codex`

See [DEVELOPMENT_WORKFLOW.md](../docs/DEVELOPMENT_WORKFLOW.md) for details.

## Documentation

- [Architecture Overview](../docs/ARCHITECTURE.md)
- [KAG Setup Guide](../docs/KAG_INTEGRATION.md)
- [API Reference](../docs/API_REFERENCE.md)
- [Getting Started](../docs/GETTING_STARTED.md)

## License

MIT License - See [LICENSE](LICENSE) for details.

---

**Dawly Documentation AI** - Part of the Dawly ecosystem  
**Repository**: https://github.com/TerryBerk/dawly-doc-AI
