# Deployment Guide for Dawly Documentation AI

**Version:** 1.0.0  
**Last Updated:** 2025-10-28

---

## Production Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 20GB+ disk space
- OpenAI API key (or local LLM)

---

## Quick Deploy

### Using Docker Compose (Production)

```bash
# Clone repository
git clone https://github.com/TerryBerk/dawly-doc-AI.git
cd dawly-doc-AI

# Create production environment file
cp .env.example .env.prod

# Edit .env.prod with production values
nano .env.prod

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
```

### Services

After deployment, services available at:

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **ElasticSearch**: http://localhost:9200
- **Redis**: localhost:6379

---

## Environment Configuration

### Production .env.prod

```bash
# KAG Configuration
KAG_PROJECT_NAME=dawly_docs_prod
KAG_LANGUAGE=en
KAG_DOMAIN=music_hardware

# Database (PostgreSQL)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=dawly_kag_prod
POSTGRES_USER=kaguser
POSTGRES_PASSWORD=<strong-password-here>

# ElasticSearch
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=dawly_docs_prod

# Redis (Caching)
REDIS_HOST=redis
REDIS_PORT=6379

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=<your-openai-api-key>
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2000

# Embedding Model
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# CORS
ALLOWED_ORIGINS=https://dawly.io,https://www.dawly.io

# KAG Processing
MAX_CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_PARALLEL_PROCESSES=4

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
ENVIRONMENT=production
```

---

## Docker Configuration

### Multi-stage Build

Dockerfile uses multi-stage build for optimization:

1. **Builder stage**: Installs dependencies with gcc/g++
2. **Runtime stage**: Slim image with only runtime dependencies
3. **Non-root user**: Runs as kaguser (UID 1000)
4. **Health checks**: Built-in health monitoring

### Benefits

- Smaller image size (~500MB vs 1GB+)
- Faster builds with layer caching
- Security: non-root execution
- Health monitoring

---

## Service Configuration

### PostgreSQL

```yaml
# Persistent storage
volumes:
  - postgres_data_prod:/var/lib/postgresql/data

# Health check
pg_isready -U kaguser

# Restart policy
restart: unless-stopped
```

### ElasticSearch

```yaml
# Memory configuration
ES_JAVA_OPTS: -Xms1g -Xmx1g

# Persistent storage
volumes:
  - elasticsearch_data_prod:/usr/share/elasticsearch/data

# Ulimits for performance
ulimits:
  memlock: -1
  nofile: 65536
```

### Redis

```yaml
# AOF persistence
command: redis-server --appendonly yes

# Persistent storage
volumes:
  - redis_data_prod:/data
```

### API (FastAPI)

```yaml
# Production workers
workers: 4

# Volume mounts
- ./docs_data:/app/docs_data      # PDF storage
- ./checkpoints:/app/checkpoints  # Processing state
- ./logs:/app/logs                # Application logs

# Depends on all services
depends_on:
  - postgres (healthy)
  - elasticsearch (healthy)
  - redis (healthy)
```

---

## Deployment Steps

### 1. Initial Setup

```bash
# Create production environment
cp .env.example .env.prod

# Generate strong passwords
openssl rand -base64 32  # For POSTGRES_PASSWORD

# Edit .env.prod with:
# - Strong PostgreSQL password
# - OpenAI API key
# - Production domain for CORS
nano .env.prod
```

### 2. Deploy Services

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
docker-compose -f docker-compose.prod.yml ps
```

### 3. Verify Deployment

```bash
# Check API health
curl http://localhost:8000/health

# Check PostgreSQL
docker exec dawly-kag-db-prod psql -U kaguser -d dawly_kag_prod -c "SELECT version();"

# Check ElasticSearch
curl http://localhost:9200/_cluster/health

# Check Redis
docker exec dawly-redis-prod redis-cli ping
```

### 4. Initialize Data

```bash
# Access API container
docker exec -it dawly-doc-ai-prod bash

# Initialize database (if needed)
python -m app.db.init

# Upload initial documentation
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@Digitakt_II_Manual.pdf" \
  -F "device_name=Digitakt II" \
  -F "manufacturer=Elektron"
