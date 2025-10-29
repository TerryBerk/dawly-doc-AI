# Dawly Documentation AI - KAG Backend

Knowledge-Augmented Generation (KAG) system for music hardware documentation.

## Overview

FastAPI-based backend providing intelligent documentation retrieval for music hardware devices. Uses RAG (Retrieval-Augmented Generation) with Elasticsearch for vector search and PostgreSQL for metadata storage.

## Features

- **📄 PDF Documentation Ingestion**: Process manufacturer manuals (Elektron, Arturia, etc.)
- **🤖 Natural Language Queries**: Ask questions in plain English
- **🔌 Connection-Focused**: Optimized for MIDI, Audio, and Power connection queries
- **🔍 Vector Search**: Elasticsearch with semantic embeddings
- **⚡ FastAPI**: High-performance async REST API
- **🐳 Docker**: Containerized with Docker Compose

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Dawly     │────▶│  FastAPI     │────▶│ Elasticsearch│
│   Frontend  │     │  (Port 8000) │     │ (Vector DB) │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ├──────────▶ PostgreSQL
                           │           (Metadata)
                           │
                           └──────────▶ Redis
                                       (Cache)
```

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

API available at: http://localhost:8000
Docs: http://localhost:8000/docs

### Option 2: Local Development

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# Edit .env with your configuration

# 3. Start databases (Docker)
docker-compose up -d postgres elasticsearch redis

# 4. Run development server
python -m app.main
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Query Documentation
```bash
POST /api/v1/query
{
  "device_id": "digitakt-ii",
  "question": "How do I connect MIDI?",
  "max_results": 5
}
```

### Ingest PDF
```bash
POST /api/v1/ingest
Content-Type: multipart/form-data

file: digitakt-ii-manual.pdf
device_name: Digitakt II
manufacturer: Elektron
```

### List Devices
```bash
GET /api/v1/devices?manufacturer=Elektron&limit=10
```

## Configuration

See `.env.example` for all configuration options.

### Key Settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | API host | 0.0.0.0 |
| `API_PORT` | API port | 8000 |
| `POSTGRES_*` | PostgreSQL settings | localhost:5432 |
| `ELASTICSEARCH_*` | Elasticsearch settings | localhost:9200 |
| `EMBEDDING_MODEL` | Sentence transformer model | all-MiniLM-L6-v2 |

## Development

### Project Structure

```
dawly-doc-AI/
├── app/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration
│   ├── api/              # API endpoints
│   │   ├── health.py
│   │   ├── query.py
│   │   ├── ingest.py
│   │   └── devices.py
│   ├── models/           # Database models
│   └── services/         # Business logic
├── docker-compose.yml    # Docker services
├── Dockerfile           # API container
├── requirements.txt     # Python dependencies
└── .env.example        # Configuration template
```

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Format code
black app/

# Lint
flake8 app/

# Type check
mypy app/
```

## Deployment

### Docker Production

```bash
# Build image
docker build -t dawly-doc-ai:latest .

# Run with compose
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests.

## Roadmap

- [x] Basic FastAPI structure
- [x] Docker Compose setup
- [ ] PDF ingestion pipeline
- [ ] Elasticsearch integration
- [ ] Sentence embeddings
- [ ] RAG query pipeline
- [ ] Device metadata extraction
- [ ] Query history
- [ ] Authentication
- [ ] Rate limiting

## License

MIT
