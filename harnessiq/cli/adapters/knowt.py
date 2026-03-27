"""Knowt platform CLI adapter."""

from __future__ import annotations

import argparse

from harnessiq.agents import AgentModel, AgentRuntimeConfig, KnowtAgent
from harnessiq.shared.dtos import HarnessAdapterResponseDTO, HarnessStatePayloadDTO
from harnessiq.shared.knowt import KnowtMemoryStore

from .base import StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .utils import load_knowt_store, result_payload


class KnowtHarnessCliAdapter(StoreBackedHarnessCliAdapter[KnowtMemoryStore]):
    """Adapt the Knowt harness memory layout to the platform-first CLI."""

    store_loader = staticmethod(load_knowt_store)

    def show(self, context: HarnessAdapterContext) -> HarnessStatePayloadDTO:
        store = self.load_store(context)
        creation_log = store.read_creation_log()
        return HarnessStatePayloadDTO(
            {
                "avatar_description": store.read_avatar_description(),
                "creation_log_count": len(creation_log),
                "recent_creation_log": [entry.as_dict() for entry in creation_log[-5:]],
                "script": store.read_script(),
            }
        )

    def run(
        self,
        *,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        model: AgentModel,
        runtime_config: AgentRuntimeConfig,
    ) -> HarnessAdapterResponseDTO:
        self.load_store(context)
        agent = KnowtAgent(
            model=model,
            memory_path=context.memory_path,
            creatify_credentials=context.bound_credentials.get("creatify"),
            max_tokens=int(context.runtime_parameters["max_tokens"]),
            reset_threshold=float(context.runtime_parameters["reset_threshold"]),
            runtime_config=runtime_config,
        )
        result = agent.run(max_cycles=args.max_cycles)
        return HarnessAdapterResponseDTO(
            result=result_payload(result),
            state=self.show(context),
        )


__all__ = ["KnowtHarnessCliAdapter"]