```

---

## Monitoring

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 api
```

### Service Status

```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Check health
docker inspect dawly-doc-ai-prod | grep -A 5 Health
```

### Resource Usage

```bash
# CPU and memory
docker stats dawly-doc-ai-prod

# Disk usage
docker system df
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale API workers
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Use load balancer (nginx) to distribute traffic
```

### Vertical Scaling

Edit docker-compose.prod.yml:

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
```

---

## Backup & Restore

### Backup PostgreSQL

```bash
# Create backup
docker exec dawly-kag-db-prod pg_dump -U kaguser dawly_kag_prod > backup_$(date +%Y%m%d).sql

# Automated daily backups
0 2 * * * docker exec dawly-kag-db-prod pg_dump -U kaguser dawly_kag_prod > /backups/dawly_$(date +\%Y\%m\%d).sql
```

### Backup ElasticSearch

```bash
# Snapshot repository
curl -X PUT "localhost:9200/_snapshot/dawly_backup" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/usr/share/elasticsearch/backups"
  }
}
'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/dawly_backup/snapshot_$(date +%Y%m%d)"
```

### Restore

```bash
# PostgreSQL
docker exec -i dawly-kag-db-prod psql -U kaguser dawly_kag_prod < backup_20251028.sql

# ElasticSearch
curl -X POST "localhost:9200/_snapshot/dawly_backup/snapshot_20251028/_restore"
```

---

## Updating

### Rolling Update

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker-compose -f docker-compose.prod.yml build api

# Restart with zero downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps api
```

### Database Migration

```bash
# Run migrations
docker exec dawly-doc-ai-prod python -m app.db.migrate

# Rollback (if needed)
docker exec dawly-doc-ai-prod python -m app.db.rollback
```

---

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Common issues:
# 1. Database not ready → wait for postgres health check
# 2. Missing env vars → check .env.prod
# 3. Port conflict → change API_PORT
```

### ElasticSearch Out of Memory

```bash
# Increase heap size in docker-compose.prod.yml
ES_JAVA_OPTS: -Xms2g -Xmx2g

# Or add more RAM to host
```

### Slow Queries

```bash
# Check ElasticSearch performance
curl http://localhost:9200/_cat/indices?v

# Optimize indices
curl -X POST "localhost:9200/dawly_docs_prod/_forcemerge?max_num_segments=1"

# Check Redis cache
docker exec dawly-redis-prod redis-cli INFO stats
```

---

## Security Checklist

- [ ] Strong PostgreSQL password
- [ ] OpenAI API key secured
- [ ] CORS origins restricted to production domains
- [ ] Non-root container user
- [ ] Secrets in .env.prod (not committed)
- [ ] Firewall rules (only necessary ports)
- [ ] HTTPS with reverse proxy (nginx/traefik)
- [ ] Regular security updates
- [ ] Log rotation configured
- [ ] Backup encryption

---

## Production Checklist

- [ ] Environment variables configured
- [ ] Volumes created and persistent
- [ ] Health checks passing
- [ ] Logs accessible
- [ ] Backups scheduled
- [ ] Monitoring configured
- [ ] Alerts set up
- [ ] Documentation reviewed
- [ ] Load testing completed
- [ ] Security audit passed

---

## Cloud Deployment

### AWS ECS

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t dawly-doc-ai .
docker tag dawly-doc-ai:latest <account>.dkr.ecr.us-east-1.amazonaws.com/dawly-doc-ai:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/dawly-doc-ai:latest

# Deploy to ECS
aws ecs update-service --cluster dawly-cluster --service dawly-doc-ai --force-new-deployment
```

### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/<project-id>/dawly-doc-ai
gcloud run deploy dawly-doc-ai --image gcr.io/<project-id>/dawly-doc-ai --platform managed
```

### Kubernetes

```yaml
# See k8s/ directory for Kubernetes manifests
kubectl apply -f k8s/
```

---

## Support

- **Issues**: https://github.com/TerryBerk/dawly-doc-AI/issues
- **Documentation**: /docs
- **Health endpoint**: /health

---

**Dawly Documentation AI** - Production Ready 🚀
