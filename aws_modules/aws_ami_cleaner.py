#! /usr/bin/python3

from typing import Iterator
import boto3
from botocore.exceptions import ClientError, ParamValidationError
from datetime import datetime, timedelta, timezone

import logging
logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger()
TODAY = datetime.now(tz=timezone.utc)
REGION = 'us-gov-west-1'
EC2_CLIENT = boto3.client('ec2', region_name=REGION)
EC2_RESOURCE = boto3.resource('ec2', region_name=REGION)


def main():
    ami_iterable = get_amis()
    amis_sorted = sort_amis(ami_iterable)
    print(f"{len(amis_sorted)}")
    builds_to_keep = keep_latest_amis(amis_sorted)
    amis = deregister_amis(builds_to_keep, ami_iterable)
    delete_snapshots(amis[0])
    delete_volumes()


def print_list(print_this: list):
    for item in print_this:
        print(f"{item}")


# AMIs

def get_amis() -> Iterator:
    try:
        # TODO update Values for RHEL 8?
        return EC2_RESOURCE.images.filter(
            Filters=[
                {
                    'Name': 'name',
                    'Values': ['*RHEL-*']
                },
                {
                    'Name': 'tag:Description',
                    'Values': ['packer*', '*RHEL*', 'Spel*']
                },
            ],
            Owners=['self']
        )

    except ClientError as api_err:
        error_code = api_err.response['Error']['Code']
        error_message = api_err.response['Error']['Message']
        LOGGER.error(f"AWS API Error: {error_code} - {error_message}")

    except (KeyError, ValueError, ParamValidationError) as data_err:
        LOGGER.error(f"Error during data processing: {data_err}")

    except Exception as err:
        LOGGER.error(f"Unexpected error: {err}")
        raise


def sort_amis(amis: list = []) -> list:
    if not amis:
        print("No AMIs found matching filter.")
        return []

    ami_names = []

    try:
        for ami in amis:
            ami_names.append(ami.name)

        #  reverse order for latest based on timestamp
        ami_names.sort(reverse=True)

    except ClientError as api_err:
        error_code = api_err.response['Error']['Code']
        error_message = api_err.response['Error']['Message']
        LOGGER.error(f"AWS API Error: {error_code} - {error_message}")

    except (KeyError, ValueError, ParamValidationError) as data_err:
        LOGGER.error(f"Error during data processing: {data_err}")

    except Exception as err:
        LOGGER.error(f"Unexpected error: {err}")
        raise

    return ami_names


def keep_latest_amis(ami_names: list = [], retain_no: int = 10) -> list:
    if not ami_names:
        print("No AMIs up for deregistering.")
        return []

    builds = []
    build_names = []
    count = 0

    try:
        for ami_name in ami_names:
            str_array = ami_name.split('-')
            str_array.pop()
            build_name = '-'.join(str_array)

            if build_name not in build_names:
                build_names.append(build_name)
                count = 1

            if (count <= retain_no) and (build_name in build_names):
                builds.append(ami_name)
                count += 1

    except ValueError as data_err:
        LOGGER.error(f"Error during data processing: {data_err}")

    except Exception as err:
        LOGGER.error(f"Unexpected error: {err}")
        raise

    return builds


def deregister_amis(keep_builds: list, ami_iterable: Iterator) -> tuple:
    if not keep_builds:
        print("No AMIs to deregister.")
        return ([], [])

    ec2_dependencies = []
    amis_retained = []
    amis_deregistered = []

    # check for images currently associated to existing EC2s
    for instance in EC2_RESOURCE.instances.all():
        ec2_dependencies.append(instance.image_id)

    try:
        for ami in ami_iterable:
            if (ami.name in keep_builds) or (ami.image_id in ec2_dependencies):
                print(f"keep {ami.image_id} for {ami.name}")
                amis_retained.append(ami.image_id)
            else:
                print(f" - deregistering {ami.image_id} for {ami.name}")
                amis_deregistered.append(ami.image_id)
                ami.deregister()

    except ClientError as api_err:
        error_code = api_err.response['Error']['Code']
        error_message = api_err.response['Error']['Message']
        LOGGER.error(f"AWS API Error: {error_code} - {error_message}")

    except (KeyError, ValueError, ParamValidationError) as data_err:
        LOGGER.error(f"Error during data processing: {data_err}")

    except Exception as err:
        LOGGER.error(f"Unexpected error: {err}")
        raise

    return (amis_deregistered, amis_retained)


