from __future__ import annotations

from harnessiq.shared.email_campaign import (
    EmailCampaignConfig,
    EmailCampaignRecipient,
    MongoRecipientSourceConfig,
    build_resend_batch_payload,
    load_email_campaign_recipients,
    render_email_campaign_template,
)


class _FakeMongoClient:
    def __init__(self, documents):
        self.documents = list(documents)
        self.calls: list[dict[str, object]] = []

    def find_documents(self, *, filter=None, projection=None, limit=None):
        self.calls.append({"filter": filter, "projection": projection, "limit": limit})
        payload = list(self.documents)
        if limit is not None:
            payload = payload[:limit]
        return payload


def test_load_email_campaign_recipients_dedupes_and_filters_sent_emails() -> None:
    source_config = MongoRecipientSourceConfig(
        connection_uri_env_var="MONGODB_URI",
        database="warehouse",
        collection="instagram_leads",
    )
    client = _FakeMongoClient(
        [
            {
                "record": {
                    "emails": ["creator@example.com", "CREATOR@example.com", "team@example.com"],
                    "source_url": "https://www.instagram.com/creator-a/",
                    "title": "Creator A",
                }
            },
            {
                "record": {
                    "emails": ["coach@example.com"],
                    "source_url": "https://www.instagram.com/creator-b/",
                    "title": "Creator B",
                }
            },
        ]
    )

    recipients = load_email_campaign_recipients(
        source_config,
        limit=10,
        sent_emails={"team@example.com"},
        mongo_client=client,
    )

    assert [recipient.email_address for recipient in recipients] == [
        "creator@example.com",
        "coach@example.com",
    ]
    assert recipients[0].metadata["source_url"] == "https://www.instagram.com/creator-a/"
    assert recipients[0].name == "Creator A"
    assert client.calls[0]["limit"] == 10


def test_render_email_campaign_template_and_build_payload() -> None:
    recipient = EmailCampaignRecipient(
        email_address="creator@example.com",
        name="Creator A",
        metadata={"username": "creator-a"},
    )

    assert render_email_campaign_template("Hi {{name}} from {{username}}", recipient) == "Hi Creator A from creator-a"

    payload = build_resend_batch_payload(
        EmailCampaignConfig(
            from_address="HarnessIQ <hello@example.com>",
            subject="Hello {{name}}",
            html_body="<p>Hi {{username}}</p>",
            text_body="Hi {{email}}",
            reply_to="reply@example.com",
        ),
        [recipient],
    )

    assert payload == [
        {
            "from": "HarnessIQ <hello@example.com>",
            "html": "<p>Hi creator-a</p>",
            "reply_to": "reply@example.com",
            "subject": "Hello Creator A",
            "text": "Hi creator@example.com",
            "to": ["creator@example.com"],
        }
    ]
