import boto3
import json

from botocore.exceptions import ClientError

import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger()

REGION = 'us-gov-west-1'

STS_CLIENT = boto3.client('sts', region_name=REGION)
AWS_ACCOUNT = STS_CLIENT.get_caller_identity().get('Account')

S3_CLIENT = boto3.client("s3", region_name=REGION)
BUCKETS = S3_CLIENT.list_buckets()['Buckets']


# aws s3api get-bucket-versioning --region us-gov-west-1 --bucket <bucket_name>
def check_bucket_versioning(bucket_issues={}):
    count = 0

    for bucket in BUCKETS:
        bucket_name = bucket['Name']

        try:
            response = S3_CLIENT.get_bucket_versioning(
                Bucket=bucket_name,
                ExpectedBucketOwner=AWS_ACCOUNT)

            if 'Status' not in response or response['Status'] != 'Enabled':
                cis_id = "2.1.3"
                msg = 'Versioning not enabled'
                LOGGER.warning(f'{msg} for {bucket_name}')

                if bucket_name not in bucket_issues.keys():
                    bucket_issues[bucket_name] = []

                if msg not in bucket_issues[bucket_name]:
                    bucket_issues[bucket_name].append({cis_id: msg})

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {bucket_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

        count += 1

    print(f'{count} BUCKETS for AWS acct {AWS_ACCOUNT}')
    return bucket_issues


# aws s3api get-bucket-encryption --region us-gov-west-1 --bucket <bucket_name>
def check_bucket_encryption(bucket_issues={}):
    count = 0

    for bucket in BUCKETS:
        bucket_name = bucket['Name']
        encryption_exists = False

        try:
            response = S3_CLIENT.get_bucket_encryption(
                Bucket=bucket_name,
                ExpectedBucketOwner=AWS_ACCOUNT
            )

            for rule in response['ServerSideEncryptionConfiguration']['Rules']:

                if(rule['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'] == 'AES256'):
                    encryption_exists = True
                    # encryption = rule['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']
                    # msg = f'encryption: {encryption}'
                    # LOGGER.info(msg)
                    break

                if(rule['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'] == 'aws:kms'):
                    encryption_exists = True
                    # encryption = rule['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']
                    # msg = f'encryption: {encryption}'
                    # LOGGER.info(msg)
                    break

            if(not encryption_exists):
                cis_id = "2.1.1"
                encryption = rule['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']
                msg = f'Incorrect server side encryption ({encryption})'
                LOGGER.warning(f'{msg} for {bucket_name}')

                if bucket_name not in bucket_issues.keys():
                    bucket_issues[bucket_name] = []

                if msg not in bucket_issues[bucket_name]:
                    bucket_issues[bucket_name].append({cis_id: msg})

        except S3_CLIENT.exceptions.from_code('ServerSideEncryptionConfigurationNotFoundError'):
            msg = 'NO server side encryption config'
            LOGGER.error(f'{msg} for {bucket_name}')

            if bucket_name not in bucket_issues.keys():
                bucket_issues[bucket_name] = []

            if msg not in bucket_issues[bucket_name]:
                bucket_issues[bucket_name].append({msg})

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {bucket_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

        count += 1

    print(f'{count} BUCKETS for AWS acct {AWS_ACCOUNT}')
    return bucket_issues


# aws s3api get-bucket-policy --region us-gov-west-1 --bucket <bucket_name> | grep aws:SecureTransport
def check_bucket_policy(bucket_issues={}):
    count = 0

    for bucket in BUCKETS:
        bucket_name = bucket['Name']
        ssl_key_exists = False

        try:
            response = S3_CLIENT.get_bucket_policy(
                Bucket=bucket_name,
                ExpectedBucketOwner=AWS_ACCOUNT)

            policy_json = json.loads(response['Policy'])

            for statement in policy_json['Statement']:
                if 'Condition' in statement.keys() and 'Bool' in statement['Condition'].keys():
                    if statement['Condition']['Bool']['aws:SecureTransport'] == 'false':
                        ssl_key_exists = True
                        LOGGER.info(f'SSL enforced for {bucket_name}')
                        break

            if(not ssl_key_exists):
                cis_id = "2.1.2"
                msg = 'SSL NOT enforced'
                LOGGER.warning(f'{msg} for {bucket_name}')

                if bucket_name not in bucket_issues.keys():
                    bucket_issues[bucket_name] = []

                if msg not in bucket_issues[bucket_name]:
                    bucket_issues[bucket_name].append({cis_id: msg})

        except S3_CLIENT.exceptions.from_code('NoSuchBucketPolicy'):
            msg = 'NO Bucket Policy'
            LOGGER.error(f'{msg} for {bucket_name}')

            if bucket_name not in bucket_issues.keys():
                bucket_issues[bucket_name] = []

            if msg not in bucket_issues[bucket_name]:
                bucket_issues[bucket_name].append(msg)

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {bucket_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

        count += 1

    print(f'{count} BUCKETS for AWS acct {AWS_ACCOUNT}')
    return bucket_issues


# 2.1.5, 3.3

# $ aws s3api get-bucket-policy --bucket <bucket_name>

# aws s3api get-public-access-block --region us-gov-west-1 --bucket <bucket_name>
def check_bucket_public_access(bucket_issues={}):
    count = 0

    for bucket in BUCKETS:
        bucket_name = bucket['Name']
        public_access_block_exists = False
        restricted_alluser_acl_exists = False
        restricted_privuser_acl_exists = False
        restricted_anonymous_access_exists = False

        # Public Access Block Configuration
        try:
            # aws s3api get-bucket-acl --region us-gov-west-1 --bucket <bucket_name>
            pab_response = S3_CLIENT.get_public_access_block(
                Bucket=bucket_name,
                ExpectedBucketOwner=AWS_ACCOUNT)

            if pab_response['PublicAccessBlockConfiguration']:
                public_access_block_exists = True
                # msg = f'{bucket_name} has {pab_response["PublicAccessBlockConfiguration"]}'
                # LOGGER.info(msg)

        except S3_CLIENT.exceptions.from_code('NoSuchPublicAccessBlockConfiguration'):
            msg = 'NO public access block configuration'
            # LOGGER.error(f'{msg} for {bucket_name}')

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {bucket_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

        # Access Control List restricting Public Access
        try:
            acl_response = S3_CLIENT.get_bucket_acl(
                Bucket=bucket_name,
                ExpectedBucketOwner=AWS_ACCOUNT)

            # $ aws s3api get-bucket-acl --bucket <bucket_name> --query 'Grants[?Grantee.URI== `http://acs.amazonaws.com/groups/global/AllUsers` ]'
            # $ aws s3api get-bucket-acl --bucket <bucket_name> --query 'Grants[?Grantee.URI== `http://acs.amazonaws.com/groups/global/AuthenticatedUsers` ]'
            # FIXME if URI for s3 logging exists, http://acs.amazonaws.com/groups/s3/LogDelivery, Anonymous User access logic is skipped?
            for grant in acl_response['Grants']:
                if 'http://acs.amazonaws.com/groups/global/AllUsers' not in grant['Grantee'].values():
                    restricted_alluser_acl_exists = True

                if 'http://acs.amazonaws.com/groups/global/AuthenticatedUsers' not in grant['Grantee'].values():
                    restricted_privuser_acl_exists = True

            # Bucket policy dis-allowing Anonymous User Access
            policy_response = S3_CLIENT.get_bucket_policy(
                Bucket=bucket_name,
                ExpectedBucketOwner=AWS_ACCOUNT)

            policy_json = json.loads(policy_response['Policy'])

            for policy in policy_json['Statement']:
                if(not (policy['Effect'] == 'Allow' and policy['Principal'] == '*')):
                    restricted_anonymous_access_exists = True

        except S3_CLIENT.exceptions.from_code('NoSuchBucketPolicy'):
            msg = 'NO Bucket Policy'
            LOGGER.error(f'{msg} for {bucket_name}')

            if bucket_name not in bucket_issues.keys():
                bucket_issues[bucket_name] = []

            if msg not in bucket_issues[bucket_name]:
                bucket_issues[bucket_name].append(msg)

        except KeyError as key_err:
            msg = f"No such key {key_err} found"
            LOGGER.error(f'{msg} for {bucket_name}')

        except ClientError as client_error:
            LOGGER.error(f'ClientError: {client_error}')

        # Final LOGIC
        if(public_access_block_exists or (restricted_alluser_acl_exists and restricted_privuser_acl_exists and restricted_anonymous_access_exists)):
            msg = "Public Access blocked"
            # LOGGER.info(f'{msg} for {bucket_name}')
            count += 1

        else:
            cis_id = "2.1.5"

            if(not public_access_block_exists):
                msg = 'NO Public Access Block configuration'

                if bucket_name not in bucket_issues.keys():
                    bucket_issues[bucket_name] = []

                if msg not in bucket_issues[bucket_name]:
                    bucket_issues[bucket_name].append({cis_id: msg})

            if(not restricted_alluser_acl_exists):
                msg = "AllUser access"

                if bucket_name not in bucket_issues.keys():
                    bucket_issues[bucket_name] = []

                if msg not in bucket_issues[bucket_name]:
                    bucket_issues[bucket_name].append({cis_id: msg})

            if(not restricted_privuser_acl_exists):
                msg = "AuthenticatedUsers access"

                if bucket_name not in bucket_issues.keys():
                    bucket_issues[bucket_name] = []

                if msg not in bucket_issues[bucket_name]:
                    bucket_issues[bucket_name].append({cis_id: msg})

            if(not restricted_anonymous_access_exists):
                msg = 'Anonymous Principal access'

                if bucket_name not in bucket_issues.keys():
                    bucket_issues[bucket_name] = []

                if msg not in bucket_issues[bucket_name]:
                    bucket_issues[bucket_name].append({cis_id: msg})

            count += 1

    print(f'{count} BUCKETS for AWS acct {AWS_ACCOUNT}')
    return bucket_issues
