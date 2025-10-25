# Service Verification Commands

## Quick Status Check

```bash
# Show all running containers
docker ps

# Show all containers (including stopped)
docker ps -a

# Check via Makefile
make status
```

## Individual Service Tests

### 1. PostgreSQL
```bash
# Check if running
docker exec -it ai-systems-postgres pg_isready -U postgres

# Connect to database
make shell-postgres
# or
docker exec -it ai-systems-postgres psql -U postgres -d ai_systems

# Check version
docker exec -it ai-systems-postgres psql -U postgres -c "SELECT version();"
```

### 2. Weaviate
```bash
# Check health
curl http://localhost:8080/v1/.well-known/ready

# Check liveness
curl http://localhost:8080/v1/.well-known/live

# Get metadata
curl http://localhost:8080/v1/meta
```

### 3. Redis
```bash
# Ping Redis
docker exec -it ai-systems-redis redis-cli ping

# Connect to Redis CLI
make shell-redis
# or
docker exec -it ai-systems-redis redis-cli

# Get info
docker exec -it ai-systems-redis redis-cli INFO
```

### 4. MinIO
```bash
# Check health
curl http://localhost:9000/minio/health/live

# Open web console
open http://localhost:9001
# Login: minioadmin / minioadmin
```

### 5. Ollama
```bash
# Check if running
curl http://localhost:11434

# List downloaded models
docker exec -it ai-systems-ollama ollama list
# or
make ollama-list

# Test with a prompt (after pulling model)
docker exec -it ai-systems-ollama ollama run llama3.1:8b "Hello, who are you?"
```

## Service Logs

```bash
# All services
make logs

# Specific service
docker logs ai-systems-postgres
docker logs ai-systems-weaviate
docker logs ai-systems-redis
docker logs ai-systems-minio
docker logs ai-systems-ollama

# Follow logs (real-time)
docker logs -f ai-systems-ollama

# Last 50 lines
docker logs --tail 50 ai-systems-postgres
```

## Service Management

```bash
# Stop all services
make down

# Stop and remove all data
make clean

# Restart a specific service
docker restart ai-systems-postgres

# Restart all services
make down && make dev
```

## Port Verification

```bash
# Check what's listening on ports
lsof -i :5432  # PostgreSQL
lsof -i :8080  # Weaviate
lsof -i :6379  # Redis
lsof -i :9000  # MinIO API
lsof -i :9001  # MinIO Console
lsof -i :11434 # Ollama
```

## Health Check Summary

```bash
# Run all health checks at once
echo "=== PostgreSQL ==="
docker exec -it ai-systems-postgres pg_isready -U postgres

echo "=== Redis ==="
docker exec -it ai-systems-redis redis-cli ping

echo "=== Weaviate ==="
curl -s http://localhost:8080/v1/.well-known/ready | head -5

echo "=== MinIO ==="
curl -s http://localhost:9000/minio/health/live

echo "=== Ollama ==="
curl -s http://localhost:11434 | head -5
```

## URLs

```bash
# View all service URLs
make URLs
```

Output:
```
Frontend:      http://localhost:3000
Backend API:   http://localhost:8000
API Docs:      http://localhost:8000/docs
Ollama (LLM):  http://localhost:11434
Weaviate:      http://localhost:8080
MinIO Console: http://localhost:9001 (admin/minioadmin)
Grafana:       http://localhost:3001 (admin/admin)
Prometheus:    http://localhost:9090
```

## Troubleshooting

### Service won't start
```bash
# Check logs
docker logs ai-systems-<service-name>

# Check if port is already in use
lsof -i :<port>

# Remove and restart
docker rm -f ai-systems-<service-name>
make down && make dev
```

### Out of disk space
```bash
# Check Docker disk usage
docker system df

# Clean up unused data
docker system prune

# Clean up everything (CAREFUL - removes all data)
docker system prune -a --volumes
```

### Ollama model download stuck
```bash
# Check logs
docker logs -f ai-systems-ollama

# Cancel and restart
make down
make dev
make ollama-pull
```
