"""
Record parser for reading DNS records from JSON or CSV files
"""

import json
import csv
import logging
from typing import List, Dict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class RecordParser:
    def parse_file(self, file_path: str) -> List[Dict]:
        """Parse DNS records from JSON or CSV file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Try to parse as JSON first
            if content.startswith('{'):
                return self._parse_json(content)
            else:
                return self._parse_csv(file_path)
                
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}")
            raise
    
    def _parse_json(self, content: str) -> List[Dict]:
        """Parse DNS records from JSON string"""
        try:
            data = json.loads(content)
            
            # Handle the backup format from the main app
            if 'records' in data:
                records = data['records']
                logger.info(f"Parsed {len(records)} records from JSON backup (timestamp: {data.get('timestamp', 'unknown')})")
                return records
            
            # Handle direct array format
            elif isinstance(data, list):
                logger.info(f"Parsed {len(data)} records from JSON array")
                return data
            
            else:
                raise ValueError("Invalid JSON format: expected 'records' key or array")
                
        except Exception as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            raise
    
    def _parse_csv(self, file_path: str) -> List[Dict]:
        """Parse DNS records from CSV file"""
        try:
            records = []
            
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    record = {
                        'hostname': row['hostname'],
                        'ip_address': row['ip_address'],
                        'record_id': row.get('record_id', ''),
                        'type': row.get('type', 'A'),
                        'ttl': int(row.get('ttl', 60)),
                        'proxied': row.get('proxied', 'false').lower() == 'true'
                    }
                    records.append(record)
            
            logger.info(f"Parsed {len(records)} records from CSV file")
            return records
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise 