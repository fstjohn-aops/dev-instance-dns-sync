# Dev Instance DNS Records Manager

A Kubernetes CronJob service that automatically manages DNS A records in Cloudflare for EC2 instances. This service runs every 5 minutes to reconcile DNS records with the current public IPs of EC2 instances.

## Overview

This service addresses the issue where EC2 instances get new public IPs when they are stopped and started, which invalidates existing DNS A records. The service:

1. Fetches all EC2 instances and their public IPs from AWS
2. Retrieves current DNS A records from Cloudflare
3. Compares and reconciles any discrepancies
4. **Updates existing DNS records only** - never creates or deletes records
5. **Automatically backs up DNS records** as JSON and CSV strings in logs

## Safety Features

**This application will NEVER create or delete DNS records under any circumstances.** It only updates existing DNS records when IP addresses change. This is a deliberate safety measure to prevent accidental data loss.

- ✅ **Updates** existing DNS records when IPs change
- ✅ **Automatic backup** of DNS records in logs
- ✅ **Recovery system** for disaster scenarios
- ❌ **Never creates** new DNS records
- ❌ **Never deletes** any DNS records

## Key Assumptions

- Only manages DNS records under the domain `aopstest.com`
- Only manages records where the hostname matches the EC2 instance name (format: `<instance-name>.aopstest.com`)
- **Only processes EC2 instances tagged with `EC2ControlsEnabled: true`**
- **Handles `-server` suffix in instance names** (removes suffix for DNS lookup)
- Operates in a single AWS region and account (same as the EC2 instances)
- Uses Cloudflare for DNS management
- **Only updates existing DNS records** - instances without DNS records are skipped

## Prerequisites

- AWS EKS cluster with pod identity configured
- Cloudflare API token with DNS management permissions
- EC2 instances tagged with `Name` tags and `EC2ControlsEnabled: true`
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
- Tags: Include metadata about when and how records are updated

### Instance Filtering

The service only processes EC2 instances that meet these criteria:
- Instance state: `running`
- Tag: `EC2ControlsEnabled: true`
- Has a `Name` tag
- Has a public IP address

### Instance Name to DNS Record Mapping

- Instance names are mapped directly to DNS records: `<instance-name>.aopstest.com`
- If an instance name ends with `-server`, the suffix is removed for DNS lookup
- Example: Instance `web-server` maps to DNS record `web.aopstest.com`

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
- **Automatic DNS record backups** (JSON and CSV formats)

### Log Structure

Logs include structured data with:
- Timestamp in UTC
- Pod name and namespace
- Instance details
- DNS record changes
- Backup data in JSON and CSV formats

## Disaster Recovery

The service includes a comprehensive disaster recovery system:

### Automatic Backup
- DNS records are automatically backed up as JSON and CSV strings in logs
- Backups are created on every run for complete audit trail

### Manual Recovery
Use the recovery system to restore DNS records from backups:

```bash
# Set your Cloudflare API token
export CLOUDFLARE_API_TOKEN='your-token-here'

# Test what would be done (dry run)
./recovery/recover.sh backup.json --dry-run

# Actually restore the records
./recovery/recover.sh backup.json

# Restore and verify
./recovery/recover.sh backup.json --verify
```

See `recovery/README.md` for detailed recovery instructions.

## Troubleshooting

### Common Issues

1. **Missing Cloudflare API Token**: Ensure the `CLOUDFLARE_API_TOKEN` environment variable is set
2. **AWS Permissions**: Verify the pod identity has `ec2:DescribeInstances` and `ec2:DescribeTags` permissions
3. **Cloudflare Permissions**: Ensure the API token has DNS management permissions for the zone
4. **No DNS Records Created**: The application only updates existing records - you must manually create DNS records first
5. **Instances Not Found**: Ensure instances are tagged with `EC2ControlsEnabled: true` and have `Name` tags

### Checking CronJob Status

```bash
# Check cronjob status
kubectl get cronjobs -n dev-instance-dns-sync

# Check recent jobs
kubectl get jobs -n dev-instance-dns-sync

# Check job logs
kubectl logs -n dev-instance-dns-sync job/dev-instance-dns-sync-<timestamp>
```

### Checking Instance Filtering

```bash
# Check if instances have the required tag
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].[InstanceId,Tags[?Key==`Name`].Value|[0],Tags[?Key==`EC2ControlsEnabled`].Value|[0]]' \
  --output table
```

## Security

- Runs as non-root user (UID 10001)
- Uses pod identity for AWS authentication
- Minimal required permissions
- No ingress (outgoing requests only)
- **Update-only operations** prevent accidental data loss
- **Automatic backup** ensures data can be recovered
- **Structured logging** for audit trail

## Image Registry

The service uses the `cr.aops.tools/aops-docker-repo` registry:
- Image: `cr.aops.tools/aops-docker-repo/dev-instance-dns-sync:latest`
- Built for `linux/amd64` platform for EKS compatibility 