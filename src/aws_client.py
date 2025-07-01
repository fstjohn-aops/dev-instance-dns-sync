"""
AWS Client for fetching EC2 instances and their public IPs
"""

import boto3
import logging
from typing import Dict, Optional
from src.config import AWS_REGION

logger = logging.getLogger(__name__)

class AWSClient:
    """AWS client for EC2 operations"""
    
    def __init__(self):
        """Initialize AWS client"""
        self.ec2_client = boto3.client('ec2', region_name=AWS_REGION)
        logger.info(f"Initialized AWS EC2 client for region: {AWS_REGION}")
    
    def get_instances_with_public_ips(self) -> Dict[str, str]:
        """
        Get all EC2 instances with their public IPs
        
        Returns:
            Dict mapping instance name to public IP
        """
        try:
            instances = {}
            next_token = None
            
            while True:
                # Get only running instances with EC2ControlsEnabled: true tag
                if next_token:
                    response = self.ec2_client.describe_instances(
                        Filters=[
                            {
                                'Name': 'instance-state-name',
                                'Values': ['running']
                            },
                            {
                                'Name': 'tag:EC2ControlsEnabled',
                                'Values': ['true']
                            }
                        ],
                        NextToken=next_token
                    )
                else:
                    response = self.ec2_client.describe_instances(
                        Filters=[
                            {
                                'Name': 'instance-state-name',
                                'Values': ['running']
                            },
                            {
                                'Name': 'tag:EC2ControlsEnabled',
                                'Values': ['true']
                            }
                        ]
                    )
                
                for reservation in response['Reservations']:
                    for instance in reservation['Instances']:
                        instance_id = instance['InstanceId']
                        instance_name = self._get_instance_name(instance)
                        
                        # Get public IP if available
                        public_ip = instance.get('PublicIpAddress')
                        
                        if instance_name and public_ip:
                            instances[instance_name] = public_ip
                        elif instance_name:
                            logger.warning(f"Instance {instance_name} has no public IP")
                
                next_token = response.get('NextToken')
                if not next_token:
                    break
            
            logger.info(f"Found {len(instances)} instances with public IPs")
            
            # Log all instances found
            instances_array = [{"name": name, "ip": ip} for name, ip in instances.items()]
            logger.info("EC2 instances found", extra={
                'instances': instances_array
            })
            
            return instances
            
        except Exception as e:
            logger.error(f"Error fetching EC2 instances: {str(e)}")
            raise
    
    def _get_instance_name(self, instance: Dict) -> Optional[str]:
        """
        Extract instance name from tags
        
        Args:
            instance: EC2 instance data
            
        Returns:
            Instance name or None if not found
        """
        if 'Tags' in instance:
            for tag in instance['Tags']:
                if tag['Key'] == 'Name':
                    return tag['Value']
        return None 