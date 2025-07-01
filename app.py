#!/usr/bin/env python3
"""
DNS Records Manager - Cron Job Service
"""

import logging
import json
import os
import sys
from datetime import datetime, timezone
from src.dns_manager import DNSManager
from src.aws_client import AWSClient
from src.config import AWS_REGION, CLOUDFLARE_DOMAIN

# Configure structured logging
class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    def format(self, record):
        # Convert plain text logs to structured JSON format
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'pod_name': os.environ.get('HOSTNAME', 'unknown'),
            'namespace': os.environ.get('POD_NAMESPACE', 'unknown'),
            'deployment': os.environ.get('DEPLOYMENT_NAME', 'unknown')
        }
        
        # Add extra fields if present
        if hasattr(record, 'dns_change'):
            log_data['dns_change'] = record.dns_change
        if hasattr(record, 'summary'):
            log_data['summary'] = record.summary
        if hasattr(record, 'instances'):
            log_data['instances'] = record.instances
        if hasattr(record, 'dns_records'):
            log_data['dns_records'] = record.dns_records
        if hasattr(record, 'dns_backup_json'):
            log_data['dns_backup_json'] = record.dns_backup_json
        if hasattr(record, 'dns_backup_csv'):
            log_data['dns_backup_csv'] = record.dns_backup_csv
            
        return json.dumps(log_data)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Apply structured formatter to root logger
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.setFormatter(StructuredFormatter())

logger = logging.getLogger(__name__)

def main():
    """Main function to run the DNS reconciliation job"""
    try:
        logger.info("Starting DNS records reconciliation job")
        
        # Initialize clients
        aws_client = AWSClient()
        dns_manager = DNSManager()
        
        # Get EC2 instances and their public IPs
        logger.info("Fetching EC2 instances and their public IPs")
        instances = aws_client.get_instances_with_public_ips()
        
        # Get current DNS records
        logger.info("Fetching current DNS records from Cloudflare")
        dns_records = dns_manager.get_dns_records()
        
        # Log DNS records as backup strings
        dns_json = dns_manager.get_dns_records_as_json_string(dns_records)
        dns_csv = dns_manager.get_dns_records_as_csv_string(dns_records)
        
        logger.info("DNS records backup (JSON format):", extra={
            'dns_backup_json': dns_json
        })
        
        logger.info("DNS records backup (CSV format):", extra={
            'dns_backup_csv': dns_csv
        })
        
        # Reconcile DNS records
        logger.info("Reconciling DNS records")
        reconciliation_stats = dns_manager.reconcile_dns_records(instances, dns_records)
        
        # Log summary statistics
        logger.info("DNS reconciliation summary", extra={
            'summary': reconciliation_stats
        })
        
        if reconciliation_stats['changes_made']:
            logger.info("DNS records updated successfully")
        else:
            logger.info("No DNS record changes needed")
            
    except Exception as e:
        logger.error(f"Error during DNS reconciliation: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 