from uuid import uuid4

import pytest

from costpilot.modules.identity.application.account_service import AccountService
from costpilot.modules.identity.domain.errors import (
    DeletionNotConfirmedError,
    IdentityProviderError,
)
from costpilot.modules.identity.domain.models import CurrentUser

USER = CurrentUser(
    user_id=uuid4(),
    email="Owner@Example.test",
    display_name="Owner",
    workspace_id=uuid4(),
    workspace_name="My workspace",
    role="owner",
)


class Recorder:
    def __init__(self, keycloak_fails=False):
        self.steps = []
        self.keycloak_fails = keycloak_fails

    async def export_workspace(self, user):
        self.steps.append("export")
        return "{}"

    async def find_subject(self, user):
        return "subject-1"

    async def delete_account(self, user):
        self.steps.append("delete data")

    async def workspace_file_keys(self, user):
        return ["a", "b"]

    async def delete_files(self, keys):
        self.steps.append(f"delete files {keys}")

    async def delete_user(self, subject):
        if self.keycloak_fails:
            raise IdentityProviderError
        self.steps.append(f"delete login {subject}")

    async def record(self, **event):
        self.steps.append(event["action"])


def service(recorder):
    return AccountService(recorder, recorder, recorder, recorder)


async def test_deletion_removes_data_then_files_then_the_login():
    recorder = Recorder()

    await service(recorder).delete(USER, " owner@example.TEST ")

    assert recorder.steps == ["delete data", "delete files ['a', 'b']", "delete login subject-1"]


async def test_deletion_needs_the_exact_email():
    recorder = Recorder()

    with pytest.raises(DeletionNotConfirmedError):
        await service(recorder).delete(USER, "someone@else.test")

    assert recorder.steps == []


async def test_a_keycloak_failure_does_not_undo_the_deletion():
    recorder = Recorder(keycloak_fails=True)

    await service(recorder).delete(USER, USER.email)

    assert recorder.steps == ["delete data", "delete files ['a', 'b']"]


async def test_each_export_is_recorded_in_the_audit_log():
    recorder = Recorder()

    assert await service(recorder).export(USER) == "{}"
    assert recorder.steps == ["account.exported", "export"]
