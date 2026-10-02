# forge-plugins

Plugins for Claude, from [GradTensor](https://www.forgeprivate.com).

## forge-pii-scan

Checks a document for personal information before you share it.

You are about to attach a contract to a support ticket, send an export to a
contractor, or publish a file as a sample. **What is actually in it?** Most people
answer that by skimming, and skimming is how a payroll column or a taxpayer ID ends
up somewhere it should not be.

This adds one tool, `scan`. It reads the text and tells you what personal
information is in it and where. It changes nothing, it needs no account, and it
stores nothing.

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

### What it will not do

It will not produce a redacted copy by rewriting the document. A language model
rewriting a file for privacy produces something nobody can verify, which is the
problem this tool exists to avoid. If you need a redacted version, remove the
identifiers yourself, or remove the sections that hold them.

## Who makes these

[GradTensor](https://www.forgeprivate.com), who build Forge, a private workspace for
confidential work. The detection engine behind `scan` is the one Forge uses on its
own ingestion, exposed read-only and without an account.

## Licence

MIT. See [LICENSE](./LICENSE).
