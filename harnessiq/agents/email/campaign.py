"""Concrete durable-memory email campaign agent."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.agents.base import AgentModel, AgentParameterSection, AgentRuntimeConfig
from harnessiq.agents.sdk_helpers import merge_profile_parameters, resolve_profile_memory_path
from harnessiq.config import HarnessProfile
from harnessiq.shared.agents import json_parameter_section, merge_agent_runtime_config
from harnessiq.shared.dtos import EmailAgentRequest, EmailCampaignAgentInstancePayload
from harnessiq.shared.email import DEFAULT_EMAIL_AGENT_IDENTITY
from harnessiq.shared.email_campaign import (
    EMAIL_HARNESS_MANIFEST,
    EmailCampaignMemoryStore,
    EmailSendRecord,
    build_resend_batch_payload,
    load_email_campaign_recipients,
    normalize_email_custom_parameters,
    resolve_email_runtime_parameters,
)
from harnessiq.shared.tools import ToolCall, ToolResult
from harnessiq.tools import RESEND_REQUEST

from .agent import BaseEmailAgent


class EmailCampaignAgent(BaseEmailAgent):
    """Send one prepared email campaign batch to deduplicated Mongo-backed recipients."""

    def __init__(
        self,
        *,
        model: AgentModel,
        request: EmailAgentRequest,
        memory_path: str | Path,
        runtime_parameters: Mapping[str, Any] | None = None,
        custom_parameters: Mapping[str, Any] | None = None,
        resend_client=None,
        runtime_config: AgentRuntimeConfig | None = None,
        instance_name: str | None = None,
    ) -> None:
        self._store = EmailCampaignMemoryStore(memory_path=Path(memory_path))
        self._runtime_parameters = resolve_email_runtime_parameters(runtime_parameters or {})
        self._custom_parameters = normalize_email_custom_parameters(custom_parameters or {})
        self._selected_recipients = []
        self._prepared_batch_payload = []
        self._delivery_records: list[EmailSendRecord] = []
        self._last_send_response: dict[str, Any] | None = None
        super().__init__(
            name="email_campaign_agent",
            model=model,
            request=request,
            resend_client=resend_client,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=int(self._runtime_parameters["max_tokens"]),
                reset_threshold=float(self._runtime_parameters["reset_threshold"]),
            ),
            memory_path=self._store.memory_path,
            instance_name=instance_name,
        )

    @classmethod
    def from_memory(
        cls,
        *,
        model: AgentModel,
        resend_credentials,
        memory_path: str | Path | None = None,
        runtime_overrides: Mapping[str, Any] | None = None,
        custom_overrides: Mapping[str, Any] | None = None,
        resend_client=None,
        runtime_config: AgentRuntimeConfig | None = None,
        instance_name: str | None = None,
    ) -> "EmailCampaignAgent":
        resolved_memory_path = (
            Path(memory_path)
            if memory_path is not None
            else Path(EMAIL_HARNESS_MANIFEST.resolved_default_memory_root)
        )
        store = EmailCampaignMemoryStore(memory_path=resolved_memory_path)
        store.prepare()
        runtime_parameters = dict(store.read_runtime_parameters())
        if runtime_overrides:
            runtime_parameters.update(runtime_overrides)
        custom_parameters = dict(store.read_custom_parameters())
        if custom_overrides:
            custom_parameters.update(custom_overrides)
        resolved_runtime = resolve_email_runtime_parameters(runtime_parameters)
        request = EmailAgentRequest(
            resend_credentials=resend_credentials,
            allowed_resend_operations=("send_batch_emails",),
            max_tokens=int(resolved_runtime["max_tokens"]),
            reset_threshold=float(resolved_runtime["reset_threshold"]),
        )
        return cls(
            model=model,
            request=request,
            memory_path=store.memory_path,
            runtime_parameters=resolved_runtime,
            custom_parameters=custom_parameters,
            resend_client=resend_client,
            runtime_config=runtime_config,
            instance_name=instance_name,
        )

    @classmethod
    def from_profile(
        cls,
        *,
        profile: HarnessProfile,
        model: AgentModel,
        resend_credentials,
        memory_path: str | Path | None = None,
        resend_client=None,
        runtime_config: AgentRuntimeConfig | None = None,
        runtime_overrides: Mapping[str, Any] | None = None,
        custom_overrides: Mapping[str, Any] | None = None,
        instance_name: str | None = None,
    ) -> "EmailCampaignAgent":
        resolved_memory_path = resolve_profile_memory_path(
            profile=profile,
            manifest=EMAIL_HARNESS_MANIFEST,
            memory_path=memory_path,
        )
        resolved_runtime, resolved_custom = merge_profile_parameters(
            profile=profile,
            runtime_overrides=runtime_overrides,
            custom_overrides=custom_overrides,
        )
        return cls.from_memory(
            model=model,
            resend_credentials=resend_credentials,
            memory_path=resolved_memory_path,
            runtime_overrides=resolved_runtime,
            custom_overrides=resolved_custom,
            resend_client=resend_client,
            runtime_config=runtime_config,
            instance_name=instance_name or profile.agent_name,
        )

    @property
    def memory_store(self) -> EmailCampaignMemoryStore:
        return self._store

    def prepare(self) -> None:
        self._store.prepare()
        source_config = self._store.read_source_config()
        campaign_config = self._store.read_campaign_config()
        source_config.validate_for_run()
        campaign_config.validate_for_run()
        recipient_limit = self._runtime_parameters.get("recipient_limit")
        batch_size = int(self._runtime_parameters["batch_size"])
        selection_limit = batch_size
        if recipient_limit is not None:
            selection_limit = min(batch_size, int(recipient_limit))
        self._selected_recipients = load_email_campaign_recipients(
            source_config,
            limit=selection_limit,
            sent_emails=self._store.sent_email_addresses(),
        )
        if not self._selected_recipients:
            raise ValueError(
                "No unsent recipients are available for the configured email campaign source."
            )
        self._prepared_batch_payload = build_resend_batch_payload(campaign_config, self._selected_recipients)

    def build_instance_payload(self) -> EmailCampaignAgentInstancePayload:
        return EmailCampaignAgentInstancePayload(
            memory_path=self._store.memory_path,
            runtime=self._runtime_parameters,
            source_config=self._store.read_source_config().as_dict(),
            campaign_config=self._store.read_campaign_config().as_dict(),
            custom_parameters=self._custom_parameters,
            agent_identity=self.email_identity(),
            additional_prompt=self.additional_email_instructions(),
        )

    def email_identity(self) -> str:
        identity = self._store.read_agent_identity()
        return identity or DEFAULT_EMAIL_AGENT_IDENTITY

    def email_objective(self) -> str:
        return (
            "Send the prepared email campaign to the selected deduplicated recipient batch. "
            "Use the configured Resend batch-send tool call and do not improvise the recipient list."
        )

    def load_email_parameter_sections(self) -> Sequence[AgentParameterSection]:
        return (
            json_parameter_section("Runtime Parameters", self._runtime_parameters),
            json_parameter_section("Source Config", self._store.read_source_config().as_dict()),
            json_parameter_section("Campaign Config", self._store.read_campaign_config().as_dict()),
            json_parameter_section(
                "Recipient Batch",
                [recipient.as_dict() for recipient in self._selected_recipients],
            ),
            json_parameter_section("Prepared Batch Payload", self._prepared_batch_payload),
        )

    def email_behavioral_rules(self) -> Sequence[str]:
        return (
            "- Use `send_batch_emails` and only `send_batch_emails` for delivery.",
            "- Send the exact prepared batch payload from the parameter sections unless a critical validation issue is found.",
            "- Do not add, remove, or rewrite recipients outside the prepared batch.",
            "- Do not rewrite the operator-authored campaign content unless instructed by the additional prompt.",
        )

    def additional_email_instructions(self) -> str | None:
        return self._store.read_additional_prompt() or None

    def build_ledger_outputs(self) -> dict[str, Any]:
        return {
            "campaign": self._store.read_campaign_config().as_dict(),
            "delivery_records": [record.as_dict() for record in self._delivery_records],
            "recipient_batch": [recipient.as_dict() for recipient in self._selected_recipients],
        }

    def build_ledger_metadata(self) -> dict[str, Any]:
        metadata = super().build_ledger_metadata()
        metadata.update(
            {
                "batch_size": int(self._runtime_parameters["batch_size"]),
                "recipient_limit": self._runtime_parameters.get("recipient_limit"),
                "selected_recipient_count": len(self._selected_recipients),
            }
        )
        if self._last_send_response is not None:
            metadata["last_send_response"] = dict(self._last_send_response)
        return metadata

    def _finalize_tool_result(
        self,
        tool_call: ToolCall,
        result: ToolResult,
    ) -> tuple[ToolResult, Any]:
        finalized_result, pause_signal = super()._finalize_tool_result(tool_call, result)
        self._record_send_history(tool_call, finalized_result)
        return finalized_result, pause_signal

    def _record_send_history(self, tool_call: ToolCall, result: ToolResult) -> None:
        if tool_call.tool_key != RESEND_REQUEST:
            return
        if tool_call.arguments.get("operation") != "send_batch_emails":
            return
        if not isinstance(result.output, Mapping) or result.output.get("error") is not None:
            return
        payload = tool_call.arguments.get("payload")
        if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes, bytearray)):
            return
        response = result.output.get("response")
        self._last_send_response = dict(result.output)
        response_items = response.get("data") if isinstance(response, Mapping) else None
        sent_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        new_records: list[EmailSendRecord] = []
        existing = {record.email_address for record in self._delivery_records}
        for index, item in enumerate(payload):
            if not isinstance(item, Mapping):
                continue
            recipient_values = item.get("to")
            if not isinstance(recipient_values, Sequence) or isinstance(recipient_values, (str, bytes, bytearray)):
                continue
            subject = str(item.get("subject", ""))
            resend_id = None
            if isinstance(response_items, Sequence) and index < len(response_items):
                response_item = response_items[index]
                if isinstance(response_item, Mapping) and response_item.get("id") is not None:
                    resend_id = str(response_item["id"])
            for raw_email in recipient_values:
                email_address = str(raw_email).strip().lower()
                if not email_address or email_address in existing:
                    continue
                existing.add(email_address)
                new_records.append(
                    EmailSendRecord(
                        email_address=email_address,
                        sent_at=sent_at,
                        subject=subject,
                        resend_id=resend_id,
                    )
                )
        if not new_records:
            return
        self._store.append_sent_records(new_records)
        self._delivery_records.extend(new_records)


__all__ = ["EmailCampaignAgent"]
