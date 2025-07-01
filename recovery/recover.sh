#!/bin/bash

# DNS Records Recovery Script Entry Point

set -e

# Check if input file is provided
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <input_file> [--dry-run] [--verify]"
    echo ""
    echo "Input file can be:"
    echo "  - JSON file with DNS records backup"
    echo "  - CSV file with DNS records"
    echo ""
    echo "Options:"
    echo "  --dry-run   Show what would be done without making changes"
    echo "  --verify    Verify records after restoration"
    exit 1
fi

# Check if CLOUDFLARE_API_TOKEN is set
if [[ -z "$CLOUDFLARE_API_TOKEN" ]]; then
    echo "Error: CLOUDFLARE_API_TOKEN environment variable is required"
    echo "Please set it with: export CLOUDFLARE_API_TOKEN='your-token-here'"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the Python recovery script
python3 "$SCRIPT_DIR/recovery_script.py" "$@" 