#!/bin/bash

set -e

if [ "$1" == "--build" ]; then
    echo "Building project..."
    mvn clean compile -q
    echo "Build complete."
fi

echo "Starting agent..."
mvn exec:java -q
