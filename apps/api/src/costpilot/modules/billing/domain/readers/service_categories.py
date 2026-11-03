"""Groups each cloud's services into FOCUS service categories. Unknown services become Other."""

OTHER_CATEGORY = "Other"

CATEGORIES = {
    "azure": {
        "virtual machines": "Compute",
        "virtual machines licenses": "Compute",
        "azure app service": "Compute",
        "functions": "Compute",
        "container instances": "Compute",
        "storage": "Storage",
        "sql database": "Databases",
        "azure cosmos db": "Databases",
        "azure database for postgresql": "Databases",
        "bandwidth": "Networking",
        "virtual network": "Networking",
        "load balancer": "Networking",
        "azure monitor": "Management and Governance",
        "log analytics": "Management and Governance",
    },
    "gcp": {
        "compute engine": "Compute",
        "cloud run": "Compute",
        "cloud functions": "Compute",
        "kubernetes engine": "Compute",
        "cloud storage": "Storage",
        "cloud sql": "Databases",
        "bigquery": "Analytics",
        "networking": "Networking",
        "cloud logging": "Management and Governance",
        "cloud monitoring": "Management and Governance",
    },
    "oci": {
        "compute": "Compute",
        "block_storage": "Storage",
        "object_storage": "Storage",
        "file_storage": "Storage",
        "database": "Databases",
        "autonomous_database": "Databases",
        "network": "Networking",
        "load_balancer": "Networking",
    },
    "digitalocean": {
        "droplets": "Compute",
        "app platform": "Compute",
        "kubernetes": "Compute",
        "volumes": "Storage",
        "spaces": "Storage",
        "snapshots": "Storage",
        "backups": "Storage",
        "databases": "Databases",
        "load balancers": "Networking",
        "floating ips": "Networking",
        "reserved ips": "Networking",
    },
}


def category(provider: str, service: str) -> str:
    return CATEGORIES.get(provider, {}).get(service.strip().lower(), OTHER_CATEGORY)
