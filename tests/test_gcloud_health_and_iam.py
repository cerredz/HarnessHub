from pathlib import Path
from unittest.mock import Mock, call

import pytest

from harnessiq.providers.gcloud import GcloudError, GcpAgentConfig
from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.health import HealthProvider
from harnessiq.providers.gcloud.infra import IamProvider, REQUIRED_ROLES


def _config() -> GcpAgentConfig:
    return GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
    )


def _gcloud_error(*parts: str, stderr: str = "not found") -> GcloudError:
    return GcloudError(command=tuple(parts or ("gcloud",)), exit_code=1, stderr=stderr)


def test_health_provider_reports_cli_install_auth_and_adc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    client = Mock()
    provider = HealthProvider(client, _config())

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/gcloud" if name == "gcloud" else None)
    client.run.return_value = "user@example.test"
    adc_path = tmp_path / "adc.json"
    adc_path.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(adc_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    assert provider.check_gcloud_installed().passed is True
    assert provider.check_gcloud_auth().passed is True
    assert provider.check_adc().passed is True
    assert provider.check_anthropic_key_local().passed is True


def test_health_provider_distinguishes_missing_cli_auth_and_adc(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Mock()
    provider = HealthProvider(client, _config())

    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client.run.side_effect = _gcloud_error("gcloud", "auth", stderr="not logged in")

    assert provider.check_gcloud_installed().passed is False
    assert provider.check_gcloud_auth().passed is False
    assert provider.check_adc().passed is False
    assert provider.check_anthropic_key_local().passed is False


def test_health_provider_checks_api_enablement_and_secret_access() -> None:
    client = Mock()
    provider = HealthProvider(client, _config())

    client.run.side_effect = [
        "run.googleapis.com",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]
    api_results = provider.check_apis_enabled()
    assert api_results[0].passed is True
    assert api_results[1].passed is False
    assert api_results[1].fix == "gcloud services enable artifactregistry.googleapis.com --project=proj-123"

    client.run.reset_mock(side_effect=True)
    client.run_json.return_value = {
        "bindings": [
            {
                "role": "roles/secretmanager.secretAccessor",
                "members": ["serviceAccount:runner@proj-123.iam.gserviceaccount.com"],
            }
        ]
    }
    secret_access = provider.check_service_account_secret_access()
    assert secret_access.passed is True


def test_health_provider_validate_all_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Mock()
    provider = HealthProvider(client, _config())

    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client.run.side_effect = _gcloud_error("gcloud", "auth", stderr="not logged in")
    client.run_json.return_value = {"bindings": []}

    with pytest.raises(RuntimeError, match="Health check failed"):
        provider.validate_all(fail_fast=True)


def test_iam_provider_create_describe_and_missing_roles(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Mock()
    config = _config()
    provider = IamProvider(client, config)
    monkeypatch.setattr(type(config), "save", lambda self, home_dir=None: Path("fake.json"))

    client.run.return_value = "created"
    sa_email = provider.create_service_account()
    assert sa_email == "harnessiq-runner@proj-123.iam.gserviceaccount.com"
    assert config.service_account_email == sa_email
    client.run.assert_called_once_with(
        cmd.create_service_account(
            cmd.ServiceAccountSpec(
                sa_id="harnessiq-runner",
                project_id="proj-123",
                display_name="HarnessIQ Cloud Run Runner",
            )
        )
    )

    client.reset_mock()
    client.run_json.return_value = {"email": sa_email}
    assert provider.describe_service_account() == {"email": sa_email}

    client.reset_mock()
    client.run_json.return_value = {
        "bindings": [
            {
                "role": "roles/secretmanager.secretAccessor",
                "members": [f"serviceAccount:{sa_email}"],
            },
            {
                "role": "roles/storage.objectAdmin",
                "members": [f"serviceAccount:{sa_email}"],
            },
        ]
    }
    assert provider.list_granted_roles() == [
        "roles/secretmanager.secretAccessor",
        "roles/storage.objectAdmin",
    ]
    assert provider.missing_roles() == [
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
        "roles/artifactregistry.reader",
    ]


def test_iam_provider_grants_required_roles_and_falls_back_to_default_compute_sa() -> None:
    client = Mock()
    config = GcpAgentConfig(agent_name="candidate-a", gcp_project_id="proj-123", region="us-central1")
    provider = IamProvider(client, config)

    client.run.side_effect = ["123456789", *["ok" for _ in REQUIRED_ROLES]]
    provider.grant_required_roles()

    expected_calls = [
        call(cmd.describe_project("proj-123", value_field="projectNumber")),
        *[
            call(
                cmd.add_iam_binding(
                    cmd.IamBinding(
                        project_id="proj-123",
                        member="serviceAccount:123456789-compute@developer.gserviceaccount.com",
                        role=role,
                    )
                )
            )
            for role in REQUIRED_ROLES
        ],
    ]
    assert client.run.call_args_list == expected_calls
