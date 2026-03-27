# Harnessiq CLI Reference

This artifact is generated from the live `harnessiq/cli/` source tree by `python scripts/sync_repo_docs.py`.

## Snapshot

| Metric | Count |
| --- | --- |
| Top-level commands | 19 |
| Registered command paths | 153 |

Alias paths are included in the registered command total. Canonical commands list aliases where they exist.

## Top-Level Commands

| Command | Direct Subcommands | Description | Source |
| --- | --- | --- | --- |
| harnessiq connect | confluence, discord, google_sheets, linear, mongodb, notion, obsidian, slack, supabase | Configure a global output sink connection | `harnessiq/cli/ledger/commands.py` |
| harnessiq connections | list, remove, test | Inspect or manage configured sink connections | `harnessiq/cli/ledger/commands.py` |
| harnessiq credentials | bind, show, test | Manage persisted harness credential bindings | `harnessiq/cli/platform_commands.py` |
| harnessiq export | - | Export ledger entries in a structured format | `harnessiq/cli/ledger/commands.py` |
| harnessiq inspect | exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Inspect one harness manifest and generated CLI surface | `harnessiq/cli/platform_commands.py` |
| harnessiq instagram | configure, get-emails, prepare, run, show | Manage and run the Instagram keyword discovery agent | `harnessiq/cli/instagram/commands.py` |
| harnessiq leads | configure, prepare, run, show | Manage and run the leads discovery agent | `harnessiq/cli/leads/commands.py` |
| harnessiq linkedin | configure, init-browser, prepare, run, show | Manage and run the LinkedIn agent | `harnessiq/cli/linkedin/commands.py` |
| harnessiq logs | - | Inspect the local audit ledger | `harnessiq/cli/ledger/commands.py` |
| harnessiq models | add, list | Manage reusable provider-backed model profiles | `harnessiq/cli/models/commands.py` |
| harnessiq outreach | configure, prepare, run, show | Manage and run the ExaOutreach agent | `harnessiq/cli/exa_outreach/commands.py` |
| harnessiq prepare | exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Prepare and persist generic config for a harness | `harnessiq/cli/platform_commands.py` |
| harnessiq prompts | activate, clear, current, list, show, text | Inspect bundled master prompts | `harnessiq/cli/master_prompts/commands.py` |
| harnessiq prospecting | configure, init-browser, prepare, run, show | Manage and run the Google Maps prospecting agent | `harnessiq/cli/prospecting/commands.py` |
| harnessiq report | - | Build a cross-agent report from the local ledger | `harnessiq/cli/ledger/commands.py` |
| harnessiq research-sweep | configure, prepare, run, show | Manage and run the ResearchSweepAgent harness | `harnessiq/cli/research_sweep/commands.py` |
| harnessiq run | exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Run a harness through the platform-first CLI | `harnessiq/cli/platform_commands.py` |
| harnessiq show | exa_outreach (outreach), instagram, knowt, leads, linkedin, mission_driven, prospecting, research_sweep (research-sweep), spawn_specialized_subagents | Show persisted platform config and harness state | `harnessiq/cli/platform_commands.py` |
| harnessiq stats | agent, export, instance, rebuild, session, summary | Inspect local stats and analytics snapshots | `harnessiq/cli/stats/commands.py` |

## `harnessiq connect`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq connect confluence | Configure a global confluence sink | `harnessiq/cli/ledger/commands.py` |
| harnessiq connect discord | Configure a global discord sink | `harnessiq/cli/ledger/commands.py` |
| harnessiq connect google_sheets | Configure a global google_sheets sink | `harnessiq/cli/ledger/commands.py` |
| harnessiq connect linear | Configure a global linear sink | `harnessiq/cli/ledger/commands.py` |
| harnessiq connect mongodb | Configure a global mongodb sink | `harnessiq/cli/ledger/commands.py` |
| harnessiq connect notion | Configure a global notion sink | `harnessiq/cli/ledger/commands.py` |
| harnessiq connect obsidian | Configure a global obsidian sink | `harnessiq/cli/ledger/commands.py` |
| harnessiq connect slack | Configure a global slack sink | `harnessiq/cli/ledger/commands.py` |
| harnessiq connect supabase | Configure a global supabase sink | `harnessiq/cli/ledger/commands.py` |

