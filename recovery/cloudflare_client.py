"""
Cloudflare API client for recovery operations
"""

import os
import logging
import CloudFlare
from typing import Dict
from src.config import CLOUDFLARE_DOMAIN

logger = logging.getLogger(__name__)

class CloudflareClient:
    def __init__(self):
        self.api_token = os.environ.get('CLOUDFLARE_API_TOKEN')
        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN environment variable is required")
        
        self.cf = CloudFlare.CloudFlare(token=self.api_token)
        self.zone_id = self._get_zone_id()
        logger.info(f"Initialized Cloudflare client for domain: {CLOUDFLARE_DOMAIN}")
    
    def _get_zone_id(self) -> str:
        """Get Cloudflare zone ID for the domain"""
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
    
    def get_existing_records(self) -> Dict[str, Dict]:
        """Get all existing A records from Cloudflare"""
        try:
            existing_records = {}
            page = 1
            per_page = 100
            
            while True:
                records = self.cf.zones.dns_records.get(
                    self.zone_id,
                    params={
                        'type': 'A',
                        'page': page,
                        'per_page': per_page
                    }
                )
                
                if not records:
                    break
                
                for record in records:
                    hostname = record['name']
                    if hostname.endswith(f'.{CLOUDFLARE_DOMAIN}'):
                        existing_records[hostname] = {
                            'id': record['id'],
                            'content': record['content'],
                            'name': record['name'],
                            'type': record['type']
                        }
                
                if len(records) < per_page:
                    break
                
                page += 1
            
            logger.info(f"Found {len(existing_records)} existing DNS A records")
            return existing_records
            
        except Exception as e:
            logger.error(f"Error fetching existing DNS records: {str(e)}")
            raise
    
    def create_record(self, hostname: str, ip_address: str, ttl: int = 60, proxied: bool = False, comment: str = ""):
        """Create a new A record"""
        try:
            record_data = {
                'type': 'A',
                'name': hostname,
                'content': ip_address,
                'ttl': ttl,
                'proxied': proxied
            }
            
            if comment:
                record_data['comment'] = comment
            
            self.cf.zones.dns_records.post(self.zone_id, data=record_data)
            logger.info(f"Created DNS record: {hostname} -> {ip_address}")
            
        except Exception as e:
            logger.error(f"Error creating DNS record {hostname}: {str(e)}")
            raise
    
    def update_record(self, record_id: str, hostname: str, ip_address: str, ttl: int = 60, proxied: bool = False, comment: str = ""):
        """Update an existing A record"""
        try:
            record_data = {
                'type': 'A',
                'name': hostname,
                'content': ip_address,
                'ttl': ttl,
                'proxied': proxied
            }
            
            if comment:
                record_data['comment'] = comment
            
            self.cf.zones.dns_records.put(self.zone_id, record_id, data=record_data)
            logger.info(f"Updated DNS record: {hostname} -> {ip_address}")
            
        except Exception as e:
            logger.error(f"Error updating DNS record {hostname}: {str(e)}")
            raise 