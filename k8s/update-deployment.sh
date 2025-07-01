#!/bin/bash

set -e

LATEST_TAG=$1

if [ -z "$LATEST_TAG" ]; then
  echo "Usage: $0 <latest-tag>"
  exit 1
fi

echo "Updating dev-instance-dns-sync cronjob to image tag: $LATEST_TAG"

# Update the cronjob with new image
kubectl -n dev-instance-dns-sync set image cronjob/dev-instance-dns-sync dev-instance-dns-sync=cr.aops.tools/aops-docker-repo/dev-instance-dns-sync:$LATEST_TAG

# Verify the image was updated
echo "Verifying cronjob image update..."
kubectl -n dev-instance-dns-sync get cronjob dev-instance-dns-sync -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'

echo -e "\nCronJob successfully updated!"

# Optional: Display the cronjob status and recent jobs
echo -e "\nCronJob status:"
kubectl -n dev-instance-dns-sync get cronjob dev-instance-dns-sync

echo -e "\nRecent jobs:"
kubectl -n dev-instance-dns-sync get jobs -l app=dev-instance-dns-sync --sort-by=.metadata.creationTimestamp | tail -5 