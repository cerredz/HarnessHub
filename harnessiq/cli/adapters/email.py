"""Email campaign platform CLI adapter."""

from __future__ import annotations

import argparse
from typing import Any

from harnessiq.agents import AgentModel, AgentRuntimeConfig, EmailCampaignAgent
from harnessiq.shared.dtos import HarnessAdapterResponseDTO, HarnessStatePayloadDTO
from harnessiq.shared.email_campaign import (
    EmailCampaignMemoryStore,
    normalize_email_custom_parameters,
    normalize_email_runtime_parameters,
    summarize_email_campaign_store,
)

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import load_email_store, result_payload


class EmailHarnessCliAdapter(StoreBackedHarnessCliAdapter[EmailCampaignMemoryStore]):
    """Adapt the email campaign harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_email_store)

    def read_native_runtime_parameters(
        self,
        store: EmailCampaignMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_runtime_parameters()

    def read_native_custom_parameters(
        self,
        store: EmailCampaignMemoryStore,
        context: HarnessAdapterContext,
    ) -> dict[str, object]:
        del context
        return store.read_custom_parameters()

    def write_runtime_parameters(self, store: EmailCampaignMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_runtime_parameters(normalize_email_runtime_parameters(context.profile.runtime_parameters))

    def write_custom_parameters(self, store: EmailCampaignMemoryStore, context: HarnessAdapterContext) -> None:
        store.write_custom_parameters(normalize_email_custom_parameters(context.profile.custom_parameters))

    def show(self, context: HarnessAdapterContext) -> HarnessStatePayloadDTO:
        store = self.load_store(context)
        return HarnessStatePayloadDTO(summarize_email_campaign_store(store))

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> HarnessAdapterResponseDTO:
        store = self.load_store(context)
        resend_credentials = context.bound_credentials.get("resend")
        if resend_credentials is None:
            raise ValueError(
                "Email Campaign requires a 'resend' credential binding. "
                "Use `harnessiq credentials bind email ...` first."
            )
        agent = EmailCampaignAgent.from_memory(
            model=model,
            resend_credentials=resend_credentials,
            memory_path=context.memory_path,
            runtime_overrides=context.runtime_parameters,
            custom_overrides=context.custom_parameters,
            runtime_config=runtime_config,
            instance_name=context.agent_name,
        )
        result = agent.run(max_cycles=args.max_cycles)
        outputs = agent.build_ledger_outputs()
        return HarnessAdapterResponseDTO(
            result=result_payload(result),
            state=self.show(context),
            extra={
                "delivery_count": len(outputs["delivery_records"]),
                "instance_id": getattr(agent, "instance_id", None),
                "instance_name": getattr(agent, "instance_name", None),
                "ledger_run_id": getattr(agent, "last_run_id", None),
                "recipient_batch_count": len(outputs["recipient_batch"]),
                "sent_count": len(store.read_sent_history()),
            },
        )


__all__ = ["EmailHarnessCliAdapter"]
