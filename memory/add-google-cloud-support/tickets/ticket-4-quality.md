## Quality Pipeline Results

### Stage 1: Static Analysis

No repository linter or formatter is configured in `pyproject.toml`. I performed manual static review for:

- shared private helper extraction in the Cloud Run builder surface
- deterministic formatting on read commands
- omission of default deployment flags where required by the spec
- absence of explicit project flags across the deploy-surface builders
- package export consistency in `commands/__init__.py`

Result: pass

### Stage 2: Type Checking

No repository type checker is configured. I kept all new builder signatures explicitly annotated and validated the import surface through the full GCP test suite and shell smoke imports.

Result: pass

### Stage 3: Unit Tests

Command run:

```bash
pytest tests/test_gcloud_client.py tests/test_gcloud_config.py tests/test_gcloud_commands_core.py tests/test_gcloud_commands_support.py tests/test_gcloud_commands_deploy.py
```

Observed result:

- 39 tests collected
- 39 tests passed

Coverage highlights:

- Cloud Run create/update shared capacity flags and targeted update helpers
- execution, read, and destructive job commands
- Cloud Scheduler create/update/read/control commands
- Artifact Registry repository/build/image commands
- Secret Manager create/version/access/list/delete/access-binding commands
- package-level `commands` export surface for the deployment modules

Result: pass

### Stage 4: Integration and Contract Tests

Not applicable for this ticket. The deployment builder modules are pure command constructors with no subprocess, filesystem, or remote side effects.

Result: not applicable

### Stage 5: Smoke and Manual Verification

Command run:

```bash
@'
from harnessiq.providers.gcloud import commands as cmd

print(cmd.create_job(cmd.JobSpec(job_name='candidate-a', image_url='us-central1-docker.pkg.dev/proj/repo/image:latest', region='us-central1')))
print(cmd.create_schedule(cmd.ScheduleSpec(
    scheduler_job_name='candidate-a-schedule',
    location='us-central1',
    cron_expression='0 */4 * * *',
    http_uri='https://example.test/run',
    service_account_email='runner@example.test',
)))
print(cmd.submit_build('us-central1-docker.pkg.dev/proj/repo/image:latest'))
print(cmd.add_secret_version('HARNESSIQ_ANTHROPIC_API_KEY'))
'@ | python -
```

Observed output:

- `['run', 'jobs', 'create', 'candidate-a', '--image=us-central1-docker.pkg.dev/proj/repo/image:latest', '--region=us-central1', '--cpu=1', '--memory=512Mi', '--task-timeout=3600s', '--max-retries=1']`
- `['scheduler', 'jobs', 'create', 'http', 'candidate-a-schedule', '--location=us-central1', '--schedule=0 */4 * * *', '--time-zone=UTC', '--uri=https://example.test/run', '--http-method=POST', '--oauth-service-account-email=runner@example.test', '--message-body={}']`
- `['builds', 'submit', '--tag=us-central1-docker.pkg.dev/proj/repo/image:latest', '.']`
- `['secrets', 'versions', 'add', 'HARNESSIQ_ANTHROPIC_API_KEY', '--data-file=-']`

This confirms the deploy-surface builder modules import cleanly and emit deterministic command lists for the core provider paths that will use them next.

Result: pass
