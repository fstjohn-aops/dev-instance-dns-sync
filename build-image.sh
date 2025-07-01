#!/bin/bash

# Check if tag parameter is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <tag>"
    echo "Example: $0 v1.0.0"
    exit 1
fi

TAG=$1

# Build x86_64 image for EKS compatibility
podman build --platform linux/amd64 -t dev-instance-dns-sync:latest .

# Tag with provided tag
podman tag dev-instance-dns-sync:latest dev-instance-dns-sync:$TAG

# Show built images
echo "Built images:"
podman images dev-instance-dns-sync 