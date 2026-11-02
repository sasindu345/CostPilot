import asyncio
from pathlib import Path

import boto3

SERVER_SIDE_ENCRYPTION = "AES256"


class S3FileStorage:
    """Keeps files in a private S3 bucket, encrypted by S3. See decision 0004."""

    def __init__(self, bucket: str, region: str) -> None:
        self._bucket = bucket
        self._client = boto3.client("s3", region_name=region)

    async def put(self, key: str, source: Path) -> None:
        await asyncio.to_thread(
            self._client.upload_file,
            str(source),
            self._bucket,
            key,
            ExtraArgs={"ServerSideEncryption": SERVER_SIDE_ENCRYPTION},
        )

    async def fetch(self, key: str, destination: Path) -> None:
        await asyncio.to_thread(self._client.download_file, self._bucket, key, str(destination))

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)
