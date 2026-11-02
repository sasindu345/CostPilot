"""Both storage types must behave the same way."""

import boto3
import pytest
from moto import mock_aws

from costpilot.modules.documents.infrastructure.local_storage import LocalFileStorage
from costpilot.modules.documents.infrastructure.s3_storage import S3FileStorage

BUCKET = "test-bucket"
REGION = "us-east-1"


@pytest.fixture(params=["local", "s3"])
def storage(request, tmp_path, monkeypatch):
    if request.param == "local":
        yield LocalFileStorage(str(tmp_path / "root"))
        return
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    with mock_aws():
        boto3.client("s3", region_name=REGION).create_bucket(Bucket=BUCKET)
        yield S3FileStorage(bucket=BUCKET, region=REGION)


async def test_a_stored_file_comes_back_unchanged(storage, tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"bill contents")
    destination = tmp_path / "destination"

    await storage.put("workspace/document", source)
    await storage.fetch("workspace/document", destination)

    assert destination.read_bytes() == b"bill contents"


async def test_a_deleted_file_is_gone(storage, tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"bill contents")
    await storage.put("workspace/document", source)

    await storage.delete("workspace/document")

    with pytest.raises(Exception):  # noqa: B017
        await storage.fetch("workspace/document", tmp_path / "destination")


async def test_deleting_a_missing_file_is_safe(storage):
    await storage.delete("workspace/missing")


async def test_local_storage_refuses_to_leave_its_folder(tmp_path):
    storage = LocalFileStorage(str(tmp_path / "root"))

    with pytest.raises(ValueError, match="leaves"):
        await storage.delete("../outside")


async def test_s3_files_are_encrypted(tmp_path, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    source = tmp_path / "source"
    source.write_bytes(b"bill contents")

    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        client.create_bucket(Bucket=BUCKET)
        await S3FileStorage(bucket=BUCKET, region=REGION).put("key", source)
        response = client.head_object(Bucket=BUCKET, Key="key")

    assert response["ServerSideEncryption"] == "AES256"
