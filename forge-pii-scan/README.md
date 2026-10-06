# forge-pii-scan

A Claude plugin that finds and masks the personal information in a document before you share it.

It adds two tools. `scan` reports what personal data a document contains and where,
without altering it. `redact` returns where to mask identifiers, and a script in
Claude's sandbox applies that to your Word, PowerPoint, Excel or PDF file so its
formatting survives. Neither stores anything, and neither needs an account or
credentials.

Email addresses, phone numbers, payment cards, SSNs, PANs and Aadhaar numbers are
matched exactly. Names and addresses are reported only where structure reveals them,
such as a table column headed Name, a signature block or a postcode, so a name written
in a sentence is missed. The plugin says so every time it reports, because a scan
people over-trust is worse than no scan.

Only the exactly matched identifiers are masked. Names and addresses are reported,
not masked.

The report carries the kind of each identifier and the line it sits on, never the value
itself. `redact` returns positions and tokens, never the value.

## Install

In Claude Code:

```
/plugin marketplace add peshwar9/forge-plugins
/plugin install forge-pii-scan
```

Or add the server directly, without the skill:

```
claude mcp add --transport http forge-pii-scan https://www.forgeprivate.com/api/mcp/public
```

## What happens to what you send

The endpoint reads the text, computes over it in memory and returns a result. Nothing
is written to a database, nothing is written to a log, and no part of the document
appears in an error message. The scan is a pure function.

## Who makes it

Built by [GradTensor](https://www.forgeprivate.com), who make Forge, a private
workspace for confidential work. The detection engine here is the one Forge uses
internally, exposed without an account.
