# Codebase Best Practices

This artifact is a generalized handbook for reducing tech debt before it lands. It is written for experienced engineers who care less about style points and more about whether a system stays understandable, adaptable, and safe under real change.

Use it as a design prompt before you add a module, a workflow, a schema, a boundary, or a migration.

## Overview

Tech debt is not mostly about ugly code. It is the cost of hidden assumptions, unstable boundaries, and shortcuts that look harmless when they are local but become expensive when the codebase grows.

The useful way to think about it:

- debt is any decision that makes future change harder than it should be
- the dangerous debt is invisible debt: code that looks reasonable today but hides a wrong model of the system
- the target is not aesthetic purity; the target is low surprise under change, failure, and scale

The central habit behind low-debt systems is simple:

- make the implicit explicit

Give important things a name, a type, a boundary, an owner, a lifecycle, and a failure mode. When something important is only "understood by the team" or "obvious from context", debt is already forming.

## Mental Models

### 1. Optimize for change radius

Ask this before merging:

- If this concept changes, how many files, modules, or services move with it?

The best proxy for debt is often blast radius. If one business rule is implemented in six places, the codebase is telling you the abstraction is wrong.

```python
class UserIdentity:
    @property
    def display_name(self) -> str:
        return self.preferred_name or f"{self.first_name} {self.last_name}".strip()
```

One home for one rule. Lower blast radius. Lower debt.

### 2. Separate what, how, and when

Most systems become muddy because these three concerns get fused:

- what: business or domain behavior
- how: infrastructure and implementation details
- when: orchestration, scheduling, workflow order

When they are collapsed together, code becomes hard to test, hard to reuse, and hard to move.

```python
def run(config: Config) -> None:
    users = repo.fetch_inactive_users()       # how
    pending = find_users_to_notify(users)     # what
    notifier.send_all(pending)                # how
```

The scheduler or route should decide when to run. The domain should decide what is true. The infrastructure should decide how bytes move.

### 3. Design from invariants, not from validation

The strongest code does not repeatedly check whether state is valid. It constructs valid state once and then relies on that guarantee.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class SubmittableOrder:
    order_id: str
    item_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.order_id.strip():
            raise ValueError("order_id must not be blank")
        if not self.item_ids:
            raise ValueError("item_ids must not be empty")
```

If a function accepts `SubmittableOrder`, it should not have to keep re-checking whether the order can be submitted.

### 4. A boundary is only real if misuse is hard

A cultural rule is weak. A mechanical rule is durable.

Examples:

- import rules enforced in CI
- JSON schemas enforced at tool boundaries
- startup config validation
- constructors that reject invalid state
- public module surfaces that hide internals

If a boundary can be violated casually, it will be violated under pressure.

### 5. Dependency direction matters more than file count

A module graph should be one-way. Cycles are one of the clearest signals that two modules know too much about each other.

Bad:

- `users -> billing`
- `billing -> users`

Better:

- `users -> accounts`
- `billing -> accounts`

When a cycle appears, the usual fix is not "live with it". The fix is to extract the unnamed shared concept.

### 6. Each function gets a limited surprise budget

A function, class, or module is allowed one major source of surprise:

- mutation
- I/O
- network call
- state transition
- expensive computation

If one unit loads files, mutates state, calls a remote API, and applies business rules, it is too many things at once.

### 7. Seams are strategic assets

A seam is any point where behavior can change without editing both sides:

- interface
- protocol
- adapter
- message contract
- router
- plugin hook

Seams are what let you migrate safely, test locally, and replace one subsystem without touching all callers.

### 8. Treat internal APIs like public ones

In a large codebase, another internal module is "another team" from the perspective of change management.

If a module is imported broadly:

- give it a stable public surface
- deprecate deliberately
- do not let callers depend on internals

### 9. Delete aggressively

Dead code is not neutral. It confuses new engineers, slows refactors, inflates CI, and encourages cargo-cult reuse. Version control already remembers the past.

### 10. Prefer boring solutions for recurring problems

The more ordinary the problem, the less appetite you should have for novelty. Novelty without lasting leverage becomes maintenance tax.

## Golden Rules

1. Put each concept in one obvious home.
2. Make illegal states impossible or at least difficult to construct.
3. Make failures part of the contract, not an undocumented side effect.
4. Keep orchestration separate from transport and storage concerns.
5. Do not let callers know lower-layer details to use an abstraction correctly.
6. If a new flag creates multiple code paths, stop and look for a new abstraction.
7. Never hide ordering requirements in object lifecycle or call sequence.
8. Keep dependency graphs acyclic.
9. Standardize common patterns once and reuse them everywhere.
10. Validate configuration at startup, not at 2 a.m. in production.
11. Write tests against behavior and contracts, not against private implementation.
12. Design migrations to be incremental and reversible.
13. Make side effects explicit.
14. Use durable state instead of relying on process memory for important workflow continuity.
15. Every TODO needs an owner and an exit plan or it should not exist.

## Practical Questions To Ask Before Merging

- What changes together, and does that concept already have a single home?
- If this workflow needed to run from an API, a job, and a CLI, where would the reusable part live?
- Can this module be used correctly without reading its internals?
- What has to be true for this code to be safe, and where is that enforced?
- If the implementation changes but the contract stays the same, will the tests stay green?
- If the author leaves, will the next engineer know where to extend this?
- If this feature doubles in scope, what breaks first?

## Code Snippets

### Make invalid states harder to represent

```python
# Bad: caller must know exactly one contact method should be present.
def send_notification(user_id: str, email: str | None, phone: str | None) -> None:
    ...

