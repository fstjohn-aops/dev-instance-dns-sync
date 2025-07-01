# DNS Records Recovery System

Simple disaster recovery system for DNS records.

## How it works

1. **Automatic Backup**: The main app logs DNS records as JSON and CSV strings in the logs
2. **Manual Recovery**: Copy the backup string to a file and run the recovery script

## Usage

### 1. Get Backup Data

When the main app runs, it logs DNS records in two formats:

**JSON Format** (recommended):
```json
{
  "timestamp": "2023-12-01T14:30:22Z",
  "domain": "aopstest.com",
  "total_records": 132,
  "records": [
    {
      "hostname": "example.aopstest.com",
      "ip_address": "192.168.1.100",
      "record_id": "abc123",
      "type": "A",
      "ttl": 60,
      "proxied": false
    }
  ]
}
```

**CSV Format**:
```csv
hostname,ip_address,record_id,type,ttl,proxied
example.aopstest.com,192.168.1.100,abc123,A,60,false
```

### 2. Create Recovery File

Copy the backup string from the logs and save it to a file:

```bash
# For JSON backup
echo '{"timestamp":"2023-12-01T14:30:22Z",...}' > backup.json

# For CSV backup
echo 'hostname,ip_address,record_id,type,ttl,proxied
example.aopstest.com,192.168.1.100,abc123,A,60,false' > backup.csv
```

### 3. Run Recovery

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

## Options

- `--dry-run`: Show what would be done without making changes
- `--verify`: Verify all records after restoration

## Files

- `recover.sh`: Simple shell script entry point
- `recovery_script.py`: Main recovery script
- `cloudflare_client.py`: Cloudflare API operations
- `record_parser.py`: Parse JSON/CSV input files
- `record_restorer.py`: Restore and verify records 