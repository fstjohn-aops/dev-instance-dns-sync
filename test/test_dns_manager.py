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
    @patch('CloudFlare.CloudFlare')
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
    @patch('CloudFlare.CloudFlare')
    def test_init_missing_token(self, mock_cloudflare):
        """Test initialization with missing API token"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="CLOUDFLARE_API_TOKEN environment variable is required"):
                DNSManager()
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('CloudFlare.CloudFlare')
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
            params={'type': 'A', 'page': 1, 'per_page': 100}
        )
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('CloudFlare.CloudFlare')
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
        
        result = dns_manager.reconcile_dns_records(instances, dns_records)
        
        # Should update test-instance-2 (IP changed) and delete orphaned record
        assert result['changes_made'] is True
        dns_manager._update_dns_record.assert_called_once_with(
            'record-2',
            'test-instance-2.aopstest.com',
            '192.168.1.101'
        )
        dns_manager._delete_dns_record.assert_called_once_with('record-3')
        dns_manager._create_dns_record.assert_not_called()
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('CloudFlare.CloudFlare')
    def test_reconcile_dns_records_with_server_suffix(self, mock_cloudflare):
        """Test DNS record reconciliation with -server suffix instances"""
        mock_cf = Mock()
        mock_cloudflare.return_value = mock_cf
        
        # Mock zone lookup
        mock_cf.zones.get.return_value = [{'id': 'test-zone-id'}]
        
        dns_manager = DNSManager()
        
        # Test data with -server suffix instances
        instances = {
            'test-instance-1-server': '192.168.1.100',
            'test-instance-2-server': '192.168.1.101'
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
            }
        }
        
        # Mock the update and delete methods
        dns_manager._update_dns_record = Mock()
        dns_manager._create_dns_record = Mock()
        dns_manager._delete_dns_record = Mock()
        
        result = dns_manager.reconcile_dns_records(instances, dns_records)
        
        # Should update test-instance-2 (IP changed)
        assert result['changes_made'] is True
        dns_manager._update_dns_record.assert_called_once_with(
            'record-2',
            'test-instance-2.aopstest.com',
            '192.168.1.101'
        )
        dns_manager._delete_dns_record.assert_not_called()
        dns_manager._create_dns_record.assert_not_called()
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('CloudFlare.CloudFlare')
    def test_reconcile_dns_records_mixed_server_suffix(self, mock_cloudflare):
        """Test DNS record reconciliation with mixed -server and non-server instances"""
        mock_cf = Mock()
        mock_cloudflare.return_value = mock_cf
        
        # Mock zone lookup
        mock_cf.zones.get.return_value = [{'id': 'test-zone-id'}]
        
        dns_manager = DNSManager()
        
        # Test data with mixed -server and non-server instances
        instances = {
            'test-instance-1-server': '192.168.1.100',  # Has -server suffix
            'test-instance-2': '192.168.1.101',         # No -server suffix
            'test-instance-3-server': '192.168.1.102'   # Has -server suffix
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
            'test-instance-3.aopstest.com': {
                'id': 'record-3',
                'content': '192.168.1.102',  # Same IP
                'name': 'test-instance-3.aopstest.com',
                'type': 'A'
            },
            'orphaned-instance.aopstest.com': {
                'id': 'record-4',
                'content': '192.168.1.300',
                'name': 'orphaned-instance.aopstest.com',
                'type': 'A'
            }
        }
        
        # Mock the update and delete methods
        dns_manager._update_dns_record = Mock()
        dns_manager._create_dns_record = Mock()
        dns_manager._delete_dns_record = Mock()
        
        result = dns_manager.reconcile_dns_records(instances, dns_records)
        
        # Should update test-instance-2 (IP changed) and delete orphaned record
        assert result['changes_made'] is True
        dns_manager._update_dns_record.assert_called_once_with(
            'record-2',
            'test-instance-2.aopstest.com',
            '192.168.1.101'
        )
        dns_manager._delete_dns_record.assert_called_once_with('record-4')
        dns_manager._create_dns_record.assert_not_called()
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('CloudFlare.CloudFlare')
    def test_reconcile_dns_records_server_suffix_orphaned_detection(self, mock_cloudflare):
        """Test that orphaned DNS records are correctly detected when instances have -server suffix"""
        mock_cf = Mock()
        mock_cloudflare.return_value = mock_cf
        
        # Mock zone lookup
        mock_cf.zones.get.return_value = [{'id': 'test-zone-id'}]
        
        dns_manager = DNSManager()
        
        # Test data - only one instance with -server suffix
        instances = {
            'test-instance-1-server': '192.168.1.100'
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
                'content': '192.168.1.200',  # Should be deleted (orphaned)
                'name': 'test-instance-2.aopstest.com',
                'type': 'A'
            },
            'test-instance-3-server.aopstest.com': {
                'id': 'record-3',
                'content': '192.168.1.300',  # Should be deleted (orphaned, DNS has -server but no matching instance)
                'name': 'test-instance-3-server.aopstest.com',
                'type': 'A'
            }
        }
        
        # Mock the update and delete methods
        dns_manager._update_dns_record = Mock()
        dns_manager._create_dns_record = Mock()
        dns_manager._delete_dns_record = Mock()
        
        result = dns_manager.reconcile_dns_records(instances, dns_records)
        
        # Should delete both orphaned records
        assert result['changes_made'] is True
        assert result['records_deleted'] == 2
        dns_manager._update_dns_record.assert_not_called()
        dns_manager._create_dns_record.assert_not_called()
        # Check that both orphaned records were deleted
        dns_manager._delete_dns_record.assert_any_call('record-2')
        dns_manager._delete_dns_record.assert_any_call('record-3')
        assert dns_manager._delete_dns_record.call_count == 2
    
    @patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'test-token'})
    @patch('CloudFlare.CloudFlare')
    def test_reconcile_dns_records_server_suffix_edge_cases(self, mock_cloudflare):
        """Test DNS record reconciliation with edge cases for -server suffix"""
        mock_cf = Mock()
        mock_cloudflare.return_value = mock_cf
        
        # Mock zone lookup
        mock_cf.zones.get.return_value = [{'id': 'test-zone-id'}]
        
        dns_manager = DNSManager()
        
        # Test edge cases with -server suffix
        instances = {
            'server': '192.168.1.100',           # Just 'server' (removesuffix should handle this)
            'test-server': '192.168.1.101',      # Ends with -server
            'test-server-server': '192.168.1.102', # Ends with -server-server (removesuffix removes only last -server)
            'test-instance': '192.168.1.103'     # No -server suffix
        }
        
        dns_records = {
            'server.aopstest.com': {
                'id': 'record-1',
                'content': '192.168.1.100',  # Same IP
                'name': 'server.aopstest.com',
                'type': 'A'
            },
            'test.aopstest.com': {
                'id': 'record-2',
                'content': '192.168.1.101',  # Same IP (test-server -> test)
                'name': 'test.aopstest.com',
                'type': 'A'
            },
            'test-server.aopstest.com': {
                'id': 'record-3',
                'content': '192.168.1.102',  # Same IP (test-server-server -> test-server)
                'name': 'test-server.aopstest.com',
                'type': 'A'
            },
            'test-instance.aopstest.com': {
                'id': 'record-4',
                'content': '192.168.1.103',  # Same IP
                'name': 'test-instance.aopstest.com',
                'type': 'A'
            }
        }
        
        # Mock the update and delete methods
        dns_manager._update_dns_record = Mock()
        dns_manager._create_dns_record = Mock()
        dns_manager._delete_dns_record = Mock()
        
        result = dns_manager.reconcile_dns_records(instances, dns_records)
        
        # Should not make any changes (all IPs match)
        assert result['changes_made'] is False
        assert result['records_updated'] == 0
        assert result['records_unchanged'] == 4
        assert result['records_deleted'] == 0
        dns_manager._update_dns_record.assert_not_called()
        dns_manager._create_dns_record.assert_not_called()
        dns_manager._delete_dns_record.assert_not_called() 