# MongoDB 8 Setup Guide

## Overview

This project uses MongoDB 8 Community Edition running in a Finch container for data persistence with complete multi-tenant isolation.

## Quick Start

### Start MongoDB

```bash
# Start MongoDB 8 using Finch
finch compose up -d

# Verify MongoDB is running
finch ps | grep mongo

# Check MongoDB version
finch exec gen-ai-eval-mongodb mongosh --eval "db.version()"
```

### Initialize Database

```bash
# Create indexes for multi-tenancy
./scripts/init-mongodb.sh
```

### Stop MongoDB

```bash
# Stop MongoDB container
finch compose down

# Stop and remove volumes (WARNING: deletes all data)
finch compose down -v
```

## Configuration

### Connection Details

- **Host**: localhost
- **Port**: 27017
- **Database**: gen_ai_eval_platform
- **Connection String**: `mongodb://localhost:27017`

### Environment Variables

Set these in `backend/.env`:

```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=gen_ai_eval_platform
```

## Multi-Tenancy Indexes

The following indexes are automatically created for tenant isolation:

### Customer Collection
- `name` (unique) - Ensures unique customer names

### Application Profiles Collection
- `customer_id` - Tenant isolation

### Datasets Collection
- `customer_id` - Tenant isolation

### Evaluation Runs Collection
- `customer_id` - Tenant isolation
- `customer_id + status` - Filtered queries by status
- `customer_id + start_time` (descending) - Recent runs first

## Database Operations

### Access MongoDB Shell

```bash
finch exec -it gen-ai-eval-mongodb mongosh gen_ai_eval_platform
```

### View Collections

```javascript
// List all collections
show collections

// Count documents in a collection
db.customers.countDocuments()
db.datasets.countDocuments()
db.evaluationRuns.countDocuments()
```

### Query Data (with tenant isolation)

```javascript
// Find all datasets for a customer
db.datasets.find({ customer_id: "cust_123" })

// Find recent evaluation runs for a customer
db.evaluationRuns.find({ customer_id: "cust_123" }).sort({ start_time: -1 }).limit(10)

// Verify tenant isolation
db.datasets.find({ customer_id: "cust_123" }).count()
db.datasets.find({ customer_id: "cust_456" }).count()
```

### Backup and Restore

```bash
# Backup database
finch exec gen-ai-eval-mongodb mongodump --db=gen_ai_eval_platform --out=/tmp/backup

# Restore database
finch exec gen-ai-eval-mongodb mongorestore --db=gen_ai_eval_platform /tmp/backup/gen_ai_eval_platform
```

## Troubleshooting

### MongoDB won't start

```bash
# Check logs
finch logs gen-ai-eval-mongodb

# Restart container
finch compose restart mongodb
```

### Connection refused

```bash
# Verify MongoDB is listening
finch exec gen-ai-eval-mongodb mongosh --eval "db.adminCommand('ping')"

# Check port mapping
finch port gen-ai-eval-mongodb 27017
```

### Reset database

```bash
# Stop and remove everything
finch compose down -v

# Start fresh
finch compose up -d
./scripts/init-mongodb.sh
```

## Performance Tuning

### Monitor Performance

```javascript
// Check index usage
db.datasets.aggregate([{ $indexStats: {} }])

// View slow queries
db.setProfilingLevel(1, { slowms: 100 })
db.system.profile.find().sort({ ts: -1 }).limit(5)
```

### Optimize Queries

All queries automatically use the `customer_id` indexes for efficient tenant isolation. The compound indexes on `evaluationRuns` optimize common query patterns:

- Filtering by status: `customer_id + status`
- Sorting by time: `customer_id + start_time`

## Security Notes

- MongoDB is running without authentication (development only)
- For production, enable authentication and use strong credentials
- Ensure firewall rules restrict access to MongoDB port
- Use TLS/SSL for encrypted connections in production

## Resources

- [MongoDB 8 Documentation](https://www.mongodb.com/docs/v8.0/)
- [Finch Documentation](https://runfinch.com/)
- [Multi-Tenancy Best Practices](https://www.mongodb.com/docs/manual/core/security-multi-tenancy/)
