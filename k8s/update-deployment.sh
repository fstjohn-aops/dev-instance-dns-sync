#!/bin/bash

set -e

# --- Configuration ---
REGISTRY="cr.aops.tools/aops-docker-repo"
IMAGE_NAME="dev-instance-dns-sync"
K8S_NAMESPACE="dev-instance-dns-sync"
K8S_RESOURCE_TYPE="cronjob"
K8S_RESOURCE_NAME="dev-instance-dns-sync"
K8S_CONTAINER_NAME="dev-instance-dns-sync"
# ---------------------

LATEST_TAG=$1

if [ -z "$LATEST_TAG" ]; then
  echo "Usage: $0 <latest-tag>"
  exit 1
fi

echo "Updating $K8S_RESOURCE_NAME $K8S_RESOURCE_TYPE to image tag: $LATEST_TAG"

# Update the resource with the new image
kubectl -n $K8S_NAMESPACE \
  set image ${K8S_RESOURCE_TYPE}/${K8S_RESOURCE_NAME} \
  ${K8S_CONTAINER_NAME}=${REGISTRY}/${IMAGE_NAME}:${LATEST_TAG}

# Verify the image was updated
echo "Verifying resource image update..."
kubectl -n $K8S_NAMESPACE get $K8S_RESOURCE_TYPE $K8S_RESOURCE_NAME -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'

echo -e "\nResource successfully updated!"

# Optional: Display the resource status and recent jobs
echo -e "\nResource status:"
kubectl -n $K8S_NAMESPACE get $K8S_RESOURCE_TYPE $K8S_RESOURCE_NAME

echo -e "\nRecent jobs:"
kubectl -n $K8S_NAMESPACE get jobs -l app=$K8S_RESOURCE_NAME --sort-by=.metadata.creationTimestamp | tail -5 