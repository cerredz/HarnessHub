"""Tests for shared leads models, memory store, and filesystem storage backend."""

from __future__ import annotations

import json

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.leads import (
    DEFAULT_LEADS_SEARCH_SUMMARY_EVERY,
    DEFAULT_LEADS_SEARCH_TAIL_SIZE,
    FileSystemLeadsStorageBackend,
    ICPS_DIRNAME,
    LEADS_STORAGE_DIRNAME,
    RUN_CONFIG_FILENAME,
    RUN_STATE_FILENAME,
    SAVED_LEADS_FILENAME,
    LeadICP,
    LeadsAgentConfig,
    LeadRecord,
    LeadRunConfig,
    LeadRunState,
    LeadSearchRecord,
    LeadsMemoryStore,
    LeadsStorageBackend,
)


class TestLeadICP:
    def test_blank_key_is_derived_from_label(self):
        icp = LeadICP(label="VP Sales at Series B SaaS")
        assert icp.key == "vp-sales-at-series-b-saas"

    def test_round_trip(self):
        original = LeadICP(
            key="revops",
            label="Revenue Operations",
            description="Target RevOps leaders",
            metadata={"titles": ["VP Revenue Operations"]},
        )
        restored = LeadICP.from_dict(original.as_dict())
        assert restored == original


class TestLeadRecord:
    def test_provider_person_id_has_highest_dedupe_priority(self):
        lead = LeadRecord(
            full_name="Alice Smith",
            company_name="Acme",
            title="VP Sales",
            icp_key="sales",
            provider="apollo",
            provider_person_id="P-123",
            linkedin_url="https://linkedin.com/in/alice",
            email="Alice@Example.com",
            found_at="2026-03-18T00:00:00Z",
        )
        assert lead.dedupe_key() == "provider:apollo:p-123"

    def test_linkedin_and_email_are_normalized(self):
        linkedin = LeadRecord(
            full_name="Alice Smith",
            company_name="Acme",
            title="VP Sales",
            icp_key="sales",
            provider="apollo",
            linkedin_url="https://LinkedIn.com/in/alice/?trk=foo",
            found_at="2026-03-18T00:00:00Z",
        )
        email = LeadRecord(
            full_name="Bob Jones",
            company_name="Beta",
            title="Head of Sales",
            icp_key="sales",
            provider="leadiq",
            email="Bob.Jones@Example.com ",
            found_at="2026-03-18T00:00:00Z",
        )
        assert linkedin.dedupe_key() == "linkedin:https://linkedin.com/in/alice"
        assert email.dedupe_key() == "email:bob.jones@example.com"


class TestLeadsMemoryStore:
    def test_prepare_creates_memory_layout(self, tmp_path):
        store = LeadsMemoryStore(tmp_path / "leads")
        store.prepare()
        assert store.memory_path.exists()
        assert store.icps_dir.exists()
        assert store.icps_dir.name == ICPS_DIRNAME

    def test_run_config_and_state_round_trip(self, tmp_path):
        store = LeadsMemoryStore(tmp_path / "leads")
        config = LeadRunConfig(
            company_background="We sell outbound infrastructure to B2B SaaS teams.",
            icps=(LeadICP(key="sales", label="Sales leaders"),),
            platforms=("apollo", "leadiq"),
            search_summary_every=25,
            search_tail_size=5,
            max_leads_per_icp=50,
        )
        state = LeadRunState(run_id="run_1", active_icp_index=1, status="running")

        store.write_run_config(config)
        store.write_run_state(state)

        assert store.run_config_path.name == RUN_CONFIG_FILENAME
        assert store.run_state_path.name == RUN_STATE_FILENAME
        assert store.read_run_config() == config
        assert store.read_run_state() == state

    def test_append_searches_are_scoped_per_icp(self, tmp_path):
        store = LeadsMemoryStore(tmp_path / "leads")
        sales = LeadICP(key="sales", label="Sales leaders")
        marketing = LeadICP(key="marketing", label="Marketing leaders")
        store.initialize_icp_states((sales, marketing))

        store.append_search(
            "sales",
            LeadSearchRecord(
                sequence=1,
                icp_key="sales",
                platform="apollo",
                query="VP Sales series B SaaS",
                recorded_at="2026-03-18T00:00:00Z",
                result_count=12,
                outcome="Strong matches",
            ),
        )
        store.append_search(
            "marketing",
            LeadSearchRecord(
                sequence=1,
                icp_key="marketing",
                platform="leadiq",
                query="VP Marketing fintech",
                recorded_at="2026-03-18T00:00:00Z",
                result_count=7,
                outcome="Too narrow",
            ),
        )

        sales_state = store.read_icp_state("sales")
        marketing_state = store.read_icp_state("marketing")
        assert len(sales_state.searches) == 1
        assert sales_state.searches[0].platform == "apollo"
        assert len(marketing_state.searches) == 1
        assert marketing_state.searches[0].platform == "leadiq"

    def test_compact_searches_replaces_old_block_and_keeps_tail(self, tmp_path):
        store = LeadsMemoryStore(tmp_path / "leads")
        icp = LeadICP(key="sales", label="Sales leaders")
        store.initialize_icp_states((icp,))
        for sequence in range(1, 4):
            store.append_search(
                "sales",
                LeadSearchRecord(
                    sequence=sequence,
                    icp_key="sales",
                    platform="apollo",
                    query=f"query {sequence}",
                    recorded_at="2026-03-18T00:00:00Z",
                ),
            )

        summary = store.compact_searches(
            "sales",
            summary_content="Apollo broad search worked best; keep title variants.",
            keep_last=1,
            created_at="2026-03-18T00:10:00Z",
        )
        state = store.read_icp_state("sales")
        summaries, tail = store.read_search_context("sales", tail_size=1)

        assert summary.summary_id == "summary_1"
        assert summary.replaced_search_count == 2
        assert summary.last_sequence == 2
        assert len(state.summaries) == 1
        assert [entry.sequence for entry in state.searches] == [3]
        assert len(summaries) == 1
        assert [entry.sequence for entry in tail] == [3]
        assert store.next_search_sequence("sales") == 4

    def test_record_saved_lead_key_is_unique(self, tmp_path):
        store = LeadsMemoryStore(tmp_path / "leads")
        icp = LeadICP(key="sales", label="Sales leaders")
        store.initialize_icp_states((icp,))

        store.record_saved_lead_key("sales", "email:alice@example.com")
        store.record_saved_lead_key("sales", "email:alice@example.com")

        state = store.read_icp_state("sales")
        assert state.saved_lead_keys == ["email:alice@example.com"]
        assert store.has_saved_lead_key("sales", "email:alice@example.com") is True


