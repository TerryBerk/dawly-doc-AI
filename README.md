# Dawly Documentation AI

Knowledge-Augmented Generation (KAG) system for music hardware documentation.

## Overview

Intelligent documentation retrieval for music hardware devices using OpenSPG KAG framework, providing accurate answers to technical questions about device connections, specifications, and setup procedures.

## Features

- **PDF Documentation Ingestion**: Process manufacturer manuals (Elektron, Arturia, etc.)
- **Natural Language Queries**: Ask questions in plain English
- **Connection-Focused**: Optimized for MIDI, Audio, and Power connection queries
- **Knowledge Graph**: Structured device specifications and relationships
- **REST API**: Integration with Dawly platform

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env

# Run development server
python -m app.main
```

## Documentation

See [docs/](docs/) for detailed documentation.

## Development

This project follows GitFlow workflow:
- `main` - production-ready code
- `develop` - integration branch
- `feature/*` - feature branches
- `hotfix/*` - production fixes

## License

MIT
