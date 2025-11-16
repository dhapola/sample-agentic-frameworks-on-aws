#!/bin/bash

# Source .env file (relative path)
ENV_FILE="./.env"

# Check if source .env file exists
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: Source .env file not found at $ENV_FILE"
  exit 1
fi

# Find all studio directories and copy the .env file to each
find . -type d -name "studio" | while read studio_dir; do
  echo "Copying .env to $studio_dir"
  cp "$ENV_FILE" "$studio_dir/.env"
done

echo "Done! .env file has been copied to all studio directories."