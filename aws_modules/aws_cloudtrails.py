import boto3
import json

from botocore.exceptions import ClientError

import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger()

REGION = 'us-gov-west-1'

STS_CLIENT = boto3.client('sts', region_name=REGION)
AWS_ACCOUNT = STS_CLIENT.get_caller_identity().get('Account')

CLOUDTRAIL_CLIENT = boto3.client('cloudtrail', region_name=REGION)
TRAILS = CLOUDTRAIL_CLIENT.describe_trails()['trailList']

S3_CLIENT = boto3.client("s3", region_name=REGION)
BUCKETS = S3_CLIENT.list_buckets()['Buckets']


# 2.1.5, 3.3
'''
$ aws cloudtrail describe-trails --query 'trailList[*].S3BucketName'
$ aws s3api get-bucket-acl --bucket <bucket_name> --query 'Grants[?Grantee.URI== `https://acs.amazonaws.com/groups/global/AllUsers` ]'
$ aws s3api get-bucket-acl --bucket <bucket_name> --query 'Grants[?Grantee.
$ aws s3api get-bucket-policy --bucket <bucket_name>
'''

'''
$ aws cloudtrail get-event-selectors --trail-name cloudtrail-multi-region
{
    "TrailARN": "arn:aws-us-gov:cloudtrail:us-gov-west-1:578463482707:trail/cloudtrail-multi-region",
    "EventSelectors": [
        {
            "ReadWriteType": "All",
            "IncludeManagementEvents": true,
            "DataResources": [],
            "ExcludeManagementEventSources": []
        }
    ]
}


$ aws configservice describe-configuration-recorders
{
    "ConfigurationRecorders": [
        {
            "name": "default",
            "roleARN": "arn:aws-us-gov:iam::578463482707:role/Config-Recorder-578463482707",
            "recordingGroup": {
                "allSupported": true,
                "includeGlobalResourceTypes": true,
                "resourceTypes": []
            }
        }
    ]
}

3.5

$ aws configservice describe-configuration-recorders
{
    "ConfigurationRecorders": [
        {
            "name": "default",
            "roleARN": "arn:aws-us-gov:iam::578463482707:role/Config-Recorder-578463482707",
            "recordingGroup": {
                "allSupported": true,
                "includeGlobalResourceTypes": true,
                "resourceTypes": []
            }
        }
    ]
}

$ aws configservice describe-configuration-recorder-status
{
    "ConfigurationRecordersStatus": [
        {
            "name": "default",
            "lastStartTime": 1574711437.693,
            "recording": true,
            "lastStatus": "SUCCESS",
            "lastStatusChangeTime": 1655668249.818
        }
    ]
}

3.6
$ aws s3api get-bucket-logging --bucket econsys-security-aws-audit-log-578463482707-west
{
    "LoggingEnabled": {
        "TargetBucket": "econsys-security-aws-audit-log-578463482707-access-logs-west",
        "TargetPrefix": ""
    }
}

3.7
aws cloudtrail describe-trails --region us-gov-west-1 --query trailList[*].KmsKeyId
'''


# aws cloudtrail list-trails --region us-gov-west-1 --query Trails[*].Name
def check_cloudtrail(trail_issues={}):
    count = 0
    # at least one trail is Multi-regional
    is_multi_regional = False

    for trail in TRAILS:
        trail_name = trail['Name']
        bucket_name = trail['S3BucketName']

        try:
            if trail['IsMultiRegionTrail']:
                is_multi_regional = True
                LOGGER.info(f'Multi region is enabled for {trail_name}')

            cis_id = "3.2"
            if trail['LogFileValidationEnabled']:
                LOGGER.info(f'Logfile validation is enabled for {trail_name}')
            else:
                trail_issues[trail_name] = []
                msg = "Logfile validation is NOT enabled"
                trail_issues[trail_name].append({cis_id: msg})
                LOGGER.warning(f'{msg} for {trail_name}')

            # response = CLOUDTRAIL_CLIENT.get_trail_status(Name=trail_name)

            # print(response)

        except CLOUDTRAIL_CLIENT.exceptions.from_code('TrailNotFoundException'):
            trail_issues[trail_name] = []
            msg = 'NO Trail'
            trail_issues[trail_name].append(msg)
            LOGGER.error(f'{msg} for {trail_name}')

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {trail_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

        cis_id = "3.1"
        if(not is_multi_regional):
            msg = "Multi-region is not enabled for any trails"
            trail_issues[trail_name].append({cis_id: msg})
            LOGGER.warning(f'{msg}')

        # ensure logging to S3
        # $ aws cloudtrail get-trail-status --name prod-cloudtrail-logs --query ['IsLogging']
        # $ aws cloudtrail describe-trails --region us-gov-west-1 --query trailList[*].CloudWatchLogsLogGroupArn
        # $ aws cloudtrail get-trail-status --name prod-cloudtrail-logs --query ['LatestDeliveryTime']
        try:
            response = S3_CLIENT.get_bucket_logging(
                Bucket=bucket_name,
                ExpectedBucketOwner=AWS_ACCOUNT)

            cis_id = "3.6"
            if (response['LoggingEnabled']):
                msg = 'Logging enabled'
                # LOGGER.info(f'{msg} to {bucket_name} for {trail_name}')
            else:
                msg = "Logging not enabled"
                trail_issues[trail_name].append({cis_id: msg})
                LOGGER.warning(f'{msg}')

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {bucket_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

    count += 1
    return trail_issues
