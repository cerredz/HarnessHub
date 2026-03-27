"""Pure flag fragment builders for GCP command composition."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands.params import SecretRef


def region_flag(region: str) -> list[str]:
    return [f"--region={region}"]


def location_flag(location: str) -> list[str]:
    return [f"--location={location}"]


def format_json() -> list[str]:
    return ["--format=json"]


def format_value(field: str) -> list[str]:
    return [f"--format=value({field})"]


def quiet() -> list[str]:
    return ["--quiet"]


def limit_flag(value: int) -> list[str]:
    return [f"--limit={value}"]


def filter_flag(expression: str) -> list[str]:
    return [f"--filter={expression}"]


def async_flag() -> list[str]:
    return ["--async"]


def wait_flag() -> list[str]:
    return ["--wait"]


def image_flag(image_url: str) -> list[str]:
    return [f"--image={image_url}"]


def cpu_flag(cpu: str) -> list[str]:
    return [f"--cpu={cpu}"]


def memory_flag(memory: str) -> list[str]:
    return [f"--memory={memory}"]


def timeout_flag(seconds: int) -> list[str]:
    return [f"--task-timeout={seconds}s"]


def retries_flag(max_retries: int) -> list[str]:
    return [f"--max-retries={max_retries}"]


def parallelism_flag(parallelism: int) -> list[str]:
    if parallelism == 0:
        return []
    return [f"--parallelism={parallelism}"]


def task_count_flag(count: int) -> list[str]:
    if count == 1:
        return []
    return [f"--tasks={count}"]


def service_account_flag(email: str) -> list[str]:
    if not email:
        return []
    return [f"--service-account={email}"]


def set_env_vars_flag(env_vars: dict[str, str]) -> list[str]:
    if not env_vars:
        return []
    pairs = ",".join(f"{key}={value}" for key, value in env_vars.items())
    return [f"--set-env-vars={pairs}"]


def update_env_vars_flag(env_vars: dict[str, str]) -> list[str]:
    if not env_vars:
        return []
    pairs = ",".join(f"{key}={value}" for key, value in env_vars.items())
    return [f"--update-env-vars={pairs}"]


def remove_env_vars_flag(keys: list[str]) -> list[str]:
    if not keys:
        return []
    return [f"--remove-env-vars={','.join(keys)}"]


def clear_env_vars_flag() -> list[str]:
    return ["--clear-env-vars"]


def set_secrets_flag(secrets: list[SecretRef]) -> list[str]:
    return [
        f"--set-secrets={secret.env_var}={secret.secret_name}:{secret.version}"
        for secret in secrets
    ]


def remove_secrets_flag(env_vars: list[str]) -> list[str]:
    if not env_vars:
        return []
    return [f"--remove-secrets={','.join(env_vars)}"]


def schedule_flag(cron_expression: str) -> list[str]:
    return [f"--schedule={cron_expression}"]


def timezone_flag(timezone: str) -> list[str]:
    return [f"--time-zone={timezone}"]


def uri_flag(uri: str) -> list[str]:
    return [f"--uri={uri}"]


def http_method_flag(method: str = "POST") -> list[str]:
    return [f"--http-method={method}"]


def oauth_sa_flag(email: str) -> list[str]:
    return [f"--oauth-service-account-email={email}"]


def message_body_flag(body: str = "{}") -> list[str]:
    return [f"--message-body={body}"]


def description_flag(text: str) -> list[str]:
    if not text:
        return []
    return [f"--description={text}"]


def replication_policy_flag(policy: str = "automatic") -> list[str]:
    return [f"--replication-policy={policy}"]


def data_file_stdin_flag() -> list[str]:
    return ["--data-file=-"]


def secret_flag(secret_name: str) -> list[str]:
    return [f"--secret={secret_name}"]


def version_flag(version: str = "latest") -> list[str]:
    return [f"--version={version}"]


def storage_location_flag(location: str) -> list[str]:
    return [f"--location={location}"]


def uniform_bucket_level_access_flag() -> list[str]:
    return ["--uniform-bucket-level-access"]


def member_flag(member: str) -> list[str]:
    return [f"--member={member}"]


def role_flag(role: str) -> list[str]:
    return [f"--role={role}"]


def display_name_flag(name: str) -> list[str]:
    if not name:
        return []
    return [f"--display-name={name}"]


def repository_format_flag(fmt: str = "docker") -> list[str]:
    return [f"--repository-format={fmt}"]


def tag_flag(tag_uri: str) -> list[str]:
    return [f"--tag={tag_uri}"]


def order_flag(order: str = "desc") -> list[str]:
    return [f"--order={order}"]


def freshness_flag(freshness: str) -> list[str]:
    return [f"--freshness={freshness}"]


def channel_type_flag(channel_type: str) -> list[str]:
    return [f"--type={channel_type}"]


def channel_labels_flag(labels: dict[str, str]) -> list[str]:
    pairs = ",".join(f"{key}={value}" for key, value in labels.items())
    return [f"--channel-labels={pairs}"]


def condition_filter_flag(filter_str: str) -> list[str]:
    return [f"--condition-filter={filter_str}"]


def notification_channels_flag(channels: list[str]) -> list[str]:
    if not channels:
        return []
    return [f"--notification-channels={','.join(channels)}"]
