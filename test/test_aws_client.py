"""
Tests for AWS client module
"""

import pytest
from unittest.mock import Mock, patch
from src.aws_client import AWSClient

class TestAWSClient:
    """Test cases for AWSClient"""
    
    @patch('boto3.client')
    def test_init(self, mock_boto3_client):
        """Test AWS client initialization"""
        mock_ec2_client = Mock()
        mock_boto3_client.return_value = mock_ec2_client
        
        client = AWSClient()
        
        mock_boto3_client.assert_called_once_with('ec2', region_name='us-west-2')
        assert client.ec2_client == mock_ec2_client
    
    @patch('boto3.client')
    def test_get_instance_name(self, mock_boto3_client):
        """Test extracting instance name from tags"""
        client = AWSClient()
        
        # Test with Name tag
        instance_with_name = {
            'Tags': [
                {'Key': 'Name', 'Value': 'test-instance'},
                {'Key': 'Environment', 'Value': 'dev'}
            ]
        }
        name = client._get_instance_name(instance_with_name)
        assert name == 'test-instance'
        
        # Test without Name tag
        instance_without_name = {
            'Tags': [
                {'Key': 'Environment', 'Value': 'dev'}
            ]
        }
        name = client._get_instance_name(instance_without_name)
        assert name is None
        
        # Test without tags
        instance_no_tags = {}
        name = client._get_instance_name(instance_no_tags)
        assert name is None
    
    @patch('boto3.client')
    def test_get_instances_with_public_ips(self, mock_boto3_client):
        """Test fetching instances with public IPs"""
        mock_ec2_client = Mock()
        mock_boto3_client.return_value = mock_ec2_client
        
        # Mock response
        mock_response = {
            'Reservations': [
                {
                    'Instances': [
                        {
                            'InstanceId': 'i-1234567890abcdef0',
                            'PublicIpAddress': '192.168.1.100',
                            'Tags': [
                                {'Key': 'Name', 'Value': 'test-instance-1'}
                            ]
                        },
                        {
                            'InstanceId': 'i-0987654321fedcba0',
                            'PublicIpAddress': '192.168.1.101',
                            'Tags': [
                                {'Key': 'Name', 'Value': 'test-instance-2'}
                            ]
                        },
                        {
                            'InstanceId': 'i-11111111111111111',
                            'Tags': [
                                {'Key': 'Name', 'Value': 'test-instance-no-ip'}
                            ]
                        }
                    ]
                }
            ]
        }
        
        mock_ec2_client.describe_instances.return_value = mock_response
        
        client = AWSClient()
        instances = client.get_instances_with_public_ips()
        
        expected = {
            'test-instance-1': '192.168.1.100',
            'test-instance-2': '192.168.1.101'
        }
        
        assert instances == expected
        mock_ec2_client.describe_instances.assert_called_once() 