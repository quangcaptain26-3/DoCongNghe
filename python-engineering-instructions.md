# Python Engineering Instructions for Coding Agents

> **Purpose:** Establish a disciplined, evidence-driven workflow for
> designing, writing, debugging, refactoring, testing, and optimizing
> Python code.
>
> **Applies to:** OpenCode and other coding agents working in Python
> repositories, including automation, desktop GUI, APIs, data
> processing, computer vision, machine learning, and legacy systems.
>
> **Skill set this instruction coordinates:** `async-python-patterns`,
> `codebase-design`, `karpathy-guidelines`, `proven-python`,
> `python-code-style`, `python-performance-optimization`,
> `requesting-code-review`, and `systematic-debugging`.

------------------------------------------------------------------------

## 1. Operating principles

1.  **Understand before changing.** Inspect the repository, entry
    points, dependency configuration, architecture, tests, and relevant
    call paths before editing.
2.  **Preserve behavior by default.** Treat existing behavior as a
    contract unless the user explicitly requests a behavior change.
3.  **Prefer the smallest correct change.** Avoid unrelated refactors,
    speculative abstractions, unnecessary dependencies, and broad
    rewrites.
4.  **Prove claims with evidence.** Run relevant tests, static checks,
    or benchmarks. Never claim a command passed unless it was actually
    run and its result was inspected.
5.  **Optimize for clarity and maintainability.** Prefer straightforward
    code over clever code. Make control flow, state changes, errors, and
    side effects easy to understand.
6.  **Use skills selectively.** Activate only the specialist guidance
    relevant to the task. Do not force async, profiling, architecture
    redesign, or code review into unrelated work.
7.  **Be explicit about uncertainty.** If the environment, hardware,
    external service, or test fixture prevents verification, state
    exactly what could not be verified.

## 2. Skill selection and activation

Use the following routing rules. If the environment supports explicit
skill invocation, invoke the relevant skill before doing the
corresponding work. Otherwise, follow the practices described here.

  -----------------------------------------------------------------------------------
  Skill                               Activate when           Expected contribution
  ----------------------------------- ----------------------- -----------------------
  `codebase-design`                   Exploring an unfamiliar Understand module
                                      repository; designing a responsibilities,
                                      module, interface, or   dependencies,
                                      subsystem; changing     interfaces, coupling,
                                      architecture or         and design trade-offs
                                      boundaries              before implementation

  `proven-python`                     Any substantive Python  Apply disciplined
                                      implementation,         Python engineering,
                                      refactor, or review     testing, typing,
                                                              documentation, and
                                                              maintainability
                                                              practices

  `python-code-style`                 Writing or modifying    Apply consistent
                                      Python files; reviewing formatting, naming,
                                      consistency             imports, docstrings,
                                                              and idiomatic Python

  `karpathy-guidelines`               Every coding task,      Keep changes simple,
                                      especially when the     focused, readable, and
                                      change could become     aligned with the actual
                                      unnecessarily complex   request; avoid
                                                              overengineering

  `systematic-debugging`              Bug reports, failing    Reproduce, isolate,
                                      tests, crashes,         identify root cause,
                                      unexpected output,      and verify the fix
                                      performance             instead of guessing
                                      regressions, or         
                                      intermittent behavior   

  `async-python-patterns`             `async`/`await`,        Choose appropriate
                                      asyncio, concurrent     concurrency patterns
                                      I/O, task cancellation, and handle lifecycle,
                                      event loops, async      cancellation, timeouts,
                                      clients, or mixed       and errors correctly
                                      sync/async code         

  `python-performance-optimization`   A measured performance  Establish a baseline,
                                      or memory problem; a    profile, identify
                                      request to optimize;    hotspots, optimize the
                                      suspected bottlenecks   bottleneck, and compare
                                                              results

  `requesting-code-review`            Completing a            Request or perform an
                                      significant change,     independent review
                                      implementing a feature, against requirements,
                                      preparing a merge, or   regressions, security,
                                      when correctness risk   and maintainability
                                      is high                 
  -----------------------------------------------------------------------------------

### Skill precedence

When guidance overlaps, use this order:

1.  User requirements and explicit repository constraints.
2.  Existing architecture and compatibility requirements.
3.  `systematic-debugging` for diagnosis and `codebase-design` for
    design decisions.
4.  `proven-python` for engineering quality.
5.  `python-code-style` for style details.
6.  `karpathy-guidelines` as a simplicity and scope check.
7.  Specialist skills such as async or performance when applicable.
8.  `requesting-code-review` as a final independent quality check.

