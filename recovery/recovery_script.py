#!/usr/bin/env python3
"""
DNS Records Recovery Script
"""

import sys
import os
import json
import csv
import logging
from typing import List, Dict

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import CLOUDFLARE_DOMAIN
from recovery.cloudflare_client import CloudflareClient
from recovery.record_parser import RecordParser
from recovery.record_restorer import RecordRestorer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    if len(sys.argv) < 2:
        print("Usage: recovery_script.py <input_file> [--dry-run] [--verify]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    verify = '--verify' in sys.argv
    
    try:
        # Initialize components
        cloudflare_client = CloudflareClient()
        record_parser = RecordParser()
        record_restorer = RecordRestorer(cloudflare_client)
        
        # Parse input file
        logger.info(f"Reading records from: {input_file}")
        records = record_parser.parse_file(input_file)
        logger.info(f"Found {len(records)} records to restore")
        
        # Get existing records
        existing_records = cloudflare_client.get_existing_records()
        logger.info(f"Found {len(existing_records)} existing records")
        
        # Restore records
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        
        results = record_restorer.restore_records(records, existing_records, dry_run)
        logger.info(f"Restoration complete: {results['created']} created, {results['updated']} updated, {results['unchanged']} unchanged")
        
        # Verify if requested
        if verify and not dry_run:
            logger.info("Verifying restored records...")
            verification_results = record_restorer.verify_records(records)
            
            if verification_results['missing'] > 0 or verification_results['incorrect'] > 0:
                logger.warning(f"Verification found issues: {verification_results['missing']} missing, {verification_results['incorrect']} incorrect")
                sys.exit(1)
            else:
                logger.info("All records verified successfully!")
        
    except Exception as e:
        logger.error(f"Recovery failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 