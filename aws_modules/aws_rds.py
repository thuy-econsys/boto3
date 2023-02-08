import boto3
from botocore.exceptions import ClientError

from aws_modules.cis_error_logger import cis_issue_logger

import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger()
REGION = 'us-gov-west-1'

RDS_CLIENT = boto3.client('rds', region_name=REGION)
RDS_INSTANCES = RDS_CLIENT.describe_db_instances()


def print_rds_instances():
    if not RDS_INSTANCES:
        print("No RDS instances to output.")
        return

    for rds in RDS_INSTANCES['DBInstances']:
        try:
            # print(rds)
            print(f'{rds["DBInstanceIdentifier"]}')
            cis_id = "2.3.1"
            print(f"storage encryption: {rds['StorageEncrypted']}")
            cis_id = "2.3.2"
            print(f"minor ver upgrade: {rds['AutoMinorVersionUpgrade']}")
            cis_id = "2.3.3"
            print(f"public access: {rds['PubliclyAccessible']}\n")

        except ClientError as err:
            LOGGER.error(f'ClientError: {err}')
