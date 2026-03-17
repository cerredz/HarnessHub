"""Tests for ExaOutreach shared types, memory store, and storage backend."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harnessiq.shared.exa_outreach import (
    DEFAULT_AGENT_IDENTITY,
    EmailSentRecord,
    EmailTemplate,
    ExaOutreachMemoryStore,
    FileSystemStorageBackend,
    LeadRecord,
    OutreachRunLog,
    StorageBackend,
)
from harnessiq.shared.tools import (
    EXA_OUTREACH_CHECK_CONTACTED,
    EXA_OUTREACH_GET_TEMPLATE,
    EXA_OUTREACH_LIST_TEMPLATES,
    EXA_OUTREACH_LOG_EMAIL_SENT,
    EXA_OUTREACH_LOG_LEAD,
)


# ---------------------------------------------------------------------------
# EmailTemplate
# ---------------------------------------------------------------------------


class TestEmailTemplate:
    def test_minimal_construction(self):
        t = EmailTemplate(
            id="t1",
            title="Test",
            subject="Hello",
            description="A test template",
            actual_email="Hi there",
        )
        assert t.id == "t1"
        assert t.links == ()
        assert t.pain_points == ()
        assert t.icp == ""
        assert t.extra == {}

    def test_full_round_trip(self):
        original = EmailTemplate(
            id="cold-intro",
            title="Cold Intro",
            subject="Quick intro",
            description="Short cold intro",
            actual_email="Hi {{name}}, I wanted to reach out...",
            links=("https://example.com",),
            pain_points=("slow hiring",),
            icp="Series B SaaS",
            extra={"tone": "casual"},
        )
        d = original.as_dict()
        restored = EmailTemplate.from_dict(d)
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.subject == original.subject
        assert restored.actual_email == original.actual_email
        assert restored.links == original.links
        assert restored.pain_points == original.pain_points
        assert restored.icp == original.icp
        assert restored.extra == original.extra

    def test_from_dict_minimal(self):
        d = {"id": "x", "title": "T", "subject": "S", "actual_email": "body"}
        t = EmailTemplate.from_dict(d)
        assert t.id == "x"
        assert t.description == ""

    def test_blank_id_raises(self):
        with pytest.raises(ValueError, match="id must not be blank"):
            EmailTemplate(id="  ", title="T", subject="S", description="D", actual_email="B")

    def test_blank_subject_raises(self):
        with pytest.raises(ValueError, match="subject must not be blank"):
            EmailTemplate(id="t", title="T", subject="  ", description="D", actual_email="B")

    def test_blank_actual_email_raises(self):
        with pytest.raises(ValueError, match="actual_email must not be blank"):
            EmailTemplate(id="t", title="T", subject="S", description="D", actual_email="  ")


# ---------------------------------------------------------------------------
# LeadRecord
# ---------------------------------------------------------------------------


class TestLeadRecord:
    def test_round_trip(self):
        lead = LeadRecord(
            url="https://linkedin.com/in/janedoe",
            name="Jane Doe",
            found_at="2025-03-16T12:00:00Z",
            email_address="jane@example.com",
            notes="VP Engineering at Acme",
        )
        d = lead.as_dict()
        restored = LeadRecord.from_dict(d)
        assert restored.url == lead.url
        assert restored.name == lead.name
        assert restored.email_address == lead.email_address
        assert restored.notes == lead.notes

    def test_optional_fields_none(self):
        lead = LeadRecord(url="https://example.com", name="Alice", found_at="2025-01-01T00:00:00Z")
        assert lead.email_address is None
        assert lead.notes is None
        d = lead.as_dict()
        restored = LeadRecord.from_dict(d)
        assert restored.email_address is None


# ---------------------------------------------------------------------------
# EmailSentRecord
# ---------------------------------------------------------------------------


class TestEmailSentRecord:
    def test_round_trip(self):
        record = EmailSentRecord(
            to_email="jane@example.com",
            to_name="Jane Doe",
            subject="Quick intro",
            template_id="cold-intro",
            sent_at="2025-03-16T12:05:00Z",
            notes="Personalized with conference reference",
        )
        d = record.as_dict()
        restored = EmailSentRecord.from_dict(d)
        assert restored.to_email == record.to_email
        assert restored.template_id == record.template_id
        assert restored.notes == record.notes

    def test_notes_optional(self):
        record = EmailSentRecord(
            to_email="a@b.com",
            to_name="A B",
            subject="S",
            template_id="t1",
            sent_at="2025-01-01T00:00:00Z",
        )
        assert record.notes is None


# ---------------------------------------------------------------------------
# OutreachRunLog
# ---------------------------------------------------------------------------


class TestOutreachRunLog:
    def test_round_trip(self):
        log = OutreachRunLog(
            run_id="run_1",
            started_at="2025-03-16T12:00:00Z",
            query="VPs at SaaS startups",
        )
        log.leads_found.append(
            LeadRecord(url="https://example.com/1", name="Alice", found_at="2025-03-16T12:01:00Z")
        )
        log.emails_sent.append(
            EmailSentRecord(
                to_email="alice@example.com",
                to_name="Alice",
                subject="Hi",
                template_id="t1",
                sent_at="2025-03-16T12:02:00Z",
            )
        )
        d = log.as_dict()
        restored = OutreachRunLog.from_dict(d)
        assert restored.run_id == "run_1"
        assert len(restored.leads_found) == 1
        assert len(restored.emails_sent) == 1
        assert restored.completed_at is None

    def test_completed_at_round_trip(self):
        log = OutreachRunLog(
            run_id="run_2",
            started_at="2025-01-01T00:00:00Z",
            query="test",
            completed_at="2025-01-01T01:00:00Z",
        )
        restored = OutreachRunLog.from_dict(log.as_dict())
        assert restored.completed_at == "2025-01-01T01:00:00Z"


# ---------------------------------------------------------------------------
# FileSystemStorageBackend
# ---------------------------------------------------------------------------


class TestFileSystemStorageBackend:
    def test_start_run_creates_file(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        backend.start_run("run_1", "VPs in NYC")
        run_path = tmp_path / "runs" / "run_1.json"
        assert run_path.exists()
        data = json.loads(run_path.read_text())
        assert data["run_id"] == "run_1"
        assert data["query"] == "VPs in NYC"
        assert data["leads_found"] == []
        assert data["emails_sent"] == []

    def test_log_lead_appends_to_run(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        backend.start_run("run_1", "test query")
        lead = LeadRecord(
            url="https://linkedin.com/in/alice",
            name="Alice",
            found_at="2025-01-01T00:00:00Z",
        )
        backend.log_lead("run_1", lead)
        data = json.loads((tmp_path / "runs" / "run_1.json").read_text())
        assert len(data["leads_found"]) == 1
        assert data["leads_found"][0]["url"] == "https://linkedin.com/in/alice"

    def test_log_email_sent_appends_to_run(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        backend.start_run("run_1", "test query")
        record = EmailSentRecord(
            to_email="alice@example.com",
            to_name="Alice",
            subject="Hi",
            template_id="cold-intro",
            sent_at="2025-01-01T00:01:00Z",
        )
        backend.log_email_sent("run_1", record)
        data = json.loads((tmp_path / "runs" / "run_1.json").read_text())
        assert len(data["emails_sent"]) == 1
        assert data["emails_sent"][0]["to_email"] == "alice@example.com"

    def test_finish_run_sets_completed_at(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        backend.start_run("run_1", "test query")
        backend.finish_run("run_1", "2025-01-01T01:00:00Z")
        data = json.loads((tmp_path / "runs" / "run_1.json").read_text())
        assert data["completed_at"] == "2025-01-01T01:00:00Z"

    def test_is_contacted_true_when_url_exists(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        backend.start_run("run_1", "test")
        backend.log_lead("run_1", LeadRecord(url="https://example.com/profile", name="Bob", found_at="2025-01-01T00:00:00Z"))
        assert backend.is_contacted("https://example.com/profile") is True

    def test_is_contacted_false_when_url_absent(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        backend.start_run("run_1", "test")
        assert backend.is_contacted("https://example.com/unknown") is False

    def test_is_contacted_false_with_no_runs(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        assert backend.is_contacted("https://example.com") is False

    def test_current_run_id_after_start(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        assert backend.current_run_id() is None
        backend.start_run("run_3", "test")
        assert backend.current_run_id() == "run_3"

    def test_multiple_leads_and_sends(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        backend.start_run("run_1", "test")
        for i in range(3):
            backend.log_lead("run_1", LeadRecord(url=f"https://example.com/{i}", name=f"Person {i}", found_at="2025-01-01T00:00:00Z"))
        data = json.loads((tmp_path / "runs" / "run_1.json").read_text())
        assert len(data["leads_found"]) == 3

    def test_is_contacted_scans_across_runs(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        backend.start_run("run_1", "q1")
        backend.log_lead("run_1", LeadRecord(url="https://example.com/alice", name="Alice", found_at="2025-01-01T00:00:00Z"))
        backend.start_run("run_2", "q2")
        # alice was in run_1, should still be detected
        assert backend.is_contacted("https://example.com/alice") is True


# ---------------------------------------------------------------------------
# ExaOutreachMemoryStore
# ---------------------------------------------------------------------------


class TestExaOutreachMemoryStore:
    def test_prepare_creates_directories_and_files(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        assert store.memory_path.exists()
        assert store.runs_dir.exists()
        assert store.query_config_path.exists()
        assert store.agent_identity_path.exists()
        assert store.additional_prompt_path.exists()

    def test_prepare_is_idempotent(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        store.prepare()  # second call must not fail or overwrite
        assert store.agent_identity_path.exists()

    def test_next_run_id_empty(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        assert store.next_run_id() == "run_1"

    def test_next_run_id_increments(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        # create two synthetic run files
        (store.runs_dir / "run_1.json").write_text("{}")
        (store.runs_dir / "run_2.json").write_text("{}")
        assert store.next_run_id() == "run_3"

    def test_list_run_files_sorted(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        for n in [3, 1, 2]:
            (store.runs_dir / f"run_{n}.json").write_text("{}")
        files = store.list_run_files()
        names = [f.name for f in files]
        assert names == ["run_1.json", "run_2.json", "run_3.json"]

    def test_write_and_read_query_config(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        store.write_query_config({"query": "VPs in NYC", "max_tokens": 80000})
        loaded = store.read_query_config()
        assert loaded["query"] == "VPs in NYC"
        assert loaded["max_tokens"] == 80000

    def test_write_and_read_agent_identity(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        store.write_agent_identity("Custom persona here")
        assert store.read_agent_identity() == "Custom persona here"

    def test_default_agent_identity(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        assert store.read_agent_identity() == DEFAULT_AGENT_IDENTITY

    def test_read_run_missing_raises(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        with pytest.raises(FileNotFoundError):
            store.read_run("run_99")

    def test_write_and_read_additional_prompt(self, tmp_path):
        store = ExaOutreachMemoryStore(memory_path=tmp_path / "outreach")
        store.prepare()
        store.write_additional_prompt("Keep emails under 80 words.")
        assert store.read_additional_prompt() == "Keep emails under 80 words."


# ---------------------------------------------------------------------------
# StorageBackend protocol conformance
# ---------------------------------------------------------------------------


class TestStorageBackendProtocol:
    def test_filesystem_backend_conforms_to_protocol(self, tmp_path):
        backend = FileSystemStorageBackend(tmp_path)
        assert isinstance(backend, StorageBackend)


# ---------------------------------------------------------------------------
# Tool key constants
# ---------------------------------------------------------------------------


class TestToolKeyConstants:
    def test_all_constants_have_expected_values(self):
        assert EXA_OUTREACH_LIST_TEMPLATES == "exa_outreach.list_templates"
        assert EXA_OUTREACH_GET_TEMPLATE == "exa_outreach.get_template"
        assert EXA_OUTREACH_CHECK_CONTACTED == "exa_outreach.check_contacted"
        assert EXA_OUTREACH_LOG_LEAD == "exa_outreach.log_lead"
        assert EXA_OUTREACH_LOG_EMAIL_SENT == "exa_outreach.log_email_sent"

    def test_constants_importable_from_shared_tools(self):
        from harnessiq.shared.tools import (
            EXA_OUTREACH_CHECK_CONTACTED,
            EXA_OUTREACH_GET_TEMPLATE,
            EXA_OUTREACH_LIST_TEMPLATES,
            EXA_OUTREACH_LOG_EMAIL_SENT,
            EXA_OUTREACH_LOG_LEAD,
        )
        assert EXA_OUTREACH_LIST_TEMPLATES.startswith("exa_outreach.")
