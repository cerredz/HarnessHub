# Ticket Index

1. Ticket 1: Introduce foundational GCP client and config primitives
   Description: Add the base `gcloud` package, persisted deployment config, and a shared subprocess-backed `GcloudClient`.
   Dependency: none
   Issue: #288
   URL: https://github.com/cerredz/HarnessHub/issues/288
   PR: #304
   PR URL: https://github.com/cerredz/HarnessHub/pull/304
   Status: implemented, awaiting merge into `main`

2. Ticket 2: Add core GCP command parameters and flag fragments
   Description: Implement the typed command parameter objects and reusable flag builders used by every later command module.
   Dependency: Ticket 1
   Issue: #289
   URL: https://github.com/cerredz/HarnessHub/issues/289
   PR: #306
   PR URL: https://github.com/cerredz/HarnessHub/pull/306
   Status: implemented, awaiting merge into `main`

3. Ticket 3: Add auth, IAM, storage, logging, and monitoring command builders
   Description: Implement pure builders for the non-deployment control-plane command surface.
   Dependency: Ticket 2
   Issue: #290
   URL: https://github.com/cerredz/HarnessHub/issues/290
   PR: #307
   PR URL: https://github.com/cerredz/HarnessHub/pull/307
   Status: implemented, awaiting merge into `main`

4. Ticket 4: Add Cloud Run, Scheduler, Artifact Registry, and Secret Manager command builders
   Description: Implement pure builders for the deployment and secret-management command surface.
   Dependency: Ticket 2
   Issue: #291
   URL: https://github.com/cerredz/HarnessHub/issues/291

5. Ticket 5: Implement Artifact Registry and Cloud Run providers
   Description: Add the first executable deployment providers on top of the command-builder layer.
   Dependency: Ticket 4
   Issue: #292
   URL: https://github.com/cerredz/HarnessHub/issues/292

6. Ticket 6: Implement Scheduler and Secret Manager providers
   Description: Add the remaining deployment-time providers needed for scheduling and secret mutation.
   Dependency: Ticket 4
   Issue: #293
   URL: https://github.com/cerredz/HarnessHub/issues/293

7. Ticket 7: Implement health and IAM providers
   Description: Add environment validation and service-account role management on top of the support command builders.
   Dependency: Ticket 3
   Issue: #294
   URL: https://github.com/cerredz/HarnessHub/issues/294

8. Ticket 8: Implement billing, logging, monitoring, and Cloud Storage providers
   Description: Add the remaining operational providers needed for observability, cost inspection, and raw storage access.
   Dependency: Ticket 3
   Issue: #295
   URL: https://github.com/cerredz/HarnessHub/issues/295

9. Ticket 9: Add `GcpContext` and package exports
   Description: Compose the full provider tree behind one shared context and clean package export surface.
   Dependency: Ticket 5, Ticket 6, Ticket 7, Ticket 8
   Issue: #296
   URL: https://github.com/cerredz/HarnessHub/issues/296

10. Ticket 10: Implement a binding-aware credential bridge
   Description: Reuse the existing repo-local credential binding system to discover harness secrets and sync them into Secret Manager.
   Dependency: Ticket 9
   Issue: #297
   URL: https://github.com/cerredz/HarnessHub/issues/297

11. Ticket 11: Add the `harnessiq gcloud` CLI scaffold
   Description: Register the top-level argparse command family and shared parsing/orchestration helpers.
   Dependency: Ticket 9
   Issue: #298
   URL: https://github.com/cerredz/HarnessHub/issues/298

12. Ticket 12: Add GCP health and credential CLI commands
   Description: Expose init-time validation and credential sync/status flows through the new CLI family.
   Dependency: Ticket 10, Ticket 11
   Issue: #299
   URL: https://github.com/cerredz/HarnessHub/issues/299

13. Ticket 13: Add GCP deployment and operations CLI commands
   Description: Expose build, deploy, schedule, execute, logs, and cost operations through the new CLI family.
   Dependency: Ticket 11
   Issue: #300
   URL: https://github.com/cerredz/HarnessHub/issues/300

14. Ticket 14: Add manifest-driven deployment specs for all harnesses
   Description: Make GCP deployment generic across all harness manifests by deriving deployable commands and metadata from existing manifest/profile state.
   Dependency: Ticket 12, Ticket 13
   Issue: #301
   URL: https://github.com/cerredz/HarnessHub/issues/301

15. Ticket 15: Add a cloud runtime wrapper and GCS-backed memory sync
   Description: Introduce the Cloud Run runtime path that syncs harness memory/profile state to and from GCS for scheduled cloud execution continuity.
   Dependency: Ticket 14
   Issue: #302
   URL: https://github.com/cerredz/HarnessHub/issues/302

16. Ticket 16: Document and verify the end-to-end GCP workflow
   Description: Add user-facing documentation and end-to-end test coverage for the new GCP deployment surface.
   Dependency: Ticket 15
   Issue: #303
   URL: https://github.com/cerredz/HarnessHub/issues/303

Phase 3a complete
Phase 3 complete