## `harnessiq connections`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq connections list | List configured sink connections | `harnessiq/cli/ledger/commands.py` |
| harnessiq connections remove | Remove a configured sink connection | `harnessiq/cli/ledger/commands.py` |
| harnessiq connections test | Validate that a sink connection can be constructed | `harnessiq/cli/ledger/commands.py` |

## `harnessiq credentials`

| Command | Aliases | Description | Source |
| --- | --- | --- | --- |
| harnessiq credentials bind | - | Bind harness credentials | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials bind exa_outreach | outreach | bind Exa Outreach | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials bind instagram | - | bind Instagram Keyword Discovery | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials bind knowt | - | bind Knowt Content Creator | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials bind leads | - | bind Leads Agent | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials bind linkedin | - | bind LinkedIn Job Applier | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials bind mission_driven | - | bind Mission Driven | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials bind prospecting | - | bind Google Maps Prospecting | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials bind research_sweep | research-sweep | bind Research Sweep | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials bind spawn_specialized_subagents | - | bind Spawn Specialized Subagents | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show | - | Show harness credentials | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show exa_outreach | outreach | show Exa Outreach | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show instagram | - | show Instagram Keyword Discovery | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show knowt | - | show Knowt Content Creator | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show leads | - | show Leads Agent | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show linkedin | - | show LinkedIn Job Applier | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show mission_driven | - | show Mission Driven | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show prospecting | - | show Google Maps Prospecting | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show research_sweep | research-sweep | show Research Sweep | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials show spawn_specialized_subagents | - | show Spawn Specialized Subagents | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test | - | Test harness credentials | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test exa_outreach | outreach | test Exa Outreach | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test instagram | - | test Instagram Keyword Discovery | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test knowt | - | test Knowt Content Creator | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test leads | - | test Leads Agent | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test linkedin | - | test LinkedIn Job Applier | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test mission_driven | - | test Mission Driven | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test prospecting | - | test Google Maps Prospecting | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test research_sweep | research-sweep | test Research Sweep | `harnessiq/cli/platform_commands.py` |
| harnessiq credentials test spawn_specialized_subagents | - | test Spawn Specialized Subagents | `harnessiq/cli/platform_commands.py` |

## `harnessiq inspect`

| Command | Aliases | Description | Source |
| --- | --- | --- | --- |
| harnessiq inspect exa_outreach | outreach | inspect Exa Outreach | `harnessiq/cli/platform_commands.py` |
| harnessiq inspect instagram | - | inspect Instagram Keyword Discovery | `harnessiq/cli/platform_commands.py` |
| harnessiq inspect knowt | - | inspect Knowt Content Creator | `harnessiq/cli/platform_commands.py` |
| harnessiq inspect leads | - | inspect Leads Agent | `harnessiq/cli/platform_commands.py` |
| harnessiq inspect linkedin | - | inspect LinkedIn Job Applier | `harnessiq/cli/platform_commands.py` |
| harnessiq inspect mission_driven | - | inspect Mission Driven | `harnessiq/cli/platform_commands.py` |
| harnessiq inspect prospecting | - | inspect Google Maps Prospecting | `harnessiq/cli/platform_commands.py` |
| harnessiq inspect research_sweep | research-sweep | inspect Research Sweep | `harnessiq/cli/platform_commands.py` |
| harnessiq inspect spawn_specialized_subagents | - | inspect Spawn Specialized Subagents | `harnessiq/cli/platform_commands.py` |

## `harnessiq instagram`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq instagram configure | Persist ICPs, identity, prompt text, and runtime parameters for the Instagram agent | `harnessiq/cli/instagram/commands.py` |
| harnessiq instagram get-emails | Return all persisted discovered emails for the configured Instagram agent | `harnessiq/cli/instagram/commands.py` |
| harnessiq instagram prepare | Create or refresh an Instagram agent memory folder | `harnessiq/cli/instagram/commands.py` |
| harnessiq instagram run | Run the Instagram keyword discovery agent from persisted memory | `harnessiq/cli/instagram/commands.py` |
| harnessiq instagram show | Render the current Instagram agent state as JSON | `harnessiq/cli/instagram/commands.py` |

