# Qdrant Setup Quick Reference

Quick commands for installing and managing Qdrant vector database.

---

## 🚀 Quick Start

### Using Finch (macOS - Recommended)

```bash
# 1. Install Finch
brew install finch

# 2. Initialize Finch VM (first time only)
finch vm init

# 3. Start Qdrant
finch run -d -p 6333:6333 -p 6334:6334 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant

# 4. Verify it's running
finch ps
curl http://localhost:6333/

# 5. Test connection
python test_qdrant.py
```

### Using Docker

```bash
# 1. Start Qdrant
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant

# 2. Verify it's running
docker ps
curl http://localhost:6333/

# 3. Test connection
python test_qdrant.py
```

---

## 📋 Common Commands

### Finch Commands

```bash
# Check status
finch ps

# Start Qdrant (if stopped)
finch start qdrant

# Stop Qdrant
finch stop qdrant

# Restart Qdrant
finch restart qdrant

# View logs
finch logs qdrant
finch logs -f qdrant  # Follow logs in real-time

# Remove container (keeps data)
finch stop qdrant
finch rm qdrant

# Remove container AND data
finch stop qdrant
finch rm qdrant
finch volume rm qdrant_storage

# Check Finch VM status
finch vm status

# Restart Finch VM
finch vm stop
finch vm start
```

### Docker Commands

```bash
# Check status
docker ps

# Start Qdrant (if stopped)
docker start qdrant

# Stop Qdrant
docker stop qdrant

# Restart Qdrant
docker restart qdrant

# View logs
docker logs qdrant
docker logs -f qdrant  # Follow logs in real-time

# Remove container (keeps data)
docker stop qdrant
docker rm qdrant

# Remove container AND data
docker stop qdrant
docker rm qdrant
docker volume rm qdrant_storage
```

---

## 🔍 Verification Commands

### Check if Qdrant is Running

```bash
# Method 1: Check container
finch ps | grep qdrant
# or
docker ps | grep qdrant

# Method 2: Test HTTP API
curl http://localhost:6333/

# Method 3: Open dashboard in browser
open http://localhost:6333/dashboard  # macOS
# or visit http://localhost:6333/dashboard in browser

# Method 4: Python test
python test_qdrant.py

# Method 5: Quick Python check
python -c "from qdrant_client import QdrantClient; print('✓ Connected!' if QdrantClient(url='http://localhost:6333').get_collections() else '✗ Failed')"
```

### Check Collections

```bash
# List all collections
python -c "
from qdrant_client import QdrantClient
client = QdrantClient(url='http://localhost:6333')
collections = client.get_collections()
print('Collections:', [c.name for c in collections.collections])
"

# Get collection info
python -c "
from qdrant_client import QdrantClient
client = QdrantClient(url='http://localhost:6333')
info = client.get_collection('api_docs')
print(f'Vectors: {info.vectors_count}')
print(f'Points: {info.points_count}')
"
```

### Check Ports

```bash
# Check if port 6333 is in use
lsof -i :6333

# Check which ports Qdrant is using
finch port qdrant
# or
docker port qdrant
```

---

## 🛠️ Troubleshooting

### Problem: Port Already in Use

```bash
# Find what's using port 6333
lsof -i :6333

# Kill the process
kill -9 <PID>

# Or use a different port
finch run -d -p 6335:6333 --name qdrant qdrant/qdrant

# Update .env
QDRANT_URL=http://localhost:6335
```

### Problem: Container Won't Start

```bash
# Check logs for errors
finch logs qdrant
# or
docker logs qdrant

# Remove and recreate container
finch stop qdrant
finch rm qdrant
finch run -d -p 6333:6333 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

### Problem: Connection Refused

```bash
# 1. Check if container is running
finch ps

# 2. Check if port is exposed
finch port qdrant

# 3. Test connection
curl http://localhost:6333/

# 4. Check Finch VM (macOS)
finch vm status

# 5. Restart Finch VM if needed
finch vm stop
finch vm start
```

### Problem: Finch VM Issues (macOS)

```bash
# Check VM status
finch vm status

# Restart VM
finch vm stop
finch vm start

# Recreate VM (if corrupted)
finch vm remove
finch vm init
```

### Problem: Data Not Persisting

```bash
# Check if volume exists
finch volume ls | grep qdrant_storage

# Inspect volume
finch volume inspect qdrant_storage

# Recreate with volume
finch stop qdrant
finch rm qdrant
finch run -d -p 6333:6333 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

