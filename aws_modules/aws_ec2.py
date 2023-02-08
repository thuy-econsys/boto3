import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone

from aws_modules.cis_error_logger import cis_issue_logger

import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger()

TODAY = datetime.now(tz=timezone.utc)
REGION = 'us-gov-west-1'

EC2_CLIENT = boto3.client('ec2', region_name=REGION)
EC2_RESOURCE = boto3.resource('ec2', region_name=REGION)

RESERVATIONS = EC2_CLIENT.describe_instances(
    Filters=[
        {
            "Name": "instance-state-name",
            "Values": ["running"]
        }
    ]
).get("Reservations")

# EC2_INSTANCES = EC2_RESOURCE.instances.filter(
#     Filters=[
#         {
#             "Name": "instance-state-name",
#             "Values": ["running", "pending"]
#         }
#     ],
#     # InstanceIds=['']
# )


# 2.2.1
# aws ec2 get-ebs-encryption-by-default --region us-gov-west-1
# TODO make sure not a false positive
def check_ebs_encryption(ec2_issues: dict = {}) -> dict:
    if not RESERVATIONS:
        print('No EC2 to check EBS volume encryption for.')
        return

    try:
        response = EC2_CLIENT.get_ebs_encryption_by_default()
        cis_id = '2.2.1'
        issue = "EBS encryption default"

        # print(response)

        if not response['EbsEncryptionByDefault']:
            ec2_issues = cis_issue_logger(issue, ec2_issues, cis_id)

    except ClientError as client_error:
        LOGGER.error(f'ClientError: {client_error}')

    return ec2_issues


# aws ec2 describe-route-tables --filter "Name=vpc-id,Values=<vpc_id>" --query "RouteTables[*].{RouteTableId:RouteTableId, VpcId:VpcId, Routes:Routes, AssociatedSubnets:Associations[*].SubnetId}"
def print_ec2_instances():
    if not RESERVATIONS:
        print('No EC2 instances to output.')

    for reservation in RESERVATIONS:
        for ec2 in reservation['Instances']:
            # print(f'{ec2["InstanceId"]} created by {ec2["ImageId"]} in {ec2["VpcId"]}, state: {ec2["State"]["Name"]}')
            print(f"{ec2['InstanceId']} attached to {ec2['BlockDeviceMappings'][0]['Ebs']['VolumeId']} status: {ec2['BlockDeviceMappings'][0]['Ebs']['Status']}")

    # for ec2 in EC2_INSTANCES.all():
    #     print(f"{ec2.instance_id} created by {ec2.image_id}")
