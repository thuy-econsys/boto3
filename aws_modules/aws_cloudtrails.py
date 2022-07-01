import boto3
from datetime import datetime

from aws_modules.cis_error_logger import cis_issue_logger

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

3.7
aws cloudtrail describe-trails --region us-gov-west-1 --query trailList[*].KmsKeyId
'''


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
                msg = "Logfile validation is NOT enabled"
                LOGGER.warning(f'{msg} for {trail_name}')

                trail_issues = cis_issue_logger(trail_name, trail_issues, cis_id)

        except CLOUDTRAIL_CLIENT.exceptions.from_code('TrailNotFoundException'):
            msg = 'NO Trail'
            LOGGER.error(f'{msg} for {trail_name}')

            if trail_name not in trail_issues.keys():
                trail_issues[trail_name] = {}
            if msg not in trail_issues[trail_name].values():
                trail_issues[trail_name].update({'exception': msg})

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {trail_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

        cis_id = "3.1"
        if(not is_multi_regional):
            msg = "Multi-region is not enabled for any trails"
            LOGGER.warning(f'{msg}')

            trail_issues = cis_issue_logger(trail_name, trail_issues, cis_id)

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
                LOGGER.warning(f'{msg}')
                
                trail_issues = cis_issue_logger(trail_name, trail_issues, cis_id)

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {bucket_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

    count += 1
    return trail_issues


def check_cloudwatch_is_logging(trail_issues={}):
    count = 0
    one_day_ago = int(datetime.now().timestamp()) - 86400

    for trail in TRAILS:
        trail_name = trail['Name']

        try:
            response = CLOUDTRAIL_CLIENT.get_trail_status(Name=trail_name)

            cis_id = '3.4'
            if('CloudWatchLogsLogGroupArn' in trail.keys() and 'LatestCloudWatchLogsDeliveryTime' in response.keys()):
                last_logged = int(response['LatestCloudWatchLogsDeliveryTime'].timestamp())
                latest_log_time = datetime.fromtimestamp(last_logged)
                msg = f'CloudWatch last logged at {latest_log_time}'

                if last_logged < one_day_ago:
                    LOGGER.warning(f'OVERDUE: {msg} for {trail_name}')

                    trail_issues = cis_issue_logger(trail_name, trail_issues, cis_id)

                # else:
                #     LOGGER.info(f'{msg} for {trail_name}')

            else:
                msg = 'CloudWatch not being logged'
                LOGGER.warning(f'{msg} for {trail_name}')

                trail_issues = cis_issue_logger(trail_name, trail_issues, cis_id)

        except CLOUDTRAIL_CLIENT.exceptions.from_code('TrailNotFoundException'):
            msg = 'NO Trail'
            LOGGER.error(f'{msg} for {trail_name}')

            if trail_name not in trail_issues.keys():
                trail_issues[trail_name] = {}
            if msg not in trail_issues[trail_name].values():
                trail_issues[trail_name].update({'exception': msg})

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {trail_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

    count += 1
    return trail_issues


# aws cloudtrail get-event-selectors --region us-gov-west-1 --trail-name <trail_name> --query EventSelectors[*].DataResources[]

# output of empty array means no Object-level logging
# aws cloudtrail put-event-selectors --region <region-name> --trail-name <trail-name> --event-selectors \
  # '[{ "ReadWriteType": "WriteOnly", "IncludeManagementEvents":true, "DataResources": [{ "Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::<s3-bucket-name>/"] }] }]'
  # '[{ "ReadWriteType": "ReadOnly", "IncludeManagementEvents":true, "DataResources": [{ "Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::<s3-bucket-name>/"] }] }]'
