# ERRATA — FP-METHODOLOGY-v0.2-ERRATA-001

**Scope:** narrow audit correction to `FAROUK_METHODOLOGY_SPEC_v0.2.md`.
**Corrected version:** `FAROUK_METHODOLOGY_SPEC_v0.2.1.md` (supersedes v0.2 on the two points below).
**Preserved:** v0.2 is NOT overwritten or deleted. No frozen campaign evidence, no frozen comparison file,
no execution/risk-policy configuration was modified by this correction.

---

## CORRECTION 1 — Scoring frameworks (factual error in v0.2)

**v0.2 said (incorrectly):** in §6 it stated *"Task's '6/6 vs 6/8': actually 6/6 vs a 7-item checklist vs
letter grades"* — i.e. it implied the **6/8** framework did not exist / was a mis-recall. **That is wrong.**

**Verified fact (Farouk's Playbook, FP-EDU-002 `sa-4cb77d9d6b13478a`):** the Playbook contains **all** of
the following, simultaneously:

- **Page 11 — "THE STACK RULE" (6 boxes):** `6/6 PASS = A+++ (full lot)`, `5/6 = A (half lot)`,
  `4/6 = watch`, `<4/6 = skip`.
- **Page 21 — "STACK COUNT" (8 boxes, Multi-Timeframe Stack checklist):**
  `at least 6/8 boxes ticked = A+++`, `5/8 = half lot`, `<5 = skip` — **and** the same page states
  **"THE RULE: All boxes must be checked. If even ONE is missing — skip the trade."**
- **Page 12 — letter-grade confluence:** separate `C / B / A / A+ / A+++` grades.
- **Setup checklists (e.g. pages 14, 21)** repeatedly state **every box must pass** ("If even one fails —
  no trade").

**Correct classification:** this is a **GENUINE UNRESOLVED INTERNAL INCONSISTENCY** between multiple,
non-reconciled **scoring** and **veto** frameworks:

1. The **graded partial-pass** rules (6/6 & 5/6 half-lot; 6/8 & 5/8 half-lot) explicitly permit taking a
   trade with one or more boxes **unticked** —
2. …which **directly contradicts** the **all-or-nothing veto** ("all boxes must be checked / if even one
   is missing — skip").
3. The **two stack counts differ** (a **6-box** /6 rule on p11 vs an **8-box** /8 count on p21, with
   different pass thresholds), and both coexist with a **separate letter-grade** system (p12).

**Instruction honoured:** the 6/8 framework is **present** and is recorded as such; v0.2.1 does **not** state
it is absent.

---

## CORRECTION 2 — Risk classification

**v0.2 said (mis-classified):** the difference between the documents' **1–2% / max-2% per-trade** risk
examples and the project's **locked 1.0% campaign-wide** cap was labelled a **`CONTRADICTED` / evidential
contradiction**.

**Corrected classification:** **`PROJECT_GOVERNANCE_OVERRIDE / POLICY_DIVERGENCE`.**

- The **source claim remains accurately recorded** — the documents do teach 1–2% per-trade / max-2% lot
  (Whale Room Guide p7/p10; Playbook p13). Nothing about the document evidence is disputed.
- This is **not** an evidential contradiction. The **project intentionally applies a stricter, independent
  risk policy** (1.0% **campaign-wide**). The two figures measure different things (per-trade teaching vs
  campaign-wide governance) and the project override is deliberate, not a factual conflict.

**No configuration changed:** `risk_policy.py` (v2.0.0, 1.0% cap) and all execution gates
(`EXECUTION_ENABLED`, `CTRADER_EXECUTION_ENABLED`, `ORDER_SENDING_ENABLED`, `ORDER_MANAGEMENT_ENABLED`)
remain exactly as they were (all False; cap 1.0%).

---

## Files changed by this correction
- **Added:** `specifications/FAROUK_METHODOLOGY_SPEC_v0.2.1.md`
- **Added:** `errata/FP-METHODOLOGY-v0.2-ERRATA-001.md` (this file)

## Files deliberately NOT modified
- `FAROUK_METHODOLOGY_SPEC_v0.2.md` and `FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md` (preserved as-is)
- `educational_claims.csv`, `comparisons/FP-OFFICIAL-DOCS-vs-CAMPAIGNS-001-002-003.json`, and all campaign
  dossiers/frozen comparisons — left unmodified; this errata + v0.2.1 are the authoritative correction of
  their affected classifications (per "do not modify frozen campaign evidence or prior frozen comparison
  files"). Readers should apply Corrections 1 & 2 above when consulting those prior records.

No detector code, QST campaign, permit, lease, broker action, or execution/risk-policy change occurred.