---

## 💾 Data Management

### Backup Qdrant Data

```bash
# Using Finch
finch run --rm \
  -v qdrant_storage:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/qdrant_backup.tar.gz /data

# Using Docker
docker run --rm \
  -v qdrant_storage:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/qdrant_backup.tar.gz /data
```

### Restore Qdrant Data

```bash
# Stop Qdrant
finch stop qdrant
finch rm qdrant

# Remove old volume
finch volume rm qdrant_storage

# Create new volume
finch volume create qdrant_storage

# Restore data
finch run --rm \
  -v qdrant_storage:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/qdrant_backup.tar.gz -C /

# Start Qdrant
finch run -d -p 6333:6333 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

### Clear All Data

```bash
# Stop and remove container
finch stop qdrant
finch rm qdrant

# Remove volume (deletes all data)
finch volume rm qdrant_storage

# Start fresh
finch run -d -p 6333:6333 --name qdrant -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

---

## ⚙️ Configuration

### Custom Configuration

```bash
# Run with custom settings
finch run -d \
  -p 6333:6333 \
  --name qdrant \
  -v qdrant_storage:/qdrant/storage \
  -e QDRANT__LOG_LEVEL=INFO \
  -e QDRANT__SERVICE__MAX_REQUEST_SIZE_MB=64 \
  qdrant/qdrant
```

### Resource Limits

```bash
# Limit memory and CPU
finch run -d \
  -p 6333:6333 \
  --name qdrant \
  -v qdrant_storage:/qdrant/storage \
  --memory="4g" \
  --cpus="2" \
  qdrant/qdrant
```

---

## 🔗 Integration with Ingester

### Configure .env

```env
# Server mode (recommended)
QDRANT_USE_EMBEDDED=false
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=api_docs
```

### Test Integration

```bash
# 1. Test Qdrant connection
python test_qdrant.py

# 2. Run ingestion
python ingest.py

# 3. Test search
python search.py "your query"
```

---

## 📊 Monitoring

### Check Resource Usage

```bash
# Container stats
finch stats qdrant
# or
docker stats qdrant

# Disk usage
finch system df
# or
docker system df
```

### View Dashboard

```bash
# Open Qdrant dashboard
open http://localhost:6333/dashboard

# Or visit in browser:
# http://localhost:6333/dashboard
```

### API Endpoints

```bash
# Health check
curl http://localhost:6333/

# Collections
curl http://localhost:6333/collections

# Collection info
curl http://localhost:6333/collections/api_docs

# Cluster info
curl http://localhost:6333/cluster
```

---

## 🚀 Production Setup

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    restart: unless-stopped
    environment:
      - QDRANT__LOG_LEVEL=INFO
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'

volumes:
  qdrant_storage:
    driver: local
```

Commands:

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f qdrant

# Restart
docker-compose restart
```

### Production Recommendations

1. **Use persistent volumes** - Always mount `/qdrant/storage`
2. **Set resource limits** - Prevent memory/CPU issues
3. **Enable monitoring** - Track performance metrics
4. **Regular backups** - Backup volume data
5. **Use API keys** - Secure your Qdrant instance
6. **Health checks** - Monitor container health
7. **Log rotation** - Prevent disk space issues

---

## 📚 Additional Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant GitHub](https://github.com/qdrant/qdrant)
- [Finch Documentation](https://runfinch.com/)
- [Docker Documentation](https://docs.docker.com/)

---

## ✅ Quick Checklist

Before running ingester:

- [ ] Qdrant container is running (`finch ps` or `docker ps`)
- [ ] Port 6333 is accessible (`curl http://localhost:6333/`)
- [ ] Dashboard loads (`http://localhost:6333/dashboard`)
- [ ] Python test passes (`python test_qdrant.py`)
- [ ] `.env` configured with `QDRANT_URL=http://localhost:6333`
- [ ] Volume is mounted for data persistence

---

## 🆘 Getting Help

If you're still having issues:

1. Check Qdrant logs: `finch logs qdrant` or `docker logs qdrant`
2. Verify network connectivity: `curl http://localhost:6333/`
3. Check Finch VM status: `finch vm status` (macOS)
4. Restart everything: Stop container, restart VM, start container
5. Check [Qdrant GitHub Issues](https://github.com/qdrant/qdrant/issues)
6. Check [Finch GitHub Issues](https://github.com/runfinch/finch/issues)
