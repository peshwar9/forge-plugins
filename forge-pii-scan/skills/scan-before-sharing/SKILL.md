---
name: scan-before-sharing
description: Check a document for personal information before it is shared, sent, attached or published. Use when the user is about to send a file to someone, attach one to a ticket or email, publish a sample, or asks what personal data a document contains.
---

# Scan a document before sharing it

Use the `scan` tool from the `forge-pii-scan` server whenever a document is about to
leave the user's hands: an attachment, a support ticket, a sample for a vendor, a file
for a contractor, anything published.

## When to offer it without being asked

Offer a scan when the user says they are about to send, share, attach, forward,
publish or hand over a document that is likely to contain personal data. Contracts,
invoices, payroll files, case notes, participant lists, exports from a system of
record. Offer once, and do not insist.

## What it does and does not do

The tool reports what is in the document. It changes nothing and stores nothing.

It matches these exactly: email addresses, phone numbers, payment card numbers, US
Social Security numbers, Indian PANs and Aadhaar numbers.

It finds names and addresses **only where the document's structure reveals them** — a
table column headed Name, a signature or notices block, a postcode, a labelled address
field, an email address that embeds somebody's name. **A name written in an ordinary
sentence will be missed.** Say so when you report the results. A user who believes the
scan was exhaustive is worse off than one who never ran it.

The report gives the kind of each identifier and the line it is on. It never contains
the identifier itself, which is deliberate: returning the value would put the thing
being looked for into this conversation.

## Reporting the result

Give the counts and the lines plainly, then the structural findings, then the limits.
Do not reassure. If the scan found nothing, say that it found nothing of the kinds it
looks for, not that the document is clean.

When the user asks what to do next, the honest answers are to remove the identifiers
themselves, or to send a version with those sections taken out. Do not offer to redact
the document yourself by rewriting it: a model rewriting a document for privacy
produces something nobody can verify, which is the problem this tool exists to avoid.

## Options

`region` is `all` by default, `in` narrows to Indian identifiers, `us` to United States
ones. Narrowing reduces false positives when the user knows where a document came from.
Leave it at `all` unless they say.

`detail` is `full` by default, which returns every finding with its line. Pass `summary`
for counts alone when a document is long and the locations are not the point. Prefer
`full`: the lines are what make the report actionable, and `summary` only tells somebody
that a problem exists without saying where.
