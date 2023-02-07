#! /usr/bin/env python3

from my_modules.benchmarker import print_execution_time
from my_modules.ipv4_parser import parse_ips_into_list, sort_ipv4

from aws_modules.aws_s3 import check_bucket_encryption, check_bucket_policy, check_bucket_public_access, check_bucket_versioning
from aws_modules.aws_cloudtrails import check_cloudtrail, check_cloudwatch_is_logging
from aws_modules.aws_instances import print_list, print_rds_instances, print_ec2_instances, sort_and_filter_amis, keep_latest_amis, deregister_amis, delete_snapshots, delete_volumes


def main():
    # no_of_runs = 2
    # print_execution_time(check_bucket_encryption.__name__, no_of_runs)

    # bucket_issues = {}
    # bucket_issues = check_bucket_encryption(bucket_issues)
    # bucket_issues = check_bucket_policy(bucket_issues)
    # bucket_issues = check_bucket_public_access(bucket_issues)
    # bucket_issues = check_bucket_versioning(bucket_issues)
    # print(bucket_issues)

    # trail_issues = check_cloudtrail()
    # trail_issues = check_cloudwatch_is_logging(trail_issues)
    # print(trail_issues)

    # print_ec2_instances()

    amis = sort_and_filter_amis()
    amis = keep_latest_amis(amis)
    amis = deregister_amis(amis)
    delete_snapshots(amis[1])
    delete_volumes()


if __name__ == '__main__':
    main()