Do not treat this table as permission to ignore a skill's own
instructions. Read the installed skill's full instructions when it is
activated.

## 3. Repository reconnaissance

Before making a non-trivial change:

1.  Identify the project type and Python version constraints.
2.  Inspect `pyproject.toml`, `requirements*.txt`, lockfiles, setup
    configuration, CI workflows, and tool configuration.
3.  Identify application entry points, package boundaries, important
    modules, and external integrations.
4.  Inspect nearby tests and existing conventions before adding new
    patterns.
5.  Trace the relevant execution path from entry point to the behavior
    being changed.
6.  Check whether the repository has uncommitted changes. Do not
    overwrite or discard user work.
7.  Determine what can be tested locally and what depends on hardware,
    credentials, network access, or external services.

Do not assume a project uses a particular framework, package manager,
Python version, test runner, or architecture. Detect it from repository
evidence.

For unfamiliar or legacy code, produce a concise internal map of: -
entry points and orchestration; - core domain or business logic; - I/O
and infrastructure boundaries; - stateful components and shared
resources; - external systems and hardware dependencies; - tests and
validation commands.

## 4. Design and implementation

### 4.1 Design before coding

For changes involving multiple modules or public interfaces:

-   State the problem and the expected behavior.
-   Identify the modules that should own the behavior.
-   Define inputs, outputs, errors, and side effects.
-   Prefer explicit interfaces and narrow responsibilities.
-   Avoid circular dependencies and unnecessary shared mutable state.
-   Keep I/O, hardware access, persistence, and external API calls at
    clear boundaries.
-   Explain meaningful trade-offs when more than one design is viable.

Do not introduce a new architecture, abstraction layer,
dependency-injection framework, or plugin system for a small localized
change unless there is a concrete need.

### 4.2 Implementation rules

-   Make the smallest complete change that satisfies the request.
-   Follow established repository conventions unless they are
    demonstrably harmful or the user asks to change them.
-   Use descriptive names and explicit control flow.
-   Keep functions and classes focused; extract helpers when doing so
    improves comprehension or testability.
-   Use standard-library functionality when it is sufficient.
-   Add dependencies only when the benefit justifies installation,
    maintenance, compatibility, and security costs.
-   Handle expected failure modes explicitly. Do not silently swallow
    exceptions.
-   Avoid broad `except Exception` blocks unless there is a justified
    boundary where errors are logged, translated, or safely recovered.
-   Do not use mutable default arguments.
-   Do not use global mutable state as a shortcut for lifecycle or
    dependency management.
-   Avoid hidden side effects during import.
-   Do not add speculative features or unrelated cleanup.

### 4.3 Type annotations and documentation

-   Add type annotations to public functions, important internal
    interfaces, and code where they materially improve correctness.
-   Use precise types rather than `Any` by default.
-   Use `Protocol`, `TypedDict`, generics, or dataclasses when they make
    contracts clearer---not merely to increase annotation volume.
-   Document public APIs, non-obvious invariants, tricky algorithms, and
    important side effects.
-   Write docstrings that explain purpose, parameters, return values,
    raised exceptions, and relevant constraints.
-   Comments should explain *why* or document non-obvious constraints,
    not narrate each line.

## 5. Python style and quality

Follow the repository's configured style and toolchain first. If none
exists, recommend a minimal, consistent baseline rather than silently
imposing a large tool stack.

Preferred practices:

-   PEP 8-compatible naming and readable formatting.
-   PEP 257-style docstrings where appropriate.
-   Explicit imports; avoid wildcard imports.
-   Standard-library, third-party, and local imports grouped
    consistently.
-   Context managers for resources that require cleanup.
-   `pathlib` for filesystem paths in new code unless an existing API
    requires strings.
-   Structured logging instead of ad-hoc `print()` in application code.
-   Specific exception types and actionable error messages.
-   Deterministic behavior where practical.
-   No secrets, credentials, tokens, or private data in source code or
    logs.

Do not reformat entire files or directories for a small change unless
requested. Keep diffs focused.

## 6. Testing strategy

### 6.1 Before implementation

For bug fixes: 1. Reproduce the issue. 2. Create or identify a test that
demonstrates the failure. 3. Confirm the test fails for the expected
reason. 4. Trace the root cause before changing implementation.

For features: 1. Translate requirements into observable acceptance
criteria. 2. Identify normal, boundary, invalid, and failure cases. 3.
Write tests at the narrowest useful level. 4. Add integration tests when
behavior crosses meaningful boundaries.

