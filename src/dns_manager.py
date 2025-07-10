"""
DNS Manager for Cloudflare DNS operations

SAFETY NOTICE: This application will NEVER delete DNS records under any circumstances.
Only updates to existing records are performed. This is a deliberate safety measure
to prevent accidental data loss.
"""

import os
import logging
import csv
from typing import Dict
from datetime import datetime, timezone
import CloudFlare
from src.config import CLOUDFLARE_DOMAIN

logger = logging.getLogger(__name__)

class DNSManager:
    """DNS manager for Cloudflare operations"""
    
    def __init__(self):
        """Initialize Cloudflare client"""
        # Get Cloudflare API token from environment
        self.api_token = os.environ.get('CLOUDFLARE_API_TOKEN')
        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN environment variable is required")
        
        self.cf = CloudFlare.CloudFlare(token=self.api_token)
        self.zone_id = self._get_zone_id()
        logger.info(f"Initialized Cloudflare client for domain: {CLOUDFLARE_DOMAIN}")
    
    def _get_zone_id(self) -> str:
        """
        Get Cloudflare zone ID for the domain
        
        Returns:
            Zone ID string
        """
        try:
            zones = self.cf.zones.get(params={'name': CLOUDFLARE_DOMAIN})
            if not zones:
                raise ValueError(f"Zone not found for domain: {CLOUDFLARE_DOMAIN}")
            
            zone_id = zones[0]['id']
            logger.info(f"Found zone ID: {zone_id} for domain: {CLOUDFLARE_DOMAIN}")
            return zone_id
            
        except Exception as e:
            logger.error(f"Error getting zone ID: {str(e)}")
            raise
    
    def get_dns_records(self) -> Dict[str, Dict]:
        """
        Get all A records from Cloudflare with pagination support
        
        Returns:
            Dict mapping hostname to DNS record data
        """
        try:
            dns_records = {}
            page = 1
            per_page = 100  # Cloudflare's default page size
            
            while True:
                logger.info(f"Fetching DNS records page {page}...")
                
                # Get A records for current page
                records = self.cf.zones.dns_records.get(
                    self.zone_id,
                    params={
                        'type': 'A',
                        'page': page,
                        'per_page': per_page
                    }
                )
                
                # If no records returned, we've reached the end
                if not records:
                    break
                
                for record in records:
                    hostname = record['name']
                    # Only include records for our domain
                    if hostname.endswith(f'.{CLOUDFLARE_DOMAIN}'):
                        dns_records[hostname] = {
                            'id': record['id'],
                            'content': record['content'],  # IP address
                            'name': record['name'],
                            'type': record['type']
                        }
                
                # If we got fewer records than per_page, we've reached the end
                if len(records) < per_page:
                    break
                
                page += 1
            
            logger.info(f"Found {len(dns_records)} DNS A records across {page} pages")
            
            # Log all DNS records found
            dns_records_array = [{"name": hostname, "ip": record['content']} for hostname, record in dns_records.items()]
            logger.info("DNS records found", extra={
                'dns_records': dns_records_array
            })
            
            return dns_records
            
        except Exception as e:
            logger.error(f"Error fetching DNS records: {str(e)}")
            raise
    
    def get_dns_records_as_json_string(self, dns_records: Dict[str, Dict]) -> str:
        """
        Convert DNS records to JSON string for logging/backup purposes
        
        Args:
            dns_records: Dict mapping hostname to DNS record data
            
        Returns:
            JSON string representation of DNS records
        """
        try:
            import json
            from datetime import datetime, timezone
            
            # Convert to a more compact format for logging
            records_list = []
            for hostname, record_data in dns_records.items():
                records_list.append({
                    'hostname': hostname,
                    'ip_address': record_data['content'],
                    'record_id': record_data['id'],
                    'type': record_data['type'],
                    'ttl': record_data.get('ttl', 60),
                    'proxied': record_data.get('proxied', False)
                })
            
            # Add metadata
            backup_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'domain': CLOUDFLARE_DOMAIN,
                'total_records': len(records_list),
                'records': records_list
            }
            
            return json.dumps(backup_data, indent=2)
            
        except Exception as e:
            logger.error(f"Error converting DNS records to JSON: {str(e)}")
            raise
    
    def get_dns_records_as_csv_string(self, dns_records: Dict[str, Dict]) -> str:
        """
        Convert DNS records to CSV string for logging/backup purposes
        
        Args:
            dns_records: Dict mapping hostname to DNS record data
            
        Returns:
            CSV string representation of DNS records
        """
        try:
            import io
            
            # Create CSV string in memory
            output = io.StringIO()
            fieldnames = ['hostname', 'ip_address', 'record_id', 'type', 'ttl', 'proxied']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            
            writer.writeheader()
            for hostname, record_data in dns_records.items():
                writer.writerow({
                    'hostname': hostname,
                    'ip_address': record_data['content'],
                    'record_id': record_data['id'],
                    'type': record_data['type'],
                    'ttl': record_data.get('ttl', 60),
                    'proxied': record_data.get('proxied', False)
                })
            
            csv_string = output.getvalue()
            output.close()
            
            return csv_string
            
        except Exception as e:
            logger.error(f"Error converting DNS records to CSV: {str(e)}")
            raise
    
    def reconcile_dns_records(self, instances: Dict[str, str], dns_records: Dict[str, Dict]) -> Dict:
        """
        Update DNS records to match EC2 instance IPs (only for existing records)
        
        This method will ONLY update existing DNS records. It will NEVER delete any DNS records
        under any circumstances. This is a safety measure to prevent accidental data loss.
        
        Args:
            instances: Dict mapping instance name to public IP
            dns_records: Dict mapping hostname to DNS record data
            
        Returns:
            Dict with statistics about the reconciliation
        """
        changes_made = False
        records_updated = 0
        records_unchanged = 0
        instances_without_records = 0
        
        for instance_name, public_ip in instances.items():
            # Handle -server suffix in instance names
            # Remove -server suffix if present for DNS record lookup
            expected_hostname = instance_name.removesuffix('-server')
            
            if expected_hostname in dns_records:
                current_ip = dns_records[expected_hostname]['content']
                if current_ip != public_ip:
                    logger.info(f"Updating DNS record: {expected_hostname} {current_ip} -> {public_ip}", 
                               extra={
                                   'dns_change': {
                                       'action': 'update',
                                       'hostname': expected_hostname,
                                       'old_ip': current_ip,
                                       'new_ip': public_ip,
                                       'instance_name': instance_name
                                   }
                               })
                    self._update_dns_record(
                        dns_records[expected_hostname]['id'],
                        expected_hostname,
                        public_ip
                    )
                    changes_made = True
                    records_updated += 1
                else:
                    logger.debug(f"DNS record up to date: {expected_hostname} -> {public_ip}")
                    records_unchanged += 1
            else:
                logger.debug(f"No DNS record exists for instance: {expected_hostname} -> {public_ip} (skipping)")
                instances_without_records += 1
        
        return {
            'changes_made': changes_made,
            'instances_processed': len(instances),
            'dns_records_checked': len(dns_records),
            'records_updated': records_updated,
            'records_unchanged': records_unchanged,
            'instances_without_records': instances_without_records,
            'records_deleted': 0  # Always 0 - deletion is disabled
        }
    
    def _update_dns_record(self, record_id: str, hostname: str, ip_address: str):
        """Update an existing A record"""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            record_data = {
                'type': 'A',
                'name': hostname,
                'content': ip_address,
                'ttl': 60,  # 1 minute TTL
                'proxied': False,  # DNS only, not proxied
                'tags': [
                    {
                        'name': 'updated-by',
                        'value': 'test-environment-dns-sync'
                    },
                    {
                        'name': 'last-updated',
                        'value': timestamp
                    }
                ]
            }
            
            # Update the DNS record
            self.cf.zones.dns_records.put(self.zone_id, record_id, data=record_data)
            logger.info(f"Updated DNS record: {hostname} -> {ip_address}")
            
        except Exception as e:
            logger.error(f"Error updating DNS record {hostname}: {str(e)}")
            raise
    