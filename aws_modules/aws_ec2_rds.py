'''
# 2.2.1
$ aws ec2 get-ebs-encryption-by-default --region us-gov-west-1
# 2.3.1
$ aws rds describe-db-instances --region us-gov-west-1 --query 'DBInstances[*].DBInstanceIdentifier'
$ aws rds describe-db-instances --region us-gov-west-1 --db-instance-identifier <DB-Name> --query 'DBInstances[*].StorageEncrypted'
'''
import boto3

from botocore.exceptions import ClientError

import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger()

REGION = 'us-gov-west-1'

STS_CLIENT = boto3.client('sts', region_name=REGION)
AWS_ACCOUNT = STS_CLIENT.get_caller_identity().get('Account')

# aws ec2 describe-route-tables --filter "Name=vpc-id,Values=<vpc_id>" --query "RouteTables[*].{RouteTableId:RouteTableId, VpcId:VpcId, Routes:Routes, AssociatedSubnets:Associations[*].SubnetId}"
