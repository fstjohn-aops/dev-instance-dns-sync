"""
Tests for DNS manager module
"""

import pytest
import os
from unittest.mock import Mock, patch
from src.dns_manager import DNSManager

class TestDNSManager:
    """Test cases for DNSManager"""
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('cloudflare.CloudFlare')
    def test_init(self, mock_cloudflare):
        """Test DNS manager initialization"""
        mock_cf = Mock()
        mock_cloudflare.return_value = mock_cf
        
        # Mock zone lookup
        mock_cf.zones.get.return_value = [{'id': 'test-zone-id'}]
        
        dns_manager = DNSManager()
        
        mock_cloudflare.assert_called_once_with(token='test-token')
        assert dns_manager.cf == mock_cf
        assert dns_manager.zone_id == 'test-zone-id'
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('cloudflare.CloudFlare')
    def test_init_missing_token(self, mock_cloudflare):
        """Test initialization with missing API token"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="CLOUDFLARE_API_TOKEN environment variable is required"):
                DNSManager()
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('cloudflare.CloudFlare')
    def test_get_dns_records(self, mock_cloudflare):
        """Test fetching DNS records"""
        mock_cf = Mock()
        mock_cloudflare.return_value = mock_cf
        
        # Mock zone lookup
        mock_cf.zones.get.return_value = [{'id': 'test-zone-id'}]
        
        # Mock DNS records
        mock_records = [
            {
                'id': 'record-1',
                'name': 'test-instance-1.aopstest.com',
                'content': '192.168.1.100',
                'type': 'A'
            },
            {
                'id': 'record-2',
                'name': 'test-instance-2.aopstest.com',
                'content': '192.168.1.101',
                'type': 'A'
            },
            {
                'id': 'record-3',
                'name': 'other-domain.com',
                'content': '192.168.1.102',
                'type': 'A'
            }
        ]
        
        mock_cf.zones.dns_records.get.return_value = mock_records
        
        dns_manager = DNSManager()
        records = dns_manager.get_dns_records()
        
        expected = {
            'test-instance-1.aopstest.com': {
                'id': 'record-1',
                'content': '192.168.1.100',
                'name': 'test-instance-1.aopstest.com',
                'type': 'A'
            },
            'test-instance-2.aopstest.com': {
                'id': 'record-2',
                'content': '192.168.1.101',
                'name': 'test-instance-2.aopstest.com',
                'type': 'A'
            }
        }
        
        assert records == expected
        mock_cf.zones.dns_records.get.assert_called_once_with(
            'test-zone-id',
            params={'type': 'A'}
        )
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('cloudflare.CloudFlare')
    def test_reconcile_dns_records(self, mock_cloudflare):
        """Test DNS record reconciliation"""
        mock_cf = Mock()
        mock_cloudflare.return_value = mock_cf
        
        # Mock zone lookup
        mock_cf.zones.get.return_value = [{'id': 'test-zone-id'}]
        
        dns_manager = DNSManager()
        
        # Test data
        instances = {
            'test-instance-1': '192.168.1.100',
            'test-instance-2': '192.168.1.101'
        }
        
        dns_records = {
            'test-instance-1.aopstest.com': {
                'id': 'record-1',
                'content': '192.168.1.100',  # Same IP
                'name': 'test-instance-1.aopstest.com',
                'type': 'A'
            },
            'test-instance-2.aopstest.com': {
                'id': 'record-2',
                'content': '192.168.1.200',  # Different IP
                'name': 'test-instance-2.aopstest.com',
                'type': 'A'
            },
            'orphaned-instance.aopstest.com': {
                'id': 'record-3',
                'content': '192.168.1.300',
                'name': 'orphaned-instance.aopstest.com',
                'type': 'A'
            }
        }
        
        # Mock the update and delete methods
        dns_manager._update_dns_record = Mock()
        dns_manager._create_dns_record = Mock()
        dns_manager._delete_dns_record = Mock()
        
        changes_made = dns_manager.reconcile_dns_records(instances, dns_records)
        
        # Should update test-instance-2 (IP changed) and delete orphaned record
        assert changes_made is True
        dns_manager._update_dns_record.assert_called_once_with(
            'record-2',
            'test-instance-2.aopstest.com',
            '192.168.1.101'
        )
        dns_manager._delete_dns_record.assert_called_once_with('record-3')
        dns_manager._create_dns_record.assert_not_called() 