# Local Dictation Docs

Start with the README at the repository root for install, run, update, troubleshooting, and maintainer commands. The numbered docs here preserve the project decisions, test expectations, and manual verification notes.

## Map

- `00_goal_alignment.md` — product goal, MVP behavior, and success criteria.
- `01_requirements.md` — functional requirements, technical requirements, defaults, and acceptance criteria.
- `02_research_findings.md` — technology research and tradeoffs.
- `03_architecture_decisions.md` — accepted architecture decisions.
- `04_implementation_plan.md` — implementation order and runtime flow notes.
- `05_test_plan.md` — automated, doctor, manual smoke, and manual error checks.
- `06_risk_register.md` — known risks and mitigations.
- `07_done_definition.md` — completion criteria.
- `08_manual_verification.md` — current manual checklist and verification history.

## Maintainer Checklist

1. Run the automated tests.
2. Build the installer.
3. Use `08_manual_verification.md` for user-facing checks that need Windows UI, microphone, tray, browser, clipboard, or target-window behavior.

Keep this checklist small. Add steps only after the existing tests or manual verification miss real failures.