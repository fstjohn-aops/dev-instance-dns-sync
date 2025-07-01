"""
DNS Manager for Cloudflare DNS operations
"""

import os
import logging
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
            return dns_records
            
        except Exception as e:
            logger.error(f"Error fetching DNS records: {str(e)}")
            raise
    
    def reconcile_dns_records(self, instances: Dict[str, str], dns_records: Dict[str, Dict]) -> bool:
        """
        Update DNS records to match EC2 instance IPs (only for existing records)
        
        Args:
            instances: Dict mapping instance name to public IP
            dns_records: Dict mapping hostname to DNS record data
            
        Returns:
            True if changes were made, False otherwise
        """
        changes_made = False
        
        for instance_name, public_ip in instances.items():
            # Handle -server suffix in instance names
            expected_hostname = instance_name.replace(f'.{CLOUDFLARE_DOMAIN}-server', f'.{CLOUDFLARE_DOMAIN}')
            
            if expected_hostname in dns_records:
                current_ip = dns_records[expected_hostname]['content']
                if current_ip != public_ip:
                    logger.info(f"Updating DNS record: {expected_hostname} {current_ip} -> {public_ip}")
                    self._update_dns_record(
                        dns_records[expected_hostname]['id'],
                        expected_hostname,
                        public_ip
                    )
                    changes_made = True
                else:
                    logger.debug(f"DNS record up to date: {expected_hostname} -> {public_ip}")
            else:
                logger.debug(f"No DNS record exists for instance: {expected_hostname} -> {public_ip} (skipping)")
        
        return changes_made
    

    
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
                'comment': f'Updated by test environment DNS sync on {timestamp}'
            }
            
            self.cf.zones.dns_records.put(self.zone_id, record_id, data=record_data)
            logger.info(f"Updated DNS record: {hostname} -> {ip_address}")
            
        except Exception as e:
            logger.error(f"Error updating DNS record {hostname}: {str(e)}")
            raise
    
 