## `harnessiq leads`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq leads configure | Write company background, ICPs, platforms, and leads runtime configuration | `harnessiq/cli/leads/commands.py` |
| harnessiq leads prepare | Create or refresh a leads agent memory folder | `harnessiq/cli/leads/commands.py` |
| harnessiq leads run | Run the leads SDK agent from persisted CLI state | `harnessiq/cli/leads/commands.py` |
| harnessiq leads show | Render the current leads agent state as JSON | `harnessiq/cli/leads/commands.py` |

## `harnessiq linkedin`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq linkedin configure | Write LinkedIn memory inputs, custom parameters, and managed files | `harnessiq/cli/linkedin/commands.py` |
| harnessiq linkedin init-browser | Open a browser, wait for LinkedIn login, and save the session for future runs | `harnessiq/cli/linkedin/commands.py` |
| harnessiq linkedin prepare | Create or refresh a LinkedIn agent memory folder | `harnessiq/cli/linkedin/commands.py` |
| harnessiq linkedin run | Run the LinkedIn SDK agent from persisted CLI state | `harnessiq/cli/linkedin/commands.py` |
| harnessiq linkedin show | Render the current LinkedIn CLI-managed state as JSON | `harnessiq/cli/linkedin/commands.py` |

## `harnessiq models`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq models add | Add or update a persisted model profile | `harnessiq/cli/models/commands.py` |
| harnessiq models list | List persisted model profiles | `harnessiq/cli/models/commands.py` |

## `harnessiq outreach`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq outreach configure | Write outreach agent search query, identity, runtime params, and additional prompt | `harnessiq/cli/exa_outreach/commands.py` |
| harnessiq outreach prepare | Create or refresh an outreach agent memory folder | `harnessiq/cli/exa_outreach/commands.py` |
| harnessiq outreach run | Run the ExaOutreach agent from persisted CLI state | `harnessiq/cli/exa_outreach/commands.py` |
| harnessiq outreach show | Render the current outreach agent state as JSON | `harnessiq/cli/exa_outreach/commands.py` |

## `harnessiq prepare`

| Command | Aliases | Description | Source |
| --- | --- | --- | --- |
| harnessiq prepare exa_outreach | outreach | prepare Exa Outreach | `harnessiq/cli/platform_commands.py` |
| harnessiq prepare instagram | - | prepare Instagram Keyword Discovery | `harnessiq/cli/platform_commands.py` |
| harnessiq prepare knowt | - | prepare Knowt Content Creator | `harnessiq/cli/platform_commands.py` |
| harnessiq prepare leads | - | prepare Leads Agent | `harnessiq/cli/platform_commands.py` |
| harnessiq prepare linkedin | - | prepare LinkedIn Job Applier | `harnessiq/cli/platform_commands.py` |
| harnessiq prepare mission_driven | - | prepare Mission Driven | `harnessiq/cli/platform_commands.py` |
| harnessiq prepare prospecting | - | prepare Google Maps Prospecting | `harnessiq/cli/platform_commands.py` |
| harnessiq prepare research_sweep | research-sweep | prepare Research Sweep | `harnessiq/cli/platform_commands.py` |
| harnessiq prepare spawn_specialized_subagents | - | prepare Spawn Specialized Subagents | `harnessiq/cli/platform_commands.py` |

## `harnessiq prompts`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq prompts activate | Activate one bundled prompt as always-on project session context for Claude Code and Codex | `harnessiq/cli/master_prompts/commands.py` |
| harnessiq prompts clear | Remove generated Claude Code and Codex prompt injection overlays | `harnessiq/cli/master_prompts/commands.py` |
| harnessiq prompts current | Show the currently active project-scoped master prompt, if any | `harnessiq/cli/master_prompts/commands.py` |
| harnessiq prompts list | List bundled master prompts | `harnessiq/cli/master_prompts/commands.py` |
| harnessiq prompts show | Render one bundled master prompt as JSON | `harnessiq/cli/master_prompts/commands.py` |
| harnessiq prompts text | Print the raw prompt text for one prompt | `harnessiq/cli/master_prompts/commands.py` |

