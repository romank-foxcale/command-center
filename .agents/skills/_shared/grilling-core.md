# Grilling with docs: shared protocol

Follow this protocol together with the specific skill.

## Run the grilling

1. First extract facts from the code, catalog, CI, docs and executable contracts. Do not ask what can be reliably inferred.
2. Separate `fact`, `decision`, `assumption` and `unknown`. Keep evidence for each fact; for each decision, keep the alternatives and consequences.
3. Ask 1–3 related questions per turn. Close the questions that change the architecture, scope or acceptance first.
4. On a vague answer, ask for an example, a boundary, a counterexample or a verification criterion.
5. Surface contradictions between answers, evidence and the model. Show the conflict briefly and reach a single decision.
6. After a significant answer, update the model and the unknowns; do not create a document for every reply.

## Keep only what is useful

Write every stored artifact in English, whatever language the conversation uses.

- An executable process goes in Nix, not Markdown.
- An accepted long-lived decision becomes an ADR following `templates/decision.md`.
- A significant domain term goes in `docs/glossary/` following `templates/glossary-term.md`.
- A hack or debt goes in an atomic note.
- Do not store the transcript, rejected alternatives or internal reasoning.

Do not duplicate a fact across the catalog, plan and docs: choose a source of truth and reference it from the others.

## Finish on evidence

1. State the outcome, non-goals and observable acceptance criteria.
2. Give evidence for every critical fact.
3. List unresolved unknowns and their impact; do not disguise them as assumptions.
4. Check artifacts and relations with the relevant validators.
