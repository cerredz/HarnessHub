"""Tests for the concrete durable-memory email campaign agent."""

from __future__ import annotations

from unittest.mock import patch

from harnessiq.agents import AgentModelRequest, AgentModelResponse
from harnessiq.agents.email import EmailCampaignAgent
from harnessiq.shared.dtos import EmailAgentRequest
from harnessiq.shared.email_campaign import (
    EmailCampaignMemoryStore,
    EmailCampaignRecipient,
    EmailCampaignConfig,
    MongoRecipientSourceConfig,
)
from harnessiq.shared.tools import ToolCall
from harnessiq.tools import RESEND_REQUEST, ResendClient, ResendCredentials


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


def test_email_campaign_agent_records_sent_history_after_batch_send(tmp_path) -> None:
    store = EmailCampaignMemoryStore(memory_path=tmp_path / "campaign-a")
    store.prepare()
    store.write_source_config(
        MongoRecipientSourceConfig(
            connection_uri_env_var="MONGODB_URI",
            database="warehouse",
            collection="instagram_leads",
        )
    )
    store.write_campaign_config(
        EmailCampaignConfig(
            from_address="HarnessIQ <hello@example.com>",
            subject="Hello {{name}}",
            html_body="<p>Hi {{name}}</p>",
        )
    )

    recipient = EmailCampaignRecipient(email_address="creator@example.com", name="Creator A")
    batch_payload = [
        {
            "from": "HarnessIQ <hello@example.com>",
            "to": ["creator@example.com"],
            "subject": "Hello Creator A",
            "html": "<p>Hi Creator A</p>",
        }
    ]
    model = _FakeModel(
        [
            AgentModelResponse(
                assistant_message="Send the prepared batch.",
                tool_calls=(
                    ToolCall(
                        tool_key=RESEND_REQUEST,
                        arguments={"operation": "send_batch_emails", "payload": batch_payload},
                    ),
                ),
                should_continue=False,
            )
        ]
    )
    agent = EmailCampaignAgent(
        model=model,
        request=EmailAgentRequest(
            resend_credentials=ResendCredentials(api_key="re_test_1234567890"),
            allowed_resend_operations=("send_batch_emails",),
        ),
        memory_path=store.memory_path,
        resend_client=ResendClient(
            credentials=ResendCredentials(api_key="re_test_1234567890"),
            request_executor=lambda *args, **kwargs: {"data": [{"id": "email_1"}]},
        ),
    )

    with patch(
        "harnessiq.agents.email.campaign.load_email_campaign_recipients",
        return_value=[recipient],
    ):
        result = agent.run(max_cycles=1)

    assert result.status == "completed"
    assert len(store.read_sent_history()) == 1
    assert store.read_sent_history()[0].email_address == "creator@example.com"
    assert agent.build_ledger_outputs()["delivery_records"][0]["email_address"] == "creator@example.com"


def test_email_campaign_agent_includes_prepared_batch_in_parameter_sections(tmp_path) -> None:
    store = EmailCampaignMemoryStore(memory_path=tmp_path / "campaign-b")
    store.prepare()
    store.write_source_config(
        MongoRecipientSourceConfig(
            connection_uri_env_var="MONGODB_URI",
            database="warehouse",
            collection="instagram_leads",
        )
    )
    store.write_campaign_config(
        EmailCampaignConfig(
            from_address="HarnessIQ <hello@example.com>",
            subject="Hello {{name}}",
            text_body="Hi {{name}}",
        )
    )
    model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
    agent = EmailCampaignAgent(
        model=model,
        request=EmailAgentRequest(
            resend_credentials=ResendCredentials(api_key="re_test_1234567890"),
            allowed_resend_operations=("send_batch_emails",),
        ),
        memory_path=store.memory_path,
    )

    with patch(
        "harnessiq.agents.email.campaign.load_email_campaign_recipients",
        return_value=[EmailCampaignRecipient(email_address="creator@example.com", name="Creator A")],
    ):
        agent.run(max_cycles=1)

    assert any(section.title == "Prepared Batch Payload" for section in model.requests[0].parameter_sections)