## `harnessiq prospecting`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq prospecting configure | Persist company description, prompts, and parameters for the prospecting agent | `harnessiq/cli/prospecting/commands.py` |
| harnessiq prospecting init-browser | Open a persistent browser session and save it for Google Maps prospecting runs | `harnessiq/cli/prospecting/commands.py` |
| harnessiq prospecting prepare | Create or refresh a Google Maps prospecting memory folder | `harnessiq/cli/prospecting/commands.py` |
| harnessiq prospecting run | Run the Google Maps prospecting agent from persisted memory | `harnessiq/cli/prospecting/commands.py` |
| harnessiq prospecting show | Render the current prospecting agent state as JSON | `harnessiq/cli/prospecting/commands.py` |

## `harnessiq research-sweep`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq research-sweep configure | Persist the research query, prompt text, and parameters for the research sweep harness | `harnessiq/cli/research_sweep/commands.py` |
| harnessiq research-sweep prepare | Create or refresh a research sweep memory folder | `harnessiq/cli/research_sweep/commands.py` |
| harnessiq research-sweep run | Run the ResearchSweepAgent from persisted memory | `harnessiq/cli/research_sweep/commands.py` |
| harnessiq research-sweep show | Render the current research sweep harness state as JSON | `harnessiq/cli/research_sweep/commands.py` |

## `harnessiq run`

| Command | Aliases | Description | Source |
| --- | --- | --- | --- |
| harnessiq run exa_outreach | outreach | run Exa Outreach | `harnessiq/cli/platform_commands.py` |
| harnessiq run instagram | - | run Instagram Keyword Discovery | `harnessiq/cli/platform_commands.py` |
| harnessiq run knowt | - | run Knowt Content Creator | `harnessiq/cli/platform_commands.py` |
| harnessiq run leads | - | run Leads Agent | `harnessiq/cli/platform_commands.py` |
| harnessiq run linkedin | - | run LinkedIn Job Applier | `harnessiq/cli/platform_commands.py` |
| harnessiq run mission_driven | - | run Mission Driven | `harnessiq/cli/platform_commands.py` |
| harnessiq run prospecting | - | run Google Maps Prospecting | `harnessiq/cli/platform_commands.py` |
| harnessiq run research_sweep | research-sweep | run Research Sweep | `harnessiq/cli/platform_commands.py` |
| harnessiq run spawn_specialized_subagents | - | run Spawn Specialized Subagents | `harnessiq/cli/platform_commands.py` |

## `harnessiq show`

| Command | Aliases | Description | Source |
| --- | --- | --- | --- |
| harnessiq show exa_outreach | outreach | show Exa Outreach | `harnessiq/cli/platform_commands.py` |
| harnessiq show instagram | - | show Instagram Keyword Discovery | `harnessiq/cli/platform_commands.py` |
| harnessiq show knowt | - | show Knowt Content Creator | `harnessiq/cli/platform_commands.py` |
| harnessiq show leads | - | show Leads Agent | `harnessiq/cli/platform_commands.py` |
| harnessiq show linkedin | - | show LinkedIn Job Applier | `harnessiq/cli/platform_commands.py` |
| harnessiq show mission_driven | - | show Mission Driven | `harnessiq/cli/platform_commands.py` |
| harnessiq show prospecting | - | show Google Maps Prospecting | `harnessiq/cli/platform_commands.py` |
| harnessiq show research_sweep | research-sweep | show Research Sweep | `harnessiq/cli/platform_commands.py` |
| harnessiq show spawn_specialized_subagents | - | show Spawn Specialized Subagents | `harnessiq/cli/platform_commands.py` |

## `harnessiq stats`

| Command | Description | Source |
| --- | --- | --- |
| harnessiq stats agent | Print one agent aggregate snapshot | `harnessiq/cli/stats/commands.py` |
| harnessiq stats export | Export stats snapshots or flat per-run CSV | `harnessiq/cli/stats/commands.py` |
| harnessiq stats instance | Print one instance aggregate snapshot | `harnessiq/cli/stats/commands.py` |
| harnessiq stats rebuild | Rebuild all stats snapshots from the ledger | `harnessiq/cli/stats/commands.py` |
| harnessiq stats session | Print one session snapshot | `harnessiq/cli/stats/commands.py` |
| harnessiq stats summary | Print repo-wide stats summary | `harnessiq/cli/stats/commands.py` |
