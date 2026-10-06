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
checked), US Social Security numbers, Indian PANs and Aadhaar numbers.

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

**Only the exactly matched identifiers are masked.** Names and addresses are
reported, not masked, and a name in a sentence is neither found nor masked, so
Claude will point out the ones it can see for you to remove.

Masking a file needs Claude to be able to run code. Supported: .docx, .pptx, .xlsx
and .pdf with a text layer. A scanned PDF has no text to find.

## Who makes these

[GradTensor](https://www.forgeprivate.com), who build Forge, a private workspace for
confidential work. The detection engine behind both tools is the one Forge uses on
its own ingestion, exposed without an account.

## Licence

MIT. See [LICENSE](./LICENSE).
