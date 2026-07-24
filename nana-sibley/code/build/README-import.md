# Build folder — how to use these files

Everything here is the **Phase 0/1** construction kit. Run in this order.

## 1. `setup_airtable.py` — build the ledger
- Create an empty Airtable base "Hearthside Ledger" + a PAT (`schema.bases:write`).
- `export AIRTABLE_PAT=...` and `export AIRTABLE_BASE_ID=app...`
- `python3 setup_airtable.py` → creates all tables, fields, links.
- Create the 4 views by hand (the script prints the list).

## 2. `n8n-w1-dream-intake.json` — import into n8n
- n8n → Workflows → Import from File.
- Then wire these (they're placeholders in the scaffold):
  - **Airtable credential** on the 3 Airtable nodes (replace `REPLACE_CRED_ID`).
  - **`YOUR_BASE_ID`** → your real base ID on every Airtable node.
  - **`ANTHROPIC_API_KEY`** as an n8n environment variable (or swap the two
    HTTP nodes for OpenAI — same shape).
  - Confirm the node **typeVersions** match your n8n version; bump if it warns.
- The full classifier prompt is condensed inline — for the complete spec see
  `prompts/w1-safety-classifier.md`.

## 3. `n8n-w2-script-generation.json` — import into n8n
- Same credential + base-ID + API-key wiring.
- **Paste the real module text** into the `Assemble Prompt` code node where it
  says `<<PASTE ...>>` (system-prompt, character-modules, format-modules,
  output-schema), OR store them in a `Prompts` table and fetch them.
- `Script Engine` and `Validate Script` nodes have **Retry On Fail = 3** — that
  is the retry loop from `w2-prompt-assembly.md`.

## 4. Re-run the two dry-run tests LIVE
- Feed the self-harm mock through W1 → confirm it lands in **Care Queue** with
  **no** Script created. (This is your real, honest screenshot moment.)
- Feed "The Rising Tide" through → confirm a Script row appears at
  **needs_review**, waiting for your approval.

## Honest caveats
- These are **scaffolds**, not plug-and-play. Node versions and the Airtable
  node's field-mapping shape vary by n8n release — expect small fixes on import.
- ⛔ Do **not** wire any paid render/voice/publish step yet. Prove W1 + W2 first.
- Never commit real API keys. Keep them in n8n credentials / env vars only.
