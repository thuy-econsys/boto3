import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone

from aws_modules.cis_error_logger import cis_issue_logger

import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger()

REGION = 'us-gov-west-1'
IAM_CLIENT = boto3.client('iam', region_name=REGION)
IAM_RESOURCE = boto3.resource('iam', region_name=REGION)


# aws iam list-users --query "Users[*].UserName"
def print_iam(iam_issues: dict = {},) -> dict:

    try:
        user = 'thuy'
        keys = IAM_CLIENT.list_access_keys(UserName=user)
        mfas = IAM_CLIENT.list_mfa_devices(UserName=user)

        if len(mfas['MFADevices']) < 0:
            issue = "No MFA device listed for {user}"
            # iam_issues = cis_issue_logger(issue, iam_issues, cis_id='1.5')

        if (keys['AccessKeyMetadata']) and (len(keys['AccessKeyMetadata']) > 0):
            issue = "Access keys for {user} exists."
            print(f"# of keys: {len(keys['AccessKeyMetadata'])}")
            # iam_issues = cis_issue_logger(issue, iam_issues, cis_id='1.4')

        else:
            print("No active access keys for root/Break-glass User")

    except ClientError as client_error:
        LOGGER.error(f'ClientError: {client_error}')

    # iam_paginator = IAM_CLIENT.get_paginator('list_user_policies')
    # iam_response = IAM_CLIENT.list

    # # lists all policies but no password policy check
    # policies = IAM_RESOURCE.policies.filter(
    #     Scope='AWS',
    #     OnlyAttached=True
    # )

    # print(f"resource: {policies}") # iam.policiesCollection(iam.ServiceResource(), iam.Policy)
    # for policy in policies:
    #     # print(f"{policy}")
    #     print(f"{policy.arn}")

    # print(f"client: {iam_paginator}") # botocore.client.IAM.Paginator.ListUserPolicies object at 0x7fd1d3bacf70>
    # print(f"{iam_paginator}")

    return iam_issues


# 1.17 Ensure a support role has been created to manage incidents with AWS Support
# 1.18 Ensure IAM instance roles are used for AWS resource access from instances
def list_instance_roles(iam_issues: dict = {},) -> dict:
    try:
        roles = IAM_CLIENT.list_roles()

        for role in roles['Roles']:
            print(f"{role['RoleName']}")
            print(f"{role['AssumeRolePolicyDocument']['Statement']}")

        # issue = ''
        # iam_issues = cis_issue_logger(issue, iam_issues, cis_id='1.18')
    
    except ClientError as client_error:
        LOGGER.error(f'ClientError: {client_error}')

    return iam_issues


# 1.4 Ensure no 'root' user account access key exists
# 1.5 Ensure MFA is enabled for the 'root' user account
# 1.6 Ensure hardware MFA is enabled for the 'root' user account Level 2
# 1.7 Eliminate use of the 'root' user for administrative and daily tasks N/A
def list_root_user_creds(iam_issues: dict = {},) -> dict:
    
    try:
        summary = IAM_CLIENT.get_account_summary()

        if summary['SummaryMap']['AccountMFAEnabled'] < 1:
            issue = "root user MFA"
            iam_issues = cis_issue_logger(issue, iam_issues, cis_id='1.5')

        if summary['SummaryMap']['AccountAccessKeysPresent'] != 0:
            issue = "root user Access Key"
            iam_issues = cis_issue_logger(issue, iam_issues, cis_id='1.4')

    except ClientError as client_error:
        LOGGER.error(f'ClientError: {client_error}')

    return iam_issues


# 1.12 Ensure credentials unused for 45 days or greater are disabled
# 1.11 Do not setup access keys during initial user setup for all IAM users that have a console password
# 1.13 Ensure there is only one active access key available for any single IAM user
# 1.14 Ensure access keys are rotated every 90 days or less
# 1.15 Ensure IAM Users Receive Permissions Only Through Groups
def list_user_creds():
    try:
        users = IAM_CLIENT.list_users()
        # print(users['Users'])

        for user in users['Users']:
            print(f"last {user['UserName']} console login: {user['PasswordLastUsed']}")

            keys = IAM_CLIENT.list_access_keys(UserName=user['UserName'])
            # print(keys)
            # print(keys['AccessKeyMetadata'])

            if keys['AccessKeyMetadata']:
                print(f"# of keys: {len(keys['AccessKeyMetadata'])}")

                for key in keys['AccessKeyMetadata']:
                    print(f"{key['UserName']} key: {key['AccessKeyId']}, status: {key['Status']}")
            else:
                print("No active access keys for IAM Users")

    except ClientError as client_error:
        LOGGER.error(f'ClientError: {client_error}')


def check_password_policy(
    iam_issues: dict = {},
    password_min: int = 14,
    password_reuse: int = 24
) -> dict:
    try:
        policy_json = IAM_CLIENT.get_account_password_policy()

        if not policy_json:
            print('No PasswordPolicy found')
            return

        if policy_json['PasswordPolicy']['MinimumPasswordLength'] < password_min:
            issue = 'MinimumPasswordLength'
            # print(f"MinimumPasswordLength {policy_json['PasswordPolicy']['MinimumPasswordLength']}")
            iam_issues = cis_issue_logger(issue, iam_issues, cis_id='1.8')

        if policy_json['PasswordPolicy']['PasswordReusePrevention'] != password_reuse:
            issue = 'PasswordReusePrevention'
            # print(f"PasswordReusePrevention {policy_json['PasswordPolicy']['PasswordReusePrevention']}")
            iam_issues = cis_issue_logger(issue, iam_issues, cis_id='1.9')

    except ClientError as client_error:
        LOGGER.error(f'ClientError: {client_error}')

    return iam_issues