# Better: the boundary owns the invariant.
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class EmailContact:
    address: str

@dataclass(frozen=True, slots=True)
class PhoneContact:
    number: str

Contact = EmailContact | PhoneContact

def send_notification(user_id: str, contact: Contact) -> None:
    match contact:
        case EmailContact(address=addr):
            _send_email(user_id, addr)
        case PhoneContact(number=num):
            _send_sms(user_id, num)
```

### Make errors explicit

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    value: T

@dataclass(frozen=True, slots=True)
class Err:
    code: str
    message: str
    context: dict[str, object]

Result = Ok[T] | Err

def get_user(user_id: str) -> Result[dict[str, object]]:
    if not user_id.strip():
        return Err("INVALID_INPUT", "user_id must not be blank", {"user_id": user_id})
    row = repo.find_user(user_id)
    if row is None:
        return Err("NOT_FOUND", "user was not found", {"user_id": user_id})
    return Ok(row)
```

### Keep routes thin and move workflow orchestration out

Testability is not the root issue here. Coupling is.

```python
# Better: route translates HTTP only.
@router.post("/orders", status_code=201)
async def create_order(payload: CreateOrderPayload) -> OrderResponse:
    result = CreateOrderUseCase().execute(user_id=payload.user_id, items=payload.items)
    return to_http_response(result)


class CreateOrderUseCase:
    def execute(self, *, user_id: str, items: list[ItemInput]) -> Result[Order]:
        user = self._users.get(user_id)
        if user is None:
            return Err("USER_NOT_FOUND", "Unknown user", {"user_id": user_id})
        inventory = self._inventory.check(items)
        if not inventory.available:
            return Err("OUT_OF_STOCK", "Inventory unavailable", {})
        order = self._orders.create(user=user, items=items)
        self._mailer.send_confirmation(user.email, order)
        return Ok(order)
```

The win is larger than tests:

- the same workflow can be used from a job or CLI
- transport details do not infect business logic
- bugs are easier to isolate because HTTP concerns and workflow concerns are not mixed

### Use explicit retry policy

```python
import time

def with_retry(fn, *, attempts: int = 3, base_delay_s: float = 0.5):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except RetryableError as exc:
            last_error = exc
            time.sleep(base_delay_s * (2 ** (attempt - 1)))
        except NonRetryableError:
            raise
    raise MaxRetriesExceeded() from last_error
```

Retry only known retryable failures, record what happened, and treat retry budget as part of the design.

### Extract the shared concept instead of accepting a cycle

```python
# Bad:
# users -> billing
# billing -> users

from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class UserDeactivated:
    user_id: str
    occurred_at: datetime


class UserService:
    def deactivate(self, user_id: str) -> UserDeactivated:
        self._repo.deactivate(user_id)
        return UserDeactivated(user_id=user_id, occurred_at=datetime.utcnow())


class BillingService:
    def handle_user_deactivated(self, event: UserDeactivated) -> None:
        self._subscriptions.cancel_for_user(event.user_id)
```

The use case or workflow layer wires the two together. The services do not import each other.

### Validate configuration on startup

```python
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    database_url: str
    webhook_url: str
    max_retries: int = Field(default=3, ge=1)

config = AppConfig.model_validate(load_env())
```

Broken config should stop the process immediately, not become a production incident later.

## Generalized Scenarios

### Scenario 1: "Just add a flag"

Flags grow path count faster than they grow clarity.

If you see:

```python
def generate_report(data, include_headers=True, legacy=False, for_export=False):
    ...
```

Pause and ask:

- are these really modes of one concept?
- or are they separate strategies sharing some preparation logic?

Usually the stable move is:

- one preparation path
- multiple formatter or strategy objects

### Scenario 2: Route as workflow engine

If an API handler parses input, runs business logic, performs storage operations, translates errors, and emits side effects, the route is over-occupying the boundary.

Routes should usually do:

- parse and validate transport input
- call a use case or workflow object
- translate domain results back to transport output

The same logic should be runnable without HTTP existing.

### Scenario 3: Hidden temporal coupling

Bad systems quietly require:

- call `connect()` first
- then call `warm_cache()`
- then call `load_templates()`
- then maybe it works

Prefer constructors, builders, or factories that produce already-valid objects. Construction should establish the invariant once.

