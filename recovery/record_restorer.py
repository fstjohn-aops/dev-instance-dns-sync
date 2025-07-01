"""
Record restorer for creating and updating DNS records
"""

import logging
from typing import List, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class RecordRestorer:
    def __init__(self, cloudflare_client):
        self.cloudflare_client = cloudflare_client
    
    def restore_records(self, records: List[Dict], existing_records: Dict[str, Dict], dry_run: bool = False) -> Dict:
        """Restore DNS records from backup"""
        created_count = 0
        updated_count = 0
        unchanged_count = 0
        
        for record in records:
            hostname = record['hostname']
            ip_address = record['ip_address']
            ttl = record.get('ttl', 60)
            proxied = record.get('proxied', False)
            
            if hostname in existing_records:
                existing_ip = existing_records[hostname]['content']
                if existing_ip != ip_address:
                    if not dry_run:
                        comment = f"Updated by recovery script on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                        self.cloudflare_client.update_record(
                            existing_records[hostname]['id'],
                            hostname,
                            ip_address,
                            ttl,
                            proxied,
                            comment
                        )
                    else:
                        logger.info(f"[DRY-RUN] Would update: {hostname} {existing_ip} -> {ip_address}")
                    updated_count += 1
                else:
                    logger.debug(f"Unchanged: {hostname} -> {ip_address}")
                    unchanged_count += 1
            else:
                if not dry_run:
                    comment = f"Created by recovery script on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    self.cloudflare_client.create_record(
                        hostname,
                        ip_address,
                        ttl,
                        proxied,
                        comment
                    )
                else:
                    logger.info(f"[DRY-RUN] Would create: {hostname} -> {ip_address}")
                created_count += 1
        
        return {
            'created': created_count,
            'updated': updated_count,
            'unchanged': unchanged_count
        }
    
    def verify_records(self, records: List[Dict]) -> Dict:
        """Verify that all records from backup exist and have correct IPs"""
        try:
            existing_records = self.cloudflare_client.get_existing_records()
            verified_count = 0
            missing_count = 0
            incorrect_count = 0
            
            for record in records:
                hostname = record['hostname']
                expected_ip = record['ip_address']
                
                if hostname in existing_records:
                    actual_ip = existing_records[hostname]['content']
                    if actual_ip == expected_ip:
                        logger.debug(f"Verified: {hostname} -> {expected_ip}")
                        verified_count += 1
                    else:
                        logger.warning(f"Incorrect IP: {hostname} expected {expected_ip}, got {actual_ip}")
                        incorrect_count += 1
                else:
                    logger.warning(f"Missing record: {hostname} -> {expected_ip}")
                    missing_count += 1
            
            logger.info(f"Verification complete: {verified_count} correct, {incorrect_count} incorrect IPs, {missing_count} missing")
            return {
                'verified': verified_count,
                'incorrect': incorrect_count,
                'missing': missing_count
            }
            
        except Exception as e:
            logger.error(f"Error verifying records: {str(e)}")
            raise 