class TestLeadsAgentConfig:
    def test_from_inputs_builds_normalized_defaults(self, tmp_path):
        config = LeadsAgentConfig.from_inputs(
            company_background="We sell outbound infrastructure to B2B SaaS teams.",
            icps=("VP Sales",),
            platforms=(" Apollo ",),
            memory_path=tmp_path / "leads",
        )

        assert config.memory_path == tmp_path / "leads"
        assert config.max_tokens == DEFAULT_AGENT_MAX_TOKENS
        assert config.reset_threshold == DEFAULT_AGENT_RESET_THRESHOLD
        assert config.run_config.icps == (LeadICP(label="VP Sales"),)
        assert config.run_config.platforms == ("apollo",)
        assert config.run_config.search_summary_every == DEFAULT_LEADS_SEARCH_SUMMARY_EVERY
        assert config.run_config.search_tail_size == DEFAULT_LEADS_SEARCH_TAIL_SIZE
        assert isinstance(config.storage_backend, FileSystemLeadsStorageBackend)


class TestFileSystemLeadsStorageBackend:
    def _lead(self, *, icp_key: str, name: str, linkedin_url: str) -> LeadRecord:
        return LeadRecord(
            full_name=name,
            company_name="Acme",
            title="VP Sales",
            icp_key=icp_key,
            provider="apollo",
            linkedin_url=linkedin_url,
            found_at="2026-03-18T00:00:00Z",
        )

    def test_start_run_and_finish_run_create_storage_files(self, tmp_path):
        backend = FileSystemLeadsStorageBackend(tmp_path)
        backend.start_run("run_1", {"company": "Harness"})
        backend.finish_run("run_1", "2026-03-18T00:30:00Z")

        run_path = tmp_path / LEADS_STORAGE_DIRNAME / "runs" / "run_1.json"
        saved_path = tmp_path / LEADS_STORAGE_DIRNAME / SAVED_LEADS_FILENAME
        assert backend.current_run_id() == "run_1"
        assert run_path.exists()
        assert saved_path.exists()
        payload = json.loads(run_path.read_text(encoding="utf-8"))
        assert payload["completed_at"] == "2026-03-18T00:30:00Z"

    def test_save_leads_dedupes_across_runs(self, tmp_path):
        backend = FileSystemLeadsStorageBackend(tmp_path)
        lead = self._lead(icp_key="sales", name="Alice Smith", linkedin_url="https://linkedin.com/in/alice/")

        backend.start_run("run_1", {"company": "Harness"})
        first_results = backend.save_leads("run_1", "sales", [lead])
        backend.finish_run("run_1", "2026-03-18T00:30:00Z")

        backend.start_run("run_2", {"company": "Harness"})
        duplicate = self._lead(
            icp_key="sales",
            name="Alice Smith",
            linkedin_url="https://linkedin.com/in/alice/?trk=foo",
        )
        second_results = backend.save_leads("run_2", "sales", [duplicate])

        assert first_results[0].saved is True
        assert second_results[0].saved is False
        assert second_results[0].reason == "duplicate"
        assert backend.has_seen_lead(lead.dedupe_key()) is True
        assert len(backend.list_leads()) == 1

    def test_list_leads_filters_by_icp(self, tmp_path):
        backend = FileSystemLeadsStorageBackend(tmp_path)
        backend.start_run("run_1", {"company": "Harness"})
        backend.save_leads(
            "run_1",
            "sales",
            [self._lead(icp_key="sales", name="Alice Smith", linkedin_url="https://linkedin.com/in/alice")],
        )
        backend.save_leads(
            "run_1",
            "marketing",
            [self._lead(icp_key="marketing", name="Bob Jones", linkedin_url="https://linkedin.com/in/bob")],
        )

        assert len(backend.list_leads()) == 2
        filtered = backend.list_leads(icp_key="sales")
        assert len(filtered) == 1
        assert filtered[0].icp_key == "sales"


class TestLeadsStorageBackendProtocol:
    def test_filesystem_backend_conforms(self, tmp_path):
        backend = FileSystemLeadsStorageBackend(tmp_path)
        assert isinstance(backend, LeadsStorageBackend)