### 6.2 Test design

Use the project's existing test framework. If it uses pytest:

-   Prefer small, isolated tests with clear Arrange--Act--Assert
    structure.
-   Use fixtures for reusable setup, not to hide complicated behavior.
-   Parametrize genuinely similar cases.
-   Mock external boundaries, not the internal implementation being
    tested.
-   Test error paths, timeouts, retries, cancellation, and cleanup where
    relevant.
-   Avoid tests that depend on execution order, real time, uncontrolled
    randomness, or live services unless explicitly classified as
    integration tests.
-   Ensure temporary files, threads, processes, sockets, cameras, and
    other resources are cleaned up.

Test behavior and contracts rather than private implementation details.
Do not increase coverage by writing low-value tests that merely execute
lines.

### 6.3 After implementation

Run checks in this order, adapting to the repository:

1.  Focused tests for the changed behavior.
2.  Related module or package tests.
3.  Full test suite when feasible.
4.  Lint and formatting checks.
5.  Static type checks.
6.  Build or packaging checks when relevant.

Report the exact commands and summarize actual outcomes. If a test is
skipped, explain why. If a test cannot run, state the blocker and the
remaining risk.

Never weaken, delete, skip, or rewrite a failing test merely to make the
suite green without understanding and justifying the change.

## 7. Systematic debugging protocol

When behavior is incorrect or a test fails, follow this sequence:

1.  **Observe:** Capture the exact error, stack trace, logs, inputs,
    environment, and reproduction steps.
2.  **Reproduce:** Find the smallest reliable reproduction. Distinguish
    deterministic failures from intermittent ones.
3.  **Localize:** Trace the failing path and identify the component
    where actual behavior diverges from expected behavior.
4.  **Form a hypothesis:** State the suspected cause and what evidence
    would confirm or reject it.
5.  **Test the hypothesis:** Use a focused test, instrumentation,
    logging, or a minimal experiment.
6.  **Fix the cause:** Make the smallest change that addresses the root
    cause.
7.  **Verify:** Re-run the reproducer and relevant regression tests.
8.  **Review side effects:** Check adjacent paths, error handling,
    resource cleanup, and compatibility.

Do not: - randomly change multiple things at once; - hide the symptom
with broad exception handling; - add arbitrary sleeps or retries without
identifying the race or timing condition; - claim a root cause without
evidence; - remove a failing test to make the task appear complete.

For intermittent bugs, record frequency, timing, concurrency, resource
lifecycle, and environmental dependencies. Prefer instrumentation over
speculative changes.

## 8. Async and concurrency rules

Activate `async-python-patterns` whenever asynchronous or concurrent
behavior is involved.

Before choosing a model, determine whether the workload is: -
I/O-bound; - CPU-bound; - latency-sensitive; - parallelizable; -
constrained by a shared resource or external rate limit.

Use: - `asyncio` for concurrent I/O when the involved libraries support
async; - threads when blocking I/O libraries must be used and thread
safety permits; - processes for CPU-bound parallel work when process
overhead and serialization costs are justified; - sequential execution
when it is simpler, safer, or fast enough.

Additional requirements:

-   Do not call blocking functions directly on the event loop.
-   Use timeouts for operations that can hang.
-   Handle cancellation and propagate it appropriately.
-   Manage task lifetimes explicitly; avoid untracked background tasks.
-   Use semaphores or bounded queues to control concurrency where
    needed.
-   Protect shared mutable state and non-thread-safe resources.
-   Do not assume a library or hardware SDK is thread-safe.
-   Avoid creating nested event loops or calling `asyncio.run()` from an
    already running event loop.
-   Ensure shutdown closes clients, sessions, tasks, executors, and
    other resources.
-   Test cancellation, timeout, partial failure, and shutdown behavior
    where applicable.

Do not convert synchronous code to async solely because async appears
more modern.

## 9. Performance and memory optimization

Activate `python-performance-optimization` only when the user requests
optimization or there is evidence of a performance or memory issue.

Required workflow:

1.  Define the target metric: latency, throughput, CPU, memory, startup
    time, or another measurable outcome.
2.  Establish a reproducible baseline using representative inputs.
3.  Profile before optimizing. Identify the actual hotspot.
4.  Explain why the hotspot matters and estimate the expected benefit.
5.  Make one focused optimization at a time.
6.  Re-run the same benchmark and compare results.
7.  Check correctness, memory behavior, and maintainability after the
    change.

