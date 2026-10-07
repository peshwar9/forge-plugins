---
name: scan-before-sharing
description: Find and mask personal information in a document or pasted text: emails, phone numbers, payment cards, US SSNs, Indian PAN and Aadhaar numbers, IBANs, bank accounts, and the names and addresses the user approves. Masks Word, PowerPoint, Excel and PDF files in place, keeping their formatting. Use when the user attaches a file likely to hold data about people, such as a CV, contract, invoice, medical or lab report, payroll or HR file, bank statement, customer list, spreadsheet, ticket, log or transcript; asks whether it is safe to share, send, upload or publish, or wants it ready for a vendor, client or auditor; asks to redact, mask, anonymise, de-identify, scrub or hide personal data; mentions GDPR, DPDP or data protection; or asks Claude to email, attach or publish a document. Never returns the values.
---

# Find and mask personal information

Two tools from the `forge-pii-scan` server:

- `scan` reports what personal information a document contains and where. It changes
  nothing.
- `redact` works out where to mask identifiers, so the user gets back the same file
  with its formatting intact, or the same text, with identifiers replaced by tokens
  such as `[EMAIL]`.

Neither stores anything, and neither returns an identifier's value.

## When to offer it without being asked

Offer a scan when the user attaches a file likely to hold data about people, or says
they are about to send, share, attach, publish or hand over one. Contracts, invoices,
payroll files, CVs, case notes, participant lists, exports from a system of record.
Offer once, and do not insist. Offer to mask after a scan finds something.

## What the tools cover, and what they do not

Matched exactly, and masked by `redact`: email addresses, phone numbers, payment card
numbers, US Social Security numbers, Indian PANs and Aadhaar numbers, and IBANs.

Masked when a label introduces them, in the text or as a spreadsheet column header:
bank account numbers ("A/C No:", "Bank A/C"), IDs ("Patient ID:", "MRN:", "UHID:",
"Report ID:", "Sample ID:", "Policy No:", "Claim No:", "Employee ID:"), names
("Name:", "Patient Name:"), ages ("Age:") and dates of birth ("DOB:"). The label stays
and only the value is replaced. A bare number is left alone, because it could be an
order or invoice number, and invoice, order and PO numbers are never treated as IDs.

Other names and addresses are found by `scan` **only where the document's structure
reveals them**, and are not masked by the tools: such as a table column headed Name, a signature or notices block,
a postcode, a labelled address field, or an email address that embeds somebody's name.
**A name written in an ordinary sentence is neither found nor masked.**

So read the document yourself as well. When you report, give the tools' findings, then
the names and addresses you can see that they did not cover, and say which came from
where. The user can then choose which of those to mask, as described below. Say what was not masked every time. A user who believes a masked copy is clean
when it still names people is worse off than one who never used the tool.

## Reporting a scan

Give the counts and the lines plainly, then the structural findings, then the limits.
Do not reassure. If the scan found nothing, say it found nothing of the kinds it looks
for, not that the document is clean.

## Masking

**Never mask by rewriting the document yourself.** A model rewriting a document for
privacy produces something nobody can verify, and it can quietly change words it was
not asked to touch. Masking always goes through `redact`, which applies the same fixed
rules every time.

### Pasted text

Split the text into lines and call `redact` with those lines as `segments` and
`output: "text"`. Join the `masked` lines back with newlines and give the result to
the user as it came back, without editing it.

### A Word, PowerPoint, Excel or PDF file

This needs code execution. The masking script is `mask_file.py`, in the same folder
as this file. Copy it into your working directory. Office files need `lxml`; PDFs need
PyMuPDF (`pip install pymupdf` if it is missing).

1. Run `python mask_file.py extract FILE`. It prints a JSON object with `segments`, the
   text that could hold an identifier, and for spreadsheets `labels`, each cell's
   column header. Each distinct text appears once, even when it repeats on every page,
   so the list is usually much shorter than the document.
2. Call `redact` with `segments`, and `labels` when present, exactly as printed and in
   the same order. Copy them character for character. The labels are what let a bank
   account in a column headed "Bank A/C" be masked. Each masked segment comes back with a fingerprint,
   and the script refuses any segment whose text differs from the file's.
3. Save the tool's structured result (`spans`, `checks`, `whole`) as `result.json`,
   then run `python mask_file.py apply FILE OUTPUT result.json`. Name the output after
   the original, such as `contract-masked.docx`.
4. **Check the report.** `apply` checks the finished file itself, by looking for every
   value it masked, and prints `"complete": true` when nothing was skipped and nothing
   is left. Do not send the file to `redact` again to check it. If `complete` is false,
   usually because a segment was skipped when its fingerprint did not match, run steps
   1 to 3 again on the output file, which then holds only what is still to mask.
5. Give the user the masked file, and report: how many identifiers of each kind were
   masked, any links that were removed because their address held an identifier, and
   what was not masked, as described above.

### Names and addresses, when the user chooses them

The tools mask names only after a "Name:" label. Every other name and address, such as
one in a sentence, a table cell or a signature line without a label, you can mask, but
only the ones the user approves.

1. After masking, list the names and addresses you can see, with where each appears,
   and ask which to mask. Suggest keeping what the recipient may need, such as the
   signatory or a company's registered office. Mask nothing the user did not approve.
2. Write each approved item to `names.json` exactly as it appears in the document,
   with its token: `[{"text": "Kavitha Raman", "replacement": "[NAME]"}, ...]`. List
   every form a person is named by, such as "Kavitha Raman", "Kavitha" and
   "Ms Raman", because only exact matches are replaced. Use `[NAME]` for people and
   `[ADDRESS]` for addresses.
3. Run `python mask_file.py replace MASKED OUTPUT names.json` on the masked copy. Its
   report also says `complete`, after checking that no approved string is left.
4. The report gives a count for each item, by its position in the list. A count of 0
   means that form does not occur on its own, usually because a longer form already
   covered it. If a name you expected to replace shows 0, check how it is written in
   the document.
5. Tell the user what was replaced and how many times, and what you saw but they
   chose to keep. Say that this step depended on your reading, so they should look
   over the result for any name you missed.

These strings stay in your sandbox. Never send them to `redact` or `scan`.

For a PDF, the script deletes the text under each black box, not just covers it.
A scanned PDF holds pictures of text rather than text, so there is nothing to find:
say so rather than reporting that it is clean.

The document's own properties, such as its author, are not changed. Mention them if
the user is anonymising a file.

For a medical, legal or HR document, say that the substance stays: the diagnosis, the
test results, the case or the salary. Masking the identifiers makes the document harder
to link to a person; it does not make it anonymous. Age, gender and dates together can
still narrow down who someone is.

Other formats, such as .doc, .odt or images, are not supported. Say so, and offer to
mask the text instead.

If you cannot run code or cannot read `mask_file.py`, say that masking a file in place
is not available here, and offer the pasted-text route for the parts that matter.

## Options

`region` is `all` by default, `in` narrows to Indian identifiers, `us` to United States
ones. It applies to both tools. Narrowing reduces false positives when the user knows
where a document came from. Leave it at `all` unless they say.

For `scan`, `detail` is `full` by default, which returns every finding with its line.
Pass `summary` for counts alone when a document is long and the locations are not the
point. Prefer `full`: the lines are what make the report actionable.
