from my_modules.benchmarker import print_execution_time

from aws_modules.aws_s3 import check_bucket_encryption, check_bucket_policy, check_bucket_public_access, check_bucket_versioning
from aws_modules.aws_cloudtrails import check_cloudtrail, check_cloudwatch_is_logging


def main():
    # no_of_runs = 2
    # print_execution_time(check_bucket_encryption.__name__, no_of_runs)

    # bucket_issues = check_bucket_encryption()
    # bucket_issues = check_bucket_policy(bucket_issues)
    # bucket_issues = check_bucket_public_access(bucket_issues)
    # bucket_issues = check_bucket_versioning()
    # print(bucket_issues)

    # trails = check_cloudtrail()
    trail_issues = check_cloudwatch_is_logging()
    print(trail_issues)


if __name__ == '__main__':
    main()
