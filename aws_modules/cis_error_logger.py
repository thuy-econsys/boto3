cis_dict = {
    "2.1.1": [
        "Incorrect server side encryption",
        "NO server side encryption config"
    ],
    "2.1.2": ["SSL NOT enforced"],
    "2.1.3": ["Versioning not enabled"],
    "2.1.5": [
        "NO Public Access Block configuration",
        "AllUser access",
        "AuthenticatedUsers access",
        "Anonymous user access"
    ],
    "2.2.1": ["EBS encryption disabled"],
    "2.3.1": ["RDS encryption disabled"],
    "2.3.2": ["RDS Auto Minor Version Upgrade disabled"],
    "2.3.3": ["RDS Publicly Accessible"],
    "3.1": ["Multi-region is not enabled for any trails"],
    "3.2": ["Logfile validation is not enabled"],
    "3.4": ["CloudWatch is not being logged"],
    "3.6": ["Logging not enabled"]
}


def cis_issue_logger(item, issues, cis_id, index=0):
    msg = cis_dict[cis_id][index]

    if item not in issues.keys():
        issues[item] = {}

    if cis_id not in issues[item].keys():
        issues[item].update({cis_id: []})

    if msg not in issues[item][cis_id]:
        issues[item][cis_id].append(msg)

    return issues
