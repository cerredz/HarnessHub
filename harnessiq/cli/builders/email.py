"""Email-campaign lifecycle builders for dedicated CLI commands."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from harnessiq.cli.common import (
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_text_argument,
)
from harnessiq.shared.email_campaign import (
    EMAIL_HARNESS_MANIFEST,
    EmailCampaignConfig,
    EmailCampaignMemoryStore,
    MongoRecipientSourceConfig,
    load_email_campaign_recipients,
    resolve_email_runtime_parameters,
    summarize_email_campaign_store,
)


class EmailCliBuilder:
    """Build and persist email-campaign CLI-managed memory state."""

    def prepare(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        return {
            "agent": agent_name,
            "memory_path": str(store.memory_path.resolve()),
            "status": "prepared",
        }

    def configure(
        self,
        *,
        agent_name: str,
        memory_root: str,
        mongodb_uri_env: str | None,
        mongodb_database: str | None,
        mongodb_collection: str | None,
        source_filter_text: str | None,
        source_filter_file: str | None,
        email_paths: Sequence[str],
        name_paths: Sequence[str],
        from_address: str | None,
        reply_to: str | None,
        subject: str | None,
        batch_validation: str | None,
        html_body_text: str | None,
        html_body_file: str | None,
        text_body_text: str | None,
        text_body_file: str | None,
        agent_identity_text: str | None,
        agent_identity_file: str | None,
        additional_prompt_text: str | None,
        additional_prompt_file: str | None,
        runtime_assignments: Sequence[str],
        custom_assignments: Sequence[str],
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        updated: list[str] = []

        existing_source = store.read_source_config()
        source_filter = self._resolve_source_filter(source_filter_text, source_filter_file)
        if any(
            value is not None
            for value in (
                mongodb_uri_env,
                mongodb_database,
                mongodb_collection,
                source_filter,
            )
        ) or email_paths or name_paths:
            store.write_source_config(
                MongoRecipientSourceConfig(
                    connection_uri_env_var=mongodb_uri_env or existing_source.connection_uri_env_var,
                    database=mongodb_database or existing_source.database,
                    collection=mongodb_collection or existing_source.collection,
                    query_filter=source_filter if source_filter is not None else existing_source.query_filter,
                    email_paths=tuple(email_paths) or existing_source.email_paths,
                    name_paths=tuple(name_paths) or existing_source.name_paths,
                )
            )
            updated.append("source_config")

        existing_campaign = store.read_campaign_config()
        html_body = resolve_text_argument(html_body_text, html_body_file)
        text_body = resolve_text_argument(text_body_text, text_body_file)
        if any(
            value is not None
            for value in (
                from_address,
                reply_to,
                subject,
                batch_validation,
                html_body,
                text_body,
            )
        ):
            store.write_campaign_config(
                EmailCampaignConfig(
                    from_address=from_address or existing_campaign.from_address,
                    reply_to=reply_to if reply_to is not None else existing_campaign.reply_to,
                    subject=subject or existing_campaign.subject,
                    batch_validation=(
                        batch_validation if batch_validation is not None else existing_campaign.batch_validation
                    ),
                    html_body=html_body if html_body is not None else existing_campaign.html_body,
                    text_body=text_body if text_body is not None else existing_campaign.text_body,
                )
            )
            updated.append("campaign_config")

        self._write_optional_text(
            store.write_agent_identity,
            resolve_text_argument(agent_identity_text, agent_identity_file),
            "agent_identity",
            updated,
        )
        self._write_optional_text(
            store.write_additional_prompt,
            resolve_text_argument(additional_prompt_text, additional_prompt_file),
            "additional_prompt",
            updated,
        )

        runtime_parameters = self._parse_runtime_assignments(runtime_assignments)
        if runtime_parameters:
            current = store.read_runtime_parameters()
            current.update(runtime_parameters)
            store.write_runtime_parameters(current)
            updated.append("runtime_parameters")

        custom_parameters = self._parse_custom_assignments(custom_assignments)
        if custom_parameters:
            current = store.read_custom_parameters()
            current.update(custom_parameters)
            store.write_custom_parameters(current)
            updated.append("custom_parameters")

        payload = self.build_summary(store=store)
        payload["status"] = "configured"
        payload["updated"] = updated
        return payload

    def show(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        return self.build_summary(store=store)

    def get_recipients(
        self,
        *,
        agent_name: str,
        memory_root: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        store = self._load_store(agent_name=agent_name, memory_root=memory_root)
        store.prepare()
        resolved_runtime = resolve_email_runtime_parameters(store.read_runtime_parameters())
        selection_limit = int(resolved_runtime["batch_size"])
        if resolved_runtime.get("recipient_limit") is not None:
            selection_limit = min(selection_limit, int(resolved_runtime["recipient_limit"]))
        if limit is not None:
            selection_limit = limit
        recipients = load_email_campaign_recipients(
            store.read_source_config(),
            limit=selection_limit,
            sent_emails=store.sent_email_addresses(),
        )
        return {
            "agent": agent_name,
            "count": len(recipients),
            "memory_path": str(store.memory_path.resolve()),
            "recipients": [recipient.as_dict() for recipient in recipients],
        }

    def build_summary(self, *, store: EmailCampaignMemoryStore) -> dict[str, Any]:
        return summarize_email_campaign_store(store)

    def _load_store(
        self,
        *,
        agent_name: str,
        memory_root: str,
    ) -> EmailCampaignMemoryStore:
        return EmailCampaignMemoryStore(memory_path=resolve_memory_path(agent_name, memory_root))

    def _parse_runtime_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=EMAIL_HARNESS_MANIFEST,
            scope="runtime",
        )

    def _parse_custom_assignments(self, assignments: Sequence[str]) -> dict[str, Any]:
        return parse_manifest_parameter_assignments(
            assignments,
            manifest=EMAIL_HARNESS_MANIFEST,
            scope="custom",
        )

    def _resolve_source_filter(self, text_value: str | None, file_value: str | None) -> dict[str, Any] | None:
        raw = resolve_text_argument(text_value, file_value)
        if raw is None:
            return None
        cleaned = raw.strip()
        if not cleaned:
            return {}
        payload = json.loads(cleaned)
        if not isinstance(payload, dict):
            raise ValueError("Email source filter must be a JSON object.")
        return dict(payload)

    def _write_optional_text(self, writer, content: str | None, key: str, updated: list[str]) -> None:
        if content is None:
            return
        writer(content)
        updated.append(key)


__all__ = ["EmailCliBuilder"]
