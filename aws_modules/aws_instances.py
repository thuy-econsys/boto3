import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone

import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger()

TODAY = datetime.now(tz=timezone.utc)
REGION = 'us-gov-west-1'
AWS_ACCOUNT = boto3.client('sts', region_name=REGION).get_caller_identity().get('Account')

RDS_CLIENT = boto3.client('rds')
RDS_CLIENT = RDS_CLIENT.describe_db_instances()

EC2_CLIENT = boto3.client('ec2', region_name=REGION)
EC2_RESOURCE = boto3.resource('ec2', region_name=REGION)

reservations = EC2_CLIENT.describe_instances(
    Filters=[
        {
            "Name": "instance-state-name",
            "Values": ["running"]
        }
    ],
    OwnerIds=['self']
).get("Reservations")

EC2_INSTANCES = EC2_RESOURCE.instances.filter(
    Filters=[
        {
            "Name": "instance-state-name",
            "Values": ["running", "pending"]
        }
    ],
    # InstanceIds=['']
)

AMI_CLIENT = EC2_CLIENT.describe_images(
    Filters=[
        {
            'Name': 'state',
            'Values': ['available']
        }
    ],
    Owners=['self']
)

AMI_RESOURCE = EC2_RESOURCE.images.filter(
    Filters=[
        {
            'Name': 'tag:Description',
            'Values': ['packer*', '*RHEL*', 'Spel*']
        },
        # {
        #     'Name': 'name',
        #     'Values': ['burpees']
        #     # 'Values': ['burp-RHEL-*']
        # }
    ],
    # ImageIds=[''],
    Owners=['self']
)

SNAPSHOT_CLIENT = EC2_CLIENT.describe_snapshots(
    OwnerIds=['self']
)

SNAPSHOT_RESOURCE = EC2_RESOURCE.snapshots.filter(
    Filters=[
        {
            'Name': 'tag:Description',
            'Values': ['*RHEL*', 'packer image*']
        },
        {
            'Name': 'tag:Name',
            'Values': ['*RHEL*', 'packer-*']
        }
    ],
    # SnapshotIds=[''],
    OwnerIds=['self']
)

VOLUME_RESOURCE = EC2_RESOURCE.volumes.filter(
    Filters=[
        {
            'Name': 'status',
            'Values': ['available', 'in-use']
        }
    ]
)


def print_list(print_this: list):
    for item in print_this:
        print(f"{item}")


def print_rds_instances():
    if not RDS_CLIENT:
        print("No RDS instances to print.")
        return

    for rds in RDS_CLIENT['DBInstances']:
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


# 2.2.1
# aws ec2 get-ebs-encryption-by-default - -region us-gov-west-1
# aws ec2 describe-route-tables --filter "Name=vpc-id,Values=<vpc_id>" --query "RouteTables[*].{RouteTableId:RouteTableId, VpcId:VpcId, Routes:Routes, AssociatedSubnets:Associations[*].SubnetId}"
def print_ec2_instances():
    for reservation in reservations:

        for ec2 in reservation['Instances']:
            print(f'{ec2["InstanceId"]} created by {ec2["ImageId"]} in {ec2["VpcId"]}, state: {ec2["State"]["Name"]}')
            print(f"has {ec2['BlockDeviceMappings'][0]['Ebs']['VolumeId']} status: {ec2['BlockDeviceMappings'][0]['Ebs']['Status']}")

    # for ec2 in EC2_INSTANCES.all():
    #     print(f"{ec2.instance_id} created by {ec2.image_id}")


def sort_and_filter_amis(days_to_retain: int = 30) -> list:
    ami_names = []
    retention_date = TODAY - timedelta(days=days_to_retain)

    # for ami in AMI_CLIENT['Images']:
    #     print(f"{ami['Name']}")

    for ami in AMI_RESOURCE:
        try:
            if ami.creation_date >= str(retention_date):
                ami_names.append(ami.name)

        except ClientError as err:
            LOGGER.error(f'ClientError: {err}')

    ami_names.sort(reverse=True)
    return ami_names


def keep_latest_amis(ami_names: list, retain_no: int = 5) -> list:
    builds_to_keep = []
    build_names = []
    count = 0

    for ami_name in ami_names:
        try:
            str_array = ami_name.split('-')
            str_array.pop()
            build_name = '-'.join(str_array)

            if build_name not in build_names:
                build_names.append(build_name)
                count = 1

            # TODO logic to break early after collecting enough builds
            if (count <= retain_no) and (build_name in build_names):
                builds_to_keep.append(ami_name)
                count += 1

        except ClientError as err:
            LOGGER.error(f'ClientError: {err}')

    return builds_to_keep


def deregister_amis(keep_builds: list) -> tuple:
    ec2_dependencies = []
    amis_retained = []
    amis_deregistered = []

    # check for images currently associated to existing EC2s
    for instance in EC2_RESOURCE.instances.all():
        ec2_dependencies.append(instance.image_id)

    # for ami in AMI_CLIENT['Images']:
    #     if (ami['Name'] not in keep_builds) or (ami['ImageId'] not in ec2_dependencies):
    #         print(f'deregister {ami["ImageId"]}')
    #         # ami.deregister()
    #     else:
    #         print(f"keep {ami['ImageId']} for {ami['Name']}")

    for ami in AMI_RESOURCE:
        try:
            if (ami.name in keep_builds) or (ami.image_id in ec2_dependencies):
                # print(f"keep {ami.image_id} for {ami.name}")
                amis_retained.append(ami.image_id)
            else:
                # print(f"deregister {ami.image_id} for {ami.name}")
                amis_deregistered.append(ami.image_id)
                # TODO uncomment to start deregistering AMIs
                # ami.deregister()

        except ClientError as err:
            LOGGER.error(f'ClientError: {err}')

    return (amis_deregistered, amis_retained)


def delete_snapshots(amis_retained: list, days_to_retain_snapshot: int = 90):
    snapshot_retention_date = TODAY - timedelta(days=days_to_retain_snapshot)

    # for ami in AMI_CLIENT['Images']:
    #     # print(f"{ami.id}")
    #     # print(f"{ami.owner_id}")
    #     print(f"{ami['ImageId']}")
    #     print(f"{ami['OwnerId']}")

    # for snapshot in snapshot_resp['Snapshots']:
    #     print(f"{snapshot['SnapshotId']}")
    #     print(f"{snapshot['Description']}")

    for snapshot in SNAPSHOT_RESOURCE:
        # print(f"id: {snapshot.id}")
        # print(f"{snapshot.tags}")

        try:
            for ami_id in amis_retained:
                if (ami_id not in snapshot.description) or (snapshot.start_time <= snapshot_retention_date):
                    print(f"{snapshot.description}")
                    # TODO uncomment to start deleting snapshots
                    # snapshot.delete()
                    break

        except ClientError as err:
            LOGGER.error(f'ClientError: {err}')

        except ValueError as err:
            LOGGER.error(f'ValueError: {err}')


def delete_volumes(days_to_retain_volume: int = 1096):
    volume_retention_date = TODAY - timedelta(days=days_to_retain_volume)

    for volume in VOLUME_RESOURCE:

        if (volume.create_time >= volume_retention_date) or (volume.state == 'in-use'):
            print(f"{volume.volume_id} to be retained - {volume.state}\n")
        else:
            print(f"{volume.volume_id} to be deleted - {volume.state}\n")
