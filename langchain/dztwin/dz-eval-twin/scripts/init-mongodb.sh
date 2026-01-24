#!/bin/bash
# Initialize MongoDB with indexes for multi-tenancy

echo "Initializing MongoDB for Gen AI Evaluation Platform..."

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to be ready..."
until finch exec gen-ai-eval-mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; do
  echo "MongoDB is unavailable - sleeping"
  sleep 2
done

echo "MongoDB is ready!"

# Create indexes for multi-tenancy
echo "Creating indexes for tenant isolation..."

finch exec gen-ai-eval-mongodb mongosh gen_ai_eval_platform --eval '
// Create indexes for customer_id on all collections
db.applicationProfiles.createIndex({ "customer_id": 1 });
db.datasets.createIndex({ "customer_id": 1 });
db.evaluationRuns.createIndex({ "customer_id": 1 });

// Create compound indexes for common queries
db.evaluationRuns.createIndex({ "customer_id": 1, "status": 1 });
db.evaluationRuns.createIndex({ "customer_id": 1, "start_time": -1 });

// Create unique index for customer names
db.customers.createIndex({ "name": 1 }, { unique: true });

print("✅ Indexes created successfully!");
print("\nExisting indexes:");
print("\nCustomers:");
printjson(db.customers.getIndexes());
print("\nApplication Profiles:");
printjson(db.applicationProfiles.getIndexes());
print("\nDatasets:");
printjson(db.datasets.getIndexes());
print("\nEvaluation Runs:");
printjson(db.evaluationRuns.getIndexes());
'

echo ""
echo "✅ MongoDB initialization complete!"
echo "MongoDB is running on: mongodb://localhost:27017"
echo "Database: gen_ai_eval_platform"
