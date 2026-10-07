# forge-plugins

Plugins for Claude, from [GradTensor](https://www.forgeprivate.com).

## forge-pii-scan

Finds and masks the personal information in a document before you share it.

You are about to attach a contract to a support ticket, send an export to a
contractor, or publish a file as a sample. **What is actually in it?** Most people
answer that by skimming, and skimming is how a payroll column or a taxpayer ID ends
up somewhere it should not be.

This adds two tools. `scan` tells you what personal information is in a document
and where. `redact` masks it: you get back the same Word, PowerPoint, Excel or PDF
file, with its formatting intact and the identifiers replaced by tokens such as
`[EMAIL]`. Neither needs an account, and neither stores anything.

### Install

```
/plugin marketplace add peshwar9/forge-plugins
/plugin install forge-pii-scan
```

Or add just the server, without the skill that teaches Claude when to reach for it:

```
claude mcp add --transport http forge-pii-scan https://www.forgeprivate.com/api/mcp/public
```

### What it finds

**Matched exactly**: email addresses, phone numbers, payment card numbers (Luhn
checked), US Social Security numbers, Indian PANs and Aadhaar numbers, and IBANs
(checksum verified). Bank account numbers, IDs, names, ages and dates of birth are
matched when a label or a spreadsheet column header says what they are, such as "A/C No:",
"Patient ID:", "Policy No:", "Name:", "Age:" or "DOB:". Invoice, order and PO numbers are
left alone.

### What you can ask

Attach a file and ask in your own words, for example:

- *"I need to share this payroll file with our auditor. Mask the personal details first."*
- *"Mask the personal information in this deck, and the names too, except the CFO."*
- *"Redact the personal details in this invoice before I forward it."*

Claude masks the identifiers, lists the names and addresses it can see, asks which of
them to mask, and gives you back the same file with its formatting intact.

**Found through structure**: a table column headed Name and how many rows sit under
it, a signature or notices block, a postcode, a labelled address field, and email
addresses that embed somebody's name.

### What it misses, which matters more

**A name written in an ordinary sentence will not be found.** "I spoke to Priya
about the renewal" passes straight through. Names are matched by the shape of the
document, not by recognising them, so the tool finds the participant table and not
the person mentioned in clause 6.

The plugin says this every time it reports, deliberately. A scan people over-trust
is worse than no scan, because it converts "I should read this carefully" into "a
tool checked it."

### What it does with what you send

The endpoint reads the text, computes over it in memory, and returns the report.
Nothing is written to a database, nothing is written to a log, and no part of the
document appears in an error message.

**The report never contains the values it found.** It says there is an email address
on line 12, not what the address is. That is the point: a report you can paste into
a ticket without re-creating the problem you were checking for.

### How masking works

Masking never means Claude rewriting your document. A language model rewriting a
file for privacy produces something nobody can verify, and it can change words it
was not asked to touch.

Instead, a small script in Claude's sandbox pulls the text out of your file and
`redact` decides what to mask, using the same fixed rules as `scan`. The tool
returns only positions and tokens, never the values. The script then makes those
exact replacements inside the original file, which is why the formatting survives.
Each paragraph carries a fingerprint, so a position is never applied to text that
differs from what was checked, and the finished file is checked again before you
get it.

In a PDF, the text under each black box is deleted, not just covered. Links whose
address holds an identifier, such as a `mailto:` link, are removed.

**The tools mask only the exactly matched identifiers.** Names and addresses are
not something they can find reliably, so Claude reads the document, lists the
names and addresses it sees, and asks you which to mask. Only the ones you approve
are replaced, by exact match, in the same formatting-safe way. Because this step
depends on Claude's reading, look over the result for any name it missed.

Masking a file needs Claude to be able to run code. Supported: .docx, .pptx, .xlsx
and .pdf with a text layer. A scanned PDF has no text to find.

### Using it from another assistant

The tools are a standard MCP server at `https://www.forgeprivate.com/api/mcp/public`, so any
assistant that connects to MCP servers can call `scan` and `redact`. To mask a file in
place, the assistant also needs code execution: it can fetch the masking script with the
`get_masking_script` tool, or as the `forge-pii-scan://mask_file.py` resource, check the
SHA-256 that comes with it, and follow the usage in the tool's description. The skill in
this plugin is how Claude learns that workflow; another assistant has to be told it.

## Who makes these

[GradTensor](https://www.forgeprivate.com), who build Forge, a private workspace for
confidential work. The detection engine behind both tools is the one Forge uses on
its own ingestion, exposed without an account.

## Licence

MIT. See [LICENSE](./LICENSE).
