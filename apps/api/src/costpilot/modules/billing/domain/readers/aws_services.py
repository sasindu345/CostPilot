"""Groups AWS services into FOCUS service categories."""

OTHER_CATEGORY = "Other"

SERVICE_CATEGORIES = {
    "amazonec2": "Compute",
    "ec2": "Compute",
    "ec2-instances": "Compute",
    "ec2-other": "Compute",
    "amazon elastic compute cloud": "Compute",
    "amazon elastic compute cloud - compute": "Compute",
    "awslambda": "Compute",
    "lambda": "Compute",
    "aws lambda": "Compute",
    "amazonecs": "Compute",
    "amazoneks": "Compute",
    "amazons3": "Storage",
    "s3": "Storage",
    "amazon simple storage service": "Storage",
    "amazonefs": "Storage",
    "amazonrds": "Databases",
    "rds": "Databases",
    "amazon relational database service": "Databases",
    "amazondynamodb": "Databases",
    "dynamodb": "Databases",
    "amazon dynamodb": "Databases",
    "amazonelasticache": "Databases",
    "awsdatatransfer": "Networking",
    "amazoncloudfront": "Networking",
    "cloudfront": "Networking",
    "amazonvpc": "Networking",
    "amazonroute53": "Networking",
    "awscloudtrail": "Management and Governance",
    "amazoncloudwatch": "Management and Governance",
    "cloudwatch": "Management and Governance",
}


def service_category(service_name: str) -> str:
    return SERVICE_CATEGORIES.get(service_name.strip().lower(), OTHER_CATEGORY)