### Scenario 4: Background jobs treated as scripts

Jobs accumulate debt because people treat them as unimportant glue.

A stable job has:

- pure or mostly pure business logic
- injected repositories/notifiers/clients
- a thin entrypoint for wiring and scheduling
- deterministic inputs like `as_of`

### Scenario 5: MongoDB schema design

The same anti-cycle thinking applies to document models, but MongoDB gives you three tools:

- embed when the child does not need strong independent identity and is loaded with the parent
- use one-way references when ownership is clear
- denormalize snapshots when read patterns need copied data more than live joins

Avoid bidirectional references unless there is a very strong reason. They tend to create application-level join debt and mirrored repository coupling.

Example:

```python
# Better: orders point to users; users do not store order_ids.
user = {"_id": "user_123", "name": "Alice"}
order = {"_id": "order_456", "user_id": "user_123", "total": 99.99}
```

If both sides "need each other", there is often an unnamed concept or a denormalized view you should model instead.

### Scenario 6: Dependency cycle pressure

A cycle usually begins as a reasonable local shortcut:

- billing needs user information
- later users need to cancel billing
- now both modules import each other

The fix is usually extraction:

- shared event
- shared identity/account model
- shared protocol
- shared adapter or use case

The cycle is a symptom. The unnamed concept is the root cause.

### Scenario 7: Large-codebase drift

At scale, individual discipline is not enough. Large codebases need mechanical governance:

- import rules in CI
- clear module ownership
- public internal APIs
- canonical libraries for repeated concerns
- migration playbooks
- dead-code deletion
- architecture docs kept current

Without that, "good engineers" still create a ball of mud because the system itself does not resist drift.

## Large Codebase Rules

### Enforce boundaries mechanically

Use tooling, not shared memory, to protect architecture:

- import linter
- forbidden dependency checks
- package visibility rules
- schema validation
- static checks

### Keep the dependency graph acyclic

Acyclic graphs do not guarantee quality, but cyclic graphs reliably predict friction:

- change becomes harder to localize
- testing becomes harder to isolate
- extraction becomes harder to perform
- architecture stops being composable

### Standardize repeated solutions

If there are seven different ways to do retries, configuration loading, HTTP requests, storage records, or error translation, the codebase is already paying tax.

Create one canonical path and make deviation expensive.

### Treat migrations like product work

A migration is not a chore wedged between features. It is a real feature with rollout stages, safety properties, and operational consequences.

Use patterns like:

- expand/contract
- dual write then cutover
- compatibility shims
- feature-flagged rollouts
- reversible deploy steps

### Protect public surfaces inside the monolith

Not every file is public. Not every symbol should be imported directly.

Healthy large repos publish a stable surface for broadly used areas and keep internals private by default.

### Delete dead code and stale patterns

What survives in the tree becomes part of the cognitive load. If a pattern is no longer blessed, remove it or actively deprecate it.

## Review Heuristics

Strong signs:

- constructors enforce invariants
- configuration is typed and validated
- boundaries are obvious from imports
- tests assert behavior, not internals
- one concept has one home
- orchestration is reusable across transports
- migrations have rollback shape

Debt signals:

- flags multiplying paths
- callers coordinating lower-level ordering
- functions returning raw dicts with hidden shape contracts
- module A importing module B and B importing A
- transport-layer exceptions escaping into business code
- "temporary" duplicate logic with no consolidation plan
- dead code kept "just in case"

## How This Maps To Harnessiq

This repo already uses several strong low-debt patterns:

- `harnessiq/agents/` is primarily orchestration. `harnessiq/agents/base/agent.py` centralizes the runtime loop, tool execution, transcript handling, and ledger flow instead of duplicating that logic per harness.
- `harnessiq/shared/` encodes stable types, durable-memory models, and constructor-level validation. Modules like `harnessiq/shared/leads.py` are good examples of invariant-first design.
- `harnessiq/tools/` provides executable seams. Agents consume tool surfaces rather than embedding large blocks of provider or utility logic inline.
- `harnessiq/providers/` splits provider integrations into API helpers, clients, and operation catalogs. That keeps transport concerns from bleeding everywhere.
- `harnessiq/toolset/` gives the repo a canonical composition surface so callers do not need to reinvent tool assembly.
- `tests/` tend to validate behavior and contracts rather than coupling tightly to internals, which is the right default.
- durable memory, stable instance ids, and ledger output reduce hidden process state and improve resumability and debuggability

The best way to keep this repo low-debt as it grows is to preserve those boundaries and tighten them where they still leak.

## Default Pre-Implementation Checklist

Before adding a new subsystem, ask:

1. What is the domain concept?
2. Where does the invariant live?
3. What is the orchestration layer?
4. What is the stable public surface?
5. Which direction should dependencies flow?
6. What should be reusable versus product-specific?
7. What migration or deprecation path will exist if this shape changes later?

If you can answer those cleanly before coding, you are already paying down debt that many teams only discover months later.