# Snapshots


def get_snapshots() -> list:
    try:
        return EC2_RESOURCE.snapshots.filter(
            Filters=[
                {
                    'Name': 'status',
                    'Values': ['completed']
                },
                {
                    'Name': 'description',
                    'Values': ['Created by CreateImage*']
                },
                {
                    'Name': 'tag:Description',
                    'Values': ['*RHEL*', 'packer image*']
                }
            ],
            OwnerIds=['self']
        )

    except ClientError as api_err:
        error_code = api_err.response['Error']['Code']
        error_message = api_err.response['Error']['Message']
        LOGGER.error(f"AWS API Error: {error_code} - {error_message}")

    except (KeyError, ValueError, ParamValidationError) as data_err:
        LOGGER.error(f"Error during data processing: {data_err}")

    except Exception as err:
        LOGGER.error(f"Unexpected error: {err}")
        raise


def delete_snapshots(amis_deregistered: list = []):
    snapshots = get_snapshots()

    if (not amis_deregistered) or (not snapshots):
        print("No snapshots associated to AMIs for deletion.")
        return []

    try:
        for snapshot in snapshots:
            for ami_id in amis_deregistered:
                # TODO add logic to delete snapshots older than 6 months or longer and not associated to EC2 resources

                if (ami_id in snapshot.description):
                    print(
                        f" - deleting snapshot {snapshot.id} for {ami_id}...")
                    amis_deregistered.remove(ami_id)
                    snapshot.delete()
                    break

    except ClientError as api_err:
        error_code = api_err.response['Error']['Code']
        error_message = api_err.response['Error']['Message']
        LOGGER.error(f"AWS API Error: {error_code} - {error_message}")

    except (KeyError, ValueError, ParamValidationError) as data_err:
        LOGGER.error(f"Error during data processing: {data_err}")

    except Exception as err:
        LOGGER.error(f"Unexpected error: {err}")
        raise


# EBS Volumes


def get_volumes() -> list:
    try:
        return EC2_CLIENT.describe_volumes(
            Filters=[
                {
                    'Name': 'status',
                    'Values': ['available', 'in-use']
                }
            ]
        )['Volumes']

    except ClientError as api_err:
        error_code = api_err.response['Error']['Code']
        error_message = api_err.response['Error']['Message']
        LOGGER.error(f"AWS API Error: {error_code} - {error_message}")

    except (KeyError, ValueError, ParamValidationError) as data_err:
        LOGGER.error(f"Error during data processing: {data_err}")

    except Exception as err:
        LOGGER.error(f"Unexpected error: {err}")
        raise


def delete_volumes(days_to_retain_volume: int = 1096):
    volumes = get_volumes()

    if not volumes:
        print("No volumes up for removal.")
        return

    volume_retention_date = TODAY - timedelta(days=days_to_retain_volume)

    try:
        for volume in volumes:
            if (volume['CreateTime'] >= volume_retention_date) or (volume['State'] == 'in-use'):
                print(
                    f"{volume['VolumeId']} to be retained - {volume['State']}")
            else:
                print(
                    f"{volume['VolumeId']} to be deleted - {volume['State']}")
                EC2_CLIENT.delete_volume(VolumeId=volume['VolumeId'])

    except ClientError as api_err:
        error_code = api_err.response['Error']['Code']
        error_message = api_err.response['Error']['Message']
        LOGGER.error(f"AWS API Error: {error_code} - {error_message}")

    except (KeyError, ValueError, ParamValidationError) as data_err:
        LOGGER.error(f"Error during data processing: {data_err}")

    except Exception as err:
        LOGGER.error(f"Unexpected error: {err}")
        raise


if __name__ == '__main__':
    main()
