import boto3
from botocore.exceptions import ClientError

from aws_modules.cis_error_logger import cis_issue_logger

import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger()

REGION = 'us-gov-west-1'
IAM_CLIENT = boto3.client('iam', region_name=REGION)
IAM_RESOURCE = boto3.resource('iam', region_name=REGION)


# aws iam list-users --query "Users[*].UserName"
def print_iam():
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
    return


def check_password_policy(iam_issues: dict = {}, password_min: int = 14, password_reuse: int = 24) -> dict:
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
