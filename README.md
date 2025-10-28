# Dawly Documentation AI - KAG System

🤖 Knowledge-Augmented Generation system for music hardware documentation powered by OpenSPG.

## 🎯 Overview

Intelligent documentation retrieval and query system for music production hardware. Built on [OpenSPG KAG](https://github.com/OpenSPG/KAG) framework with specialized knowledge graph for device specifications, connections, and setup procedures.

## ✨ Features

- **📄 PDF Ingestion Pipeline** - Automatic extraction from manufacturer manuals
- **🧠 Knowledge Graph** - OpenSPG-powered SPG schema for devices and connections
- **💬 Natural Language Queries** - Ask questions in plain English
- **🔌 Connection Intelligence** - Port compatibility validation and recommendations
- **🎹 Device-Specific Context** - Filter answers by specific hardware
- **🚀 FastAPI REST API** - Easy integration with frontend
- **📊 Source References** - Citations with page numbers and confidence scores
- **⚡ ElasticSearch** - Vector embeddings for semantic search
- **🐘 PostgreSQL** - Knowledge graph storage
- **🔴 Redis** - Query caching for performance

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Dawly Documentation AI                     │
│                        (KAG System)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌────────────────┐                 │
│  │  PDF Scanner │ ───► │  Text Chunker  │                 │
│  └──────────────┘      └────────────────┘                 │
│         │                      │                           │
│         ▼                      ▼                           │
│  ┌──────────────┐      ┌────────────────┐                 │
│  │  PDF Reader  │ ───► │Entity Extractor│                 │
│  └──────────────┘      └────────────────┘                 │
│                                │                           │
│                                ▼                           │
│                    ┌────────────────────┐                  │
│                    │ Ingestion Pipeline │                  │
│                    └────────────────────┘                  │
│                                │                           │
│                                ▼                           │
│                    ┌────────────────────┐                  │
│                    │   OpenSPG  KAG     │                  │
│                    │   Knowledge Graph  │                  │
│                    └────────────────────┘                  │
│                           │      │                         │
│                  ┌────────┴──────┴────────┐               │
│                  │                         │               │
│         ┌────────▼────────┐     ┌─────────▼──────────┐    │
│         │   PostgreSQL    │     │  ElasticSearch     │    │
│         │  Graph Storage  │     │  Vector Embeddings │    │
│         └─────────────────┘     └────────────────────┘    │
│                                                             │
│                    ┌────────────────────┐                  │
│                    │    FastAPI Server  │                  │
│                    │  /query  /ingest   │                  │
│                    └────────────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- OpenAI API key (or local LLM)

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

# Setup environment
cp .env.example .env
# Edit .env with your OpenAI API key and configuration
```

### Environment Configuration

Edit `.env`:
```bash
# KAG Configuration
KAG_PROJECT_NAME=dawly_docs
KAG_LANGUAGE=en
KAG_DOMAIN=music_hardware

# Database (PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dawly_kag
POSTGRES_USER=kaguser
POSTGRES_PASSWORD=your_secure_password

# ElasticSearch
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=dawly_docs

# Redis (Optional, for caching)
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2000

# Embedding Model
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### Start Services

```bash
# Start PostgreSQL, ElasticSearch, Redis
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Run API server
uvicorn app.main:app --reload

# API available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## 📖 API Endpoints

### Query Documentation

```bash
POST /api/v1/query
Content-Type: application/json

{
  "query": "How do I connect MIDI devices to Digitakt II?",
  "device_id": "digitakt-ii"  # optional filter
}

Response:
{
  "answer": "Connect your MIDI controller to the MIDI In port...",
  "sources": [
    {
      "title": "Digitakt II Manual",
      "page": 12,
      "relevance": 0.95
    }
  ],
  "confidence": 0.9
}
```

### Ingest PDF

```bash
POST /api/v1/ingest
Content-Type: multipart/form-data

file: digitakt_manual.pdf
device_name: Digitakt II
manufacturer: Elektron

Response:
{
  "job_id": "job-123-456",
  "status": "processing",
  "message": "PDF ingestion started"
}
```

### Get Ingestion Status

```bash
GET /api/v1/ingest/status/{job_id}

Response:
{
  "job_id": "job-123-456",
  "status": "completed",
  "progress": 100,
  "entities_extracted": 45
}
```

### List Devices

```bash
GET /api/v1/devices?manufacturer=Elektron&type=drum_machine

Response:
{
  "devices": [
    {
      "id": "digitakt-ii",
      "name": "Digitakt II",
      "manufacturer": "Elektron",
      "type": "drum_machine",
      "ports": [...]
    }
  ]
}
```

### Get Device Connections

```bash
GET /api/v1/devices/{device_id}/connections

Response:
{
  "device_id": "digitakt-ii",
  "connections": [
    {
      "port_type": "midi_in",
      "compatible_with": ["midi_out"],
      "cable_type": "5-pin DIN MIDI",
      "notes": "Connect MIDI controller here"
    }
  ]
}
```

## 🗂️ Project Structure

```
dawly-doc-AI/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── schemas/
│   │   └── device_schema.py       # SPG schema (Pydantic models)
│   ├── ingestion/
│   │   ├── pdf_scanner.py         # PDF file discovery
│   │   ├── pdf_reader.py          # Text extraction
│   │   ├── text_chunker.py        # Intelligent chunking
│   │   ├── entity_extractor.py    # Device/port extraction
│   │   └── pipeline.py            # Orchestration
│   ├── api/
│   │   └── routes/
│   │       ├── query.py           # Query endpoints
│   │       ├── ingest.py          # Ingestion endpoints
│   │       └── devices.py         # Device endpoints
│   └── kag/
│       └── kg_builder.py          # Knowledge graph construction
├── tests/
│   ├── test_device_schema.py      # Schema unit tests
│   ├── test_pdf_ingestion.py      # Ingestion tests
│   └── integration/
│       └── test_api_workflow.py   # API integration tests
├── docs/
│   └── DEPLOYMENT.md              # Production deployment guide
├── kag_config.yaml                # KAG configuration
├── docker-compose.yml             # Development stack
├── docker-compose.prod.yml        # Production stack
├── Dockerfile                     # Multi-stage build
├── requirements.txt               # Python dependencies
└── pytest.ini                     # Test configuration
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Unit tests only (fast)
pytest -m "not integration and not slow"

# Integration tests
pytest -m integration

# With coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Specific test file
pytest tests/test_device_schema.py

# Verbose output
pytest -v --log-cli-level=DEBUG
```

## 🔧 Development

### SPG Schema

Defined in `app/schemas/device_schema.py`:

**Entities:**
- `Device` - Music hardware device
- `ConnectionPort` - Physical port on device
- `Documentation` - Manual or guide
- `ConnectionProcedure` - Step-by-step connection guide

**Relations:**
- `HasPort` - Device → Port
- `CompatibleWith` - Port → Port
- `DocumentedIn` - Device → Documentation
- `RequiresCable` - Port → CableType
- `DescribesConnection` - Procedure → Device

### Adding New Device Type

```python
class DeviceType(str, Enum):
    SYNTHESIZER = "synthesizer"
    DRUM_MACHINE = "drum_machine"
    SAMPLER = "sampler"
    SEQUENCER = "sequencer"
    MIXER = "mixer"
    EFFECTS_UNIT = "effects_unit"
    AUDIO_INTERFACE = "audio_interface"
    CONTROLLER = "controller"
    # Add your new type here
    NEW_TYPE = "new_type"
```

### Port Compatibility

Edit `PORT_COMPATIBILITY` matrix in `device_schema.py`:

```python
PORT_COMPATIBILITY = {
    PortType.MIDI_OUT: [PortType.MIDI_IN],
    PortType.AUDIO_OUT: [PortType.AUDIO_IN],
    # Add new compatibility rules
}
```

## 🐳 Docker Deployment

### Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Production

```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d

# Check service health
docker-compose -f docker-compose.prod.yml ps
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete production deployment guide.

## 📚 Documentation

- [Architecture](../docs/ARCHITECTURE.md) - System design
- [Deployment](docs/DEPLOYMENT.md) - Production deployment
- [API Reference](http://localhost:8000/docs) - OpenAPI documentation
- [MVP Specification](../DAWLY_MVP_SPEC.md) - Complete project spec

## 🤝 Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Follow [GitFlow workflow](../docs/DEVELOPMENT_WORKFLOW.md)
4. Add tests for new features
5. Ensure all tests pass (`pytest`)
6. Submit PR with @codex review request

## 🔗 Related Repositories

- [dawly-front](https://github.com/TerryBerk/dawly-front) - Frontend React Flow dashboard
- [dawly-back](https://github.com/TerryBerk/dawly-back) - Strapi CMS backend

## 📄 License

MIT License - see LICENSE file for details.

---

**Dawly Documentation AI** - Intelligent Music Hardware Documentation 🎹🤖
