from unittest.mock import Mock, call

import pytest

from harnessiq.providers.gcloud import GcloudError, GcpAgentConfig
from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.deploy import (
    ArtifactRegistryProvider,
    CloudRunProvider,
)


def _config() -> GcpAgentConfig:
    return GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
        env_vars={"HARNESSIQ_AGENT_MODULE": "harnessiq.agents.linkedin"},
        secrets=[{"env_var": "ANTHROPIC_API_KEY", "secret_name": "HARNESSIQ_ANTHROPIC_API_KEY"}],
    )


def _gcloud_error(*parts: str, stderr: str = "not found") -> GcloudError:
    return GcloudError(command=tuple(parts or ("gcloud",)), exit_code=1, stderr=stderr)


def test_artifact_registry_repository_exists_checks_describe() -> None:
    client = Mock()
    provider = ArtifactRegistryProvider(client, _config())

    client.run_json.return_value = {"name": "harnessiq"}
    assert provider.repository_exists() is True
    client.run_json.assert_called_once_with(
        cmd.describe_repository("harnessiq", "us-central1")
    )

    client.run_json.reset_mock(side_effect=True)
    client.run_json.side_effect = _gcloud_error("gcloud", "artifacts")
    assert provider.repository_exists() is False

    client.run_json.side_effect = _gcloud_error("gcloud", "artifacts", stderr="permission denied")
    with pytest.raises(GcloudError):
        provider.repository_exists()


def test_artifact_registry_ensure_repository_creates_only_when_missing() -> None:
    client = Mock()
    provider = ArtifactRegistryProvider(client, _config())

    client.run_json.side_effect = _gcloud_error("gcloud", "artifacts")
    provider.ensure_repository()

    client.run.assert_called_once_with(cmd.create_repository("harnessiq", "us-central1"))

    client.reset_mock(return_value=True, side_effect=True)
    client.run_json.return_value = {"name": "harnessiq"}
    provider.ensure_repository()
    client.run.assert_not_called()


def test_artifact_registry_build_and_list_flows_use_command_builders() -> None:
    client = Mock()
    provider = ArtifactRegistryProvider(client, _config())

    client.run_json.return_value = {"name": "harnessiq"}
    client.run.return_value = "submitted"
    client.run_json.side_effect = None

    assert provider.build_image("src") == "submitted"
    assert client.run.call_args_list == [
        call(cmd.submit_build(_config().image_url, "src"))
    ]

    client.reset_mock()
    client.run_json.return_value = [{"package": "candidate-a"}]
    assert provider.list_images() == [{"package": "candidate-a"}]
    client.run_json.assert_called_once_with(
        cmd.list_images(
            "us-central1-docker.pkg.dev/proj-123/harnessiq",
            "us-central1",
        )
    )

    client.reset_mock()
    provider.delete_image()
    client.run.assert_called_once_with(cmd.delete_image(_config().image_url))


def test_cloud_run_job_exists_and_describe_use_builder_commands() -> None:
    client = Mock()
    provider = CloudRunProvider(client, _config())

    client.run_json.return_value = {"name": "harnessiq-candidate-a"}
    assert provider.job_exists() is True
    client.run_json.assert_called_once_with(
        cmd.describe_job("harnessiq-candidate-a", "us-central1")
    )

    client.run_json.reset_mock(side_effect=True)
    client.run_json.side_effect = _gcloud_error("gcloud", "run")
    assert provider.job_exists() is False

    client.run_json.side_effect = _gcloud_error("gcloud", "run", stderr="permission denied")
    with pytest.raises(GcloudError):
        provider.job_exists()

    client.run_json.reset_mock(side_effect=True)
    client.run_json.side_effect = None
    client.run_json.return_value = {"name": "harnessiq-candidate-a"}
    assert provider.describe() == {"name": "harnessiq-candidate-a"}


def test_cloud_run_deploy_branches_between_create_and_update() -> None:
    client = Mock()
    provider = CloudRunProvider(client, _config())
    spec = cmd.JobSpec.from_config(_config())

    client.run_json.return_value = {"name": _config().job_name}
    client.run.return_value = "updated"
    assert provider.deploy_job() == "updated"
    client.run.assert_called_once_with(cmd.update_job(spec))

    client.reset_mock()
    client.run_json.side_effect = _gcloud_error("gcloud", "run")
    client.run.return_value = "created"
    assert provider.deploy_job() == "created"
    client.run.assert_called_once_with(cmd.create_job(spec))


def test_cloud_run_execute_and_execution_management_use_builders() -> None:
    client = Mock()
    provider = CloudRunProvider(client, _config())

    client.run.return_value = "execution-1"
    assert (
        provider.execute(
            wait=True,
            task_count=3,
            timeout_override=900,
            env_overrides={"FOO": "bar"},
        )
        == "execution-1"
    )
    client.run.assert_called_once_with(
        cmd.execute_job(
            _config().job_name,
            _config().region,
            cmd.ExecutionOptions(
                wait=True,
                task_count=3,
                timeout_override=900,
                env_overrides={"FOO": "bar"},
            ),
        )
    )

    client.reset_mock()
    client.run_json.return_value = [{"name": "exec-1"}]
    assert provider.list_executions(limit=3) == [{"name": "exec-1"}]
    client.run_json.assert_called_once_with(
        cmd.list_executions(_config().job_name, _config().region, 3)
    )

    client.reset_mock()
    provider.cancel_execution("exec-1")
    client.run.assert_called_once_with(cmd.cancel_execution("exec-1", _config().region))

    client.reset_mock()
    provider.delete()
    client.run.assert_called_once_with(cmd.delete_job(_config().job_name, _config().region))
