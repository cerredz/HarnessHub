from pathlib import Path

from harnessiq.shared.harness_manifests import list_harness_manifests


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "harnessiq" / "cli" / "skills"


def test_cli_skills_readme_exists_and_indexes_every_manifest() -> None:
    readme_path = SKILLS_DIR / "README.md"
    assert readme_path.exists()

    readme_text = readme_path.read_text(encoding="utf-8")
    for manifest in list_harness_manifests():
        assert manifest.display_name in readme_text
        assert f"./{manifest.manifest_id}.md" in readme_text


def test_each_manifest_has_a_matching_skill_file_with_core_inventory() -> None:
    for manifest in list_harness_manifests():
        doc_path = SKILLS_DIR / f"{manifest.manifest_id}.md"
        assert doc_path.exists(), f"Missing CLI skill doc for manifest '{manifest.manifest_id}'."

        text = doc_path.read_text(encoding="utf-8")

        assert manifest.display_name in text
        assert manifest.default_memory_root in text
        assert f"harnessiq inspect {manifest.manifest_id}" in text

        for runtime_parameter in manifest.runtime_parameters:
            assert runtime_parameter.key in text

        for custom_parameter in manifest.custom_parameters:
            assert custom_parameter.key in text

        if manifest.custom_parameters_open_ended:
            assert "open-ended" in text

        if manifest.cli_command:
            assert f"harnessiq {manifest.cli_command}" in text
        else:
            assert f"harnessiq prepare {manifest.manifest_id}" in text
            assert f"harnessiq run {manifest.manifest_id}" in text
