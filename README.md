# Dev Instance DNS Records Manager

A Kubernetes CronJob service that automatically manages DNS A records in Cloudflare for EC2 instances. This service runs every 5 minutes to reconcile DNS records with the current public IPs of EC2 instances.

## Overview

This service addresses the issue where EC2 instances get new public IPs when they are stopped and started, which invalidates existing DNS A records. The service:

1. Fetches all EC2 instances and their public IPs from AWS
2. Retrieves current DNS A records from Cloudflare
3. Compares and reconciles any discrepancies
4. **Updates existing DNS records only** - never creates or deletes records

## Safety Features

**This application will NEVER create or delete DNS records under any circumstances.** It only updates existing DNS records when IP addresses change. This is a deliberate safety measure to prevent accidental data loss.

- ✅ **Updates** existing DNS records when IPs change
- ❌ **Never creates** new DNS records
- ❌ **Never deletes** any DNS records

## Key Assumptions

- Only manages DNS records under the domain `aopstest.com`
- Only manages records where the hostname matches the EC2 instance name (format: `<instance-name>.aopstest.com`)
- Operates in a single AWS region and account (same as the EC2 instances)
- Uses Cloudflare for DNS management
- **Only updates existing DNS records** - instances without DNS records are skipped

## Prerequisites

- AWS EKS cluster with pod identity configured
- Cloudflare API token with DNS management permissions
- EC2 instances tagged with `Name` tags
- **Existing DNS A records** for the instances you want to manage

## Setup

### 1. Environment Setup

```bash
# Set up virtual environment
./setup-venv.sh

# Activate virtual environment
source venv/bin/activate
```

### 2. Cloudflare API Token

You need a Cloudflare API token with the following permissions:
- Zone:Read for the `aopstest.com` zone
- DNS:Edit for the `aopstest.com` zone

### 3. Kubernetes Deployment

1. Update the Cloudflare API token in the secret:
   ```bash
   # Base64 encode your token
   echo -n "your-cloudflare-api-token" | base64
   ```

2. Update `k8s/04-secret.yml` with the base64-encoded token

3. Apply the Kubernetes manifests:
   ```bash
   kubectl apply -f k8s/
   ```

4. Apply the EKS pod identity association:
   ```bash
   eksctl apply -f eks/
   ```

### 4. Build and Deploy

```bash
# Build and push the Docker image
./push-image.sh v1.0.0
```

## Configuration

### Environment Variables

- `AWS_REGION`: AWS region (default: us-west-2)
- `CLOUDFLARE_API_TOKEN`: Cloudflare API token (required)
- `LOG_LEVEL`: Logging level (default: INFO)

### DNS Record Settings

- TTL: 60 seconds (1 minute)
- Proxied: False (DNS only, not proxied through Cloudflare)

## Development

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
./test.sh
```

### Local Development

```bash
# Set environment variables
export CLOUDFLARE_API_TOKEN="your-token"
export AWS_REGION="us-west-2"

# Run the application
python app.py
```

## Monitoring

The service logs all operations in structured JSON format. Key log events:

- Instance discovery and IP mapping
- DNS record updates (only)
- Reconciliation summary
- Instances without DNS records (skipped)

## Troubleshooting

### Common Issues

1. **Missing Cloudflare API Token**: Ensure the `CLOUDFLARE_API_TOKEN` environment variable is set
2. **AWS Permissions**: Verify the pod identity has `ec2:DescribeInstances` and `ec2:DescribeTags` permissions
3. **Cloudflare Permissions**: Ensure the API token has DNS management permissions for the zone
4. **No DNS Records Created**: The application only updates existing records - you must manually create DNS records first

### Checking CronJob Status

```bash
# Check cronjob status
kubectl get cronjobs -n dev-instance-dns-records-manager

# Check recent jobs
kubectl get jobs -n dev-instance-dns-records-manager

# Check job logs
kubectl logs -n dev-instance-dns-records-manager job/dev-instance-dns-records-manager-<timestamp>
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Kubernetes    │    │       AWS       │    │    Cloudflare   │
│   CronJob       │    │      EC2        │    │       DNS       │
│                 │    │                 │    │                 │
│ Runs every      │───▶│ Describe        │    │ Update A        │
│ 5 minutes       │    │ Instances       │    │ Records Only    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Security

- Runs as non-root user (UID 10001)
- Uses pod identity for AWS authentication
- Minimal required permissions
- No ingress (outgoing requests only)
- **Update-only operations** prevent accidental data loss 