from __future__ import annotations

from pathlib import Path

import pytest

from harnessiq.providers.gcloud import DEFAULT_GCP_CONFIG_DIRNAME, GcpAgentConfig


def test_config_round_trips_through_disk(tmp_path: Path) -> None:
    config = GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        env_vars={"HARNESSIQ_AGENT": "candidate-a"},
        secrets=[{"env_var": "ANTHROPIC_API_KEY", "secret_name": "HARNESSIQ_ANTHROPIC_API_KEY"}],
    )

    saved_path = config.save(home_dir=tmp_path)
    loaded = GcpAgentConfig.load("candidate-a", home_dir=tmp_path)

    assert saved_path == tmp_path / DEFAULT_GCP_CONFIG_DIRNAME / "candidate-a.json"
    assert loaded.as_dict() == config.as_dict()
    assert loaded.image_url == "us-central1-docker.pkg.dev/proj-123/harnessiq/candidate-a:latest"


def test_config_applies_default_names_from_agent_name() -> None:
    config = GcpAgentConfig(
        agent_name="Candidate A",
        gcp_project_id="proj-123",
        region="us-central1",
    )

    assert config.image_name == "candidate-a"
    assert config.job_name == "harnessiq-candidate-a"
    assert config.scheduler_job_name == "harnessiq-candidate-a-schedule"


def test_load_raises_when_config_is_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="candidate-a"):
        GcpAgentConfig.load("candidate-a", home_dir=tmp_path)


def test_load_rejects_mismatched_agent_name_in_file(tmp_path: Path) -> None:
    config = GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
    )
    path = config.save(home_dir=tmp_path)
    path.write_text(
        path.read_text(encoding="utf-8").replace('"agent_name": "candidate-a"', '"agent_name": "candidate-b"'),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="candidate-b"):
        GcpAgentConfig.load("candidate-a", home_dir=tmp_path)


def test_config_path_for_rejects_blank_agent_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="agent_name"):
        GcpAgentConfig.config_path_for("   ", home_dir=tmp_path)


def test_config_rejects_blank_required_fields() -> None:
    with pytest.raises(ValueError, match="gcp_project_id"):
        GcpAgentConfig(agent_name="candidate-a", gcp_project_id=" ", region="us-central1")

    with pytest.raises(ValueError, match="region"):
        GcpAgentConfig(agent_name="candidate-a", gcp_project_id="proj-123", region=" ")


def test_config_normalizes_optional_fields_and_secret_entries() -> None:
    config = GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        service_account_email="  runner@proj-123.iam.gserviceaccount.com  ",
        manifest_id=" linkedin ",
        schedule_cron=" 0 8 * * * ",
        secrets=[{"env_var": " LINKEDIN_EMAIL ", "secret_name": " HARNESSIQ_LINKEDIN_EMAIL "}],
    )

    assert config.service_account_email == "runner@proj-123.iam.gserviceaccount.com"
    assert config.manifest_id == "linkedin"
    assert config.schedule_cron == "0 8 * * *"
    assert config.secrets == [
        {
            "env_var": "LINKEDIN_EMAIL",
            "secret_name": "HARNESSIQ_LINKEDIN_EMAIL",
        }
    ]