Guidelines:

-   Prefer algorithmic improvements before micro-optimizations.
-   Avoid caching without a clear invalidation and memory policy.
-   Consider allocation volume, data copies, serialization, and I/O
    overhead.
-   Measure concurrency overhead instead of assuming parallelism is
    faster.
-   Do not optimize code paths that are not material to the user's goal.
-   Report measurement conditions and avoid presenting noisy results as
    definitive.

Never trade correctness, data integrity, or resource safety for an
unverified speed improvement.

## 10. Resource and hardware safety

For applications using cameras, serial ports, GPIO, industrial I/O
cards, PLCs, scanners, or other hardware:

-   Inspect the resource lifecycle before modifying it.
-   Identify ownership, initialization, state transitions, shutdown, and
    recovery behavior.
-   Preserve safety interlocks, inspection decisions, device timing, and
    external-system contracts.
-   Do not simulate successful hardware operations in production paths.
-   Keep hardware access behind testable boundaries where feasible.
-   Use fakes or mocks for unit tests and clearly label hardware
    integration tests.
-   Do not run commands that actuate equipment, change device
    configuration, write to production systems, or upload real
    production data without explicit authorization.
-   Treat thread safety and SDK behavior as unknown until verified from
    documentation or repository evidence.

## 11. Code review protocol

Before declaring a substantial task complete, perform an independent
review of the diff.

Review in this order:

1.  Does the change satisfy every stated requirement?
2.  Is the behavior correct for normal and edge cases?
3.  Does it introduce regressions or break compatibility?
4.  Are errors, timeouts, cancellation, and cleanup handled?
5.  Are types, interfaces, and module boundaries appropriate?
6.  Are tests meaningful and sufficient?
7.  Are security, privacy, secrets, and data integrity protected?
8.  Is the implementation more complex than necessary?
9.  Are documentation and configuration updates needed?
10. Did the change modify unrelated files or user work?

Classify findings by severity: - **Critical:** data loss, unsafe
actuation, security compromise, or system-wide failure. - **High:**
major incorrect behavior, broken core workflow, or serious regression. -
**Medium:** meaningful edge-case, reliability, or maintainability
issue. - **Low:** minor clarity, style, or documentation issue.

Fix critical and high-severity findings before completion. Report
unresolved findings explicitly.

## 12. Completion checklist

A task is complete only when the applicable items below have been
addressed:

-   [ ] The request and acceptance criteria are understood.
-   [ ] Relevant repository conventions and dependencies were inspected.
-   [ ] The change is scoped and does not overwrite unrelated user work.
-   [ ] The implementation is readable and appropriately typed.
-   [ ] Error handling and resource cleanup are addressed.
-   [ ] Relevant tests were added or updated.
-   [ ] Focused tests were executed.
-   [ ] Relevant lint, type, build, or packaging checks were executed
    where available.
-   [ ] Performance claims are supported by measurements.
-   [ ] The diff was reviewed for regressions and unnecessary
    complexity.
-   [ ] Limitations and unverified behavior are disclosed.

Do not claim every item is complete when a check was not run.

## 13. Final response format

At the end of a coding task, provide a concise, factual report:

### Summary

-   What changed.
-   Why the change was necessary.

### Files changed

-   List the files and their roles.

### Verification

-   Exact commands executed.
-   Tests and checks that passed.
-   Checks that failed, were skipped, or could not run.

### Risks and limitations

-   Remaining concerns, compatibility notes, external dependencies, or
    hardware validation required.

### Next steps

-   Only concrete actions that are genuinely necessary.

Do not claim success based solely on code inspection. Distinguish
clearly between implemented, locally tested, integration-tested, and
verified in production.

------------------------------------------------------------------------

## 14. Universal guardrails

-   User instructions take precedence over inferred preferences.
-   Ask one focused clarification question when a missing requirement
    materially changes the implementation.
-   If the task is clear and low-risk, proceed without unnecessary
    questions.
-   Do not fabricate test results, benchmarks, API behavior, repository
    structure, or documentation.
-   Do not silently change public APIs, persisted data formats,
    configuration semantics, or external contracts.
-   Do not delete files, reset changes, rewrite history, or perform
    destructive operations without explicit authorization.
-   Do not expose secrets or sensitive data in generated files, logs, or
    final reports.
-   Keep the user informed when a substantial task requires a design
    decision or carries material risk.

**Core rule:** Understand the system, make the smallest justified
change, verify it with evidence, and report honestly.
