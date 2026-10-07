"""Mask personal identifiers in a Word, PowerPoint, Excel or PDF file, keeping its formatting.

Used with the `redact` tool from the forge-pii-scan server. The tool decides what to
mask; this file only finds the text in the document and applies the tool's answer.

    python mask_file.py extract IN            -> prints the segments (and labels) to send to `redact`
    python mask_file.py apply IN OUT RESULT   -> writes the masked copy, checks it, prints a report
    python mask_file.py replace IN OUT LIST   -> replaces strings the user approved

RESULT is a JSON file holding the tool's structured result: spans, checks and whole.

LIST is a JSON file of exact strings the user chose to mask, each with its token:
[{"text": "Kavitha Raman", "replacement": "[NAME]"}, ...]. Nothing detects them here:
the user approved each one, and every exact occurrence is replaced. These strings
are never sent anywhere.

Office files need lxml, which keeps the XML exactly as Office wrote it. PDF needs
PyMuPDF (`pip install pymupdf`).

Nothing here prints an identifier. Reports give segment numbers, kinds and counts only.
"""

import hashlib
import json
import re
import sys
import zipfile

from lxml import etree

# Which segments are sent to `redact`. Almost every identifier contains a digit or an
# @. The exception is a labelled name, which is letters after "Name:", so a segment
# is also sent when it, or the spreadsheet column it sits under, has a label word.
# Anything else cannot need masking and is not sent, which keeps the request small.
CANDIDATE = re.compile(r"[@\d]")
LABEL_WORDS = re.compile(r"\b(?:name|age|dob|d\.o\.b|birth)\b", re.I)

# Masked values shorter than this are not looked for in the output when it is
# checked, because an age such as "45" also occurs in "45 mg" and would be reported
# as left behind when it was not.
MIN_CHECKED = 6

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
TC = "http://schemas.microsoft.com/office/spreadsheetml/2018/threadedcomments"

# Comment formats that hold their text directly in one element, with no paragraph
# around it: Excel's threaded comments and PowerPoint's older comments. Each such
# element is its own paragraph.
SELF_CONTAINED = (f"{{{TC}}}text", f"{{{P}}}text")
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

# Per format: which parts hold text, and which element is a paragraph and which holds text.
FORMATS = {
    "docx": (re.compile(r"word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$"), f"{{{W}}}p", f"{{{W}}}t"),
    # Comments are where people write what they would not put in a cell or on a slide,
    # such as a personal email, so every comment format is included.
    "pptx": (re.compile(r"ppt/(slides/slide\d+|notesSlides/notesSlide\d+|comments/\w+)\.xml$"), f"{{{A}}}p", f"{{{A}}}t"),
    "xlsx": (re.compile(r"xl/(sharedStrings|worksheets/sheet\d+|comments\d*|comments/comment\d+|threadedComments/threadedComment\d+)\.xml$"), None, f"{{{S}}}t"),
}


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def kind_of(path):
    ext = path.rsplit(".", 1)[-1].lower()
    if ext not in FORMATS and ext != "pdf":
        sys.exit(f"Unsupported file type .{ext}. Supported: .docx, .pptx, .xlsx, .pdf")
    return ext


# ---------------------------------------------------------------- Office files

def _paragraphs(root, para_tag, text_tag):
    """Each paragraph as a list of its own text elements, in document order.

    A text box sits inside a paragraph and holds paragraphs of its own, so each text
    element belongs to its nearest paragraph only. Spreadsheets have no paragraph
    element: a shared string (si) or an inline string (is) plays that part.
    """
    owners = {}
    order = []
    for t in root.iter(text_tag, *SELF_CONTAINED):
        if t.tag in SELF_CONTAINED:
            node = t
            if node not in owners:
                owners[node] = []
                order.append(node)
            owners[node].append(t)
            continue
        node = t
        while node is not None:
            node = node.getparent()
            if node is None:
                break
            tag = node.tag
            # In a spreadsheet a shared string (si), an inline string (is) or a
            # comment's text plays the part of a paragraph.
            if (para_tag and tag == para_tag) or (para_tag is None and tag in (f"{{{S}}}si", f"{{{S}}}is", f"{{{S}}}text")):
                break
            if para_tag is None and tag in (f"{{{S}}}rPh",):  # phonetic hints are not cell text
                node = None
                break
        if node is None:
            continue
        if node not in owners:
            owners[node] = []
            order.append(node)
        owners[node].append(t)
    return [owners[p] for p in order]


def _cell_col_row(ref):
    m = re.match(r"([A-Z]+)(\d+)$", ref or "")
    return (m.group(1), int(m.group(2))) if m else (None, None)


def _sheet_labels(z):
    """Column headers, so a cell can be read beside the header that says what it is.

    A bank account is only masked when something labels it as one, and in a
    spreadsheet that something is the header in row 1. Returns the header for each
    value cell and inline string, keyed by sheet part and cell reference, and for
    each shared string the header of every cell that uses it, when they all agree.
    """
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = etree.fromstring(z.read("xl/sharedStrings.xml"))
        shared = ["".join(t.text or "" for t in si.iter(f"{{{S}}}t")) for si in root.iter(f"{{{S}}}si")]

    def text_of(c):
        if c.get("t") == "s":
            v = c.find(f"{{{S}}}v")
            try:
                return shared[int(v.text)]
            except (TypeError, ValueError, IndexError, AttributeError):
                return None
        if c.get("t") == "inlineStr":
            return "".join(t.text or "" for t in c.iter(f"{{{S}}}t"))
        return None

    by_cell, si_labels = {}, {}
    for name in z.namelist():
        if not re.search(r"xl/worksheets/sheet\d+\.xml$", name):
            continue
        root = etree.fromstring(z.read(name))
        headers = {}
        cells = list(root.iter(f"{{{S}}}c"))
        for c in cells:
            col, row = _cell_col_row(c.get("r"))
            if row == 1:
                headers[col] = (text_of(c) or "").strip() or None
        for c in cells:
            col, row = _cell_col_row(c.get("r"))
            if not row or row == 1:
                continue
            label = headers.get(col)
            by_cell[(name, c.get("r"))] = label
            if c.get("t") == "s":
                try:
                    si_labels.setdefault(int(c.find(f"{{{S}}}v").text), set()).add(label)
                except (TypeError, ValueError, AttributeError):
                    pass
    si_label = {i: next(iter(ls)) for i, ls in si_labels.items() if len(ls) == 1}
    return by_cell, si_label


def _office_segments(path, kind):
    parts_re, para_tag, text_tag = FORMATS[kind]
    segments = []  # (part, reference within the part, text, label)
    with zipfile.ZipFile(path) as z:
        by_cell, si_label = _sheet_labels(z) if kind == "xlsx" else ({}, {})
        for name in sorted(z.namelist()):
            if not parts_re.search(name):
                continue
            root = etree.fromstring(z.read(name))
            is_sheet = kind == "xlsx" and "/worksheets/" in name
            for i, ts in enumerate(_paragraphs(root, para_tag, text_tag)):
                label = None
                if kind == "xlsx" and name == "xl/sharedStrings.xml":
                    label = si_label.get(i)
                elif is_sheet:
                    container = ts[0].getparent()
                    while container is not None and container.tag != f"{{{S}}}c":
                        container = container.getparent()
                    label = by_cell.get((name, container.get("r"))) if container is not None else None
                segments.append((name, ("p", i), "".join(t.text or "" for t in ts), label))
            # A phone or ID number typed into a spreadsheet as a number is stored as a
            # cell value, not as text, and would otherwise be missed.
            for i, c in enumerate(_value_cells(root)):
                segments.append((name, ("v", i), c.find(f"{{{S}}}v").text or "", by_cell.get((name, c.get("r")))))
            # Link targets, such as mailto: addresses, are stored outside the text.
            rels = name.rsplit("/", 1)
            rels_name = f"{rels[0]}/_rels/{rels[1]}.rels"
            if rels_name in z.namelist():
                for rel in etree.fromstring(z.read(rels_name)):
                    if rel.get("TargetMode") == "External":
                        segments.append((rels_name, ("rel", rel.get("Id")), rel.get("Target") or "", None))
    return segments


def _value_cells(root):
    """Cells holding a number or a formula's text result, without a formula of their own."""
    return [
        c for c in root.iter(f"{{{S}}}c")
        if c.find(f"{{{S}}}v") is not None and c.find(f"{{{S}}}f") is None
        and c.get("t") in (None, "n", "str")
    ]


def _masked_text(text, edit):
    if edit["whole"] is not None:
        return edit["whole"]
    cps = list(text)
    for s in sorted(edit["spans"], key=lambda s: -s["start"]):
        cps[s["start"]:s["end"]] = [s["replacement"]]
    return "".join(cps)


def _apply_to_elements(ts, spans):
    """Apply code-point spans to a paragraph spread across several text elements."""
    texts = [list(t.text or "") for t in ts]
    owner = [(i, j) for i, chars in enumerate(texts) for j in range(len(chars))]
    for s in sorted(spans, key=lambda s: -s["start"]):
        covered = owner[s["start"]:s["end"]]
        if not covered:
            continue
        first_el, first_pos = covered[0]
        for el, pos in reversed(covered):
            texts[el][pos] = ""
        texts[first_el][first_pos] = s["replacement"]
    for t, chars in zip(ts, texts):
        t.text = "".join(chars)
        if t.text != t.text.strip():
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def _apply_office(src, dst, kind, segments, edits):
    parts_re, para_tag, text_tag = FORMATS[kind]
    report = {"masked_segments": 0, "skipped_segments": [], "links_removed": 0}
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            mine = {k: v for k, v in edits.items() if segments[k][0] == item.filename}
            if mine:
                root = etree.fromstring(data)
                if item.filename.endswith(".rels"):
                    drop = {segments[k][1][1] for k in mine}
                    for rel in list(root):
                        if rel.get("Id") in drop:
                            # A link whose target holds an identifier is pointed at
                            # nothing rather than masked, since a masked URL is broken anyway.
                            rel.set("Target", "#")
                            report["links_removed"] += 1
                else:
                    paras = _paragraphs(root, para_tag, text_tag)
                    cells = _value_cells(root) if kind == "xlsx" else []
                    for k, edit in mine.items():
                        ref_kind, ref = segments[k][1]
                        report["masked_segments"] += 1
                        if ref_kind == "v":
                            # The masked value is text now, so the cell becomes a string.
                            c = cells[ref]
                            masked = _masked_text(c.find(f"{{{S}}}v").text or "", edit)
                            c.remove(c.find(f"{{{S}}}v"))
                            c.set("t", "inlineStr")
                            etree.SubElement(etree.SubElement(c, f"{{{S}}}is"), f"{{{S}}}t").text = masked
                            continue
                        ts = paras[ref]
                        if edit["whole"] is not None:
                            ts[0].text = edit["whole"]
                            for t in ts[1:]:
                                t.text = ""
                        else:
                            _apply_to_elements(ts, edit["spans"])
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            zout.writestr(item, data)
    return report


# ---------------------------------------------------------------- PDF

def _pdf_segments(path):
    import fitz  # PyMuPDF
    segments = []
    with fitz.open(path) as doc:
        for page in doc:
            for i, line in enumerate(page.get_text("text").split("\n")):
                segments.append((page.number, i, line, None))
            for link in page.get_links():
                if link.get("uri"):
                    segments.append((page.number, "link", link["uri"], None))
    return segments


def _apply_pdf(src, dst, segments, edits):
    import fitz
    report = {"masked_segments": 0, "skipped_segments": [], "links_removed": 0, "not_found_on_page": []}
    with fitz.open(src) as doc:
        for k, edit in edits.items():
            page_no, idx, text, _label = segments[k]
            page = doc[page_no]
            if idx == "link":
                for link in page.get_links():
                    if link.get("uri") == text:
                        page.delete_link(link)
                        report["links_removed"] += 1
                continue
            cps = list(text)
            targets = [text] if edit["whole"] is not None else ["".join(cps[s["start"]:s["end"]]) for s in edit["spans"]]
            for value in targets:
                rects = page.search_for(value)
                if not rects:
                    report["not_found_on_page"].append(k)
                for r in rects:
                    page.add_redact_annot(r, fill=(0, 0, 0))
            report["masked_segments"] += 1
        for page in doc:
            # Removes the text under each box, not just covers it.
            page.apply_redactions()
        doc.save(dst, garbage=4, deflate=True)
    return report


# ---------------------------------------------------------------- shared

def _is_candidate(seg):
    text, label = seg[2], seg[3]
    return bool(CANDIDATE.search(text) or LABEL_WORDS.search(text) or (label and LABEL_WORDS.search(label)))


def _sent(segments):
    """The distinct candidate segments, in first-seen order, and where each one occurs.

    A report's header repeats on every page, and a spreadsheet repeats values down a
    column. Each distinct text, with its label, is sent once, and the answer is
    applied to every place it occurs. On a 48-page lab report that is 52 segments
    instead of 720, and the request is what the assistant has to write out, so it is
    most of the time a masking takes.
    """
    order, where = [], {}
    for k, seg in enumerate(segments):
        if not _is_candidate(seg):
            continue
        key = (seg[2], seg[3])
        if key not in where:
            where[key] = []
            order.append(key)
        where[key].append(k)
    return order, where


def _plan(segments, result):
    """Match the tool's answer to the segments, refusing any whose fingerprint differs."""
    order, where = _sent(segments)
    checks = {c["segment"]: c["sha256"] for c in result.get("checks", [])}
    edits = {}
    for c in result.get("spans", []):
        edits.setdefault(c["segment"], {"spans": [], "whole": None})["spans"].append(c)
    for w in result.get("whole", []):
        edits.setdefault(w["segment"], {"spans": [], "whole": None})["whole"] = w["masked"]
    plan = {}
    for sent_index, edit in edits.items():
        if sent_index >= len(order) or checks.get(sent_index) != fingerprint(order[sent_index][0]):
            _plan.skipped.append(sent_index)
            continue
        for k in where[order[sent_index]]:
            plan[k] = edit
    return plan


_plan.skipped = []


def _plan_replacements(segments, items):
    """Spans for every exact occurrence of each approved string, longest first.

    Longest first, so that "Kavitha Raman" is replaced whole before "Kavitha" is
    looked for, and an occurrence never overlaps one already taken. Link targets and
    spreadsheet number cells are left out: names are not stored there.
    """
    order = sorted(
        [n for n, i in enumerate(items) if i.get("text")], key=lambda n: -len(items[n]["text"])
    )
    counts = [0] * len(items)
    plan = {}
    for k, seg in enumerate(segments):
        ref = seg[1]
        if isinstance(ref, tuple) and ref[0] in ("rel", "v") or ref == "link":
            continue
        cps = list(seg[2])
        taken = [False] * len(cps)
        spans = []
        for n in order:
            item = items[n]
            needle = list(item["text"])
            for i in range(len(cps) - len(needle) + 1):
                if cps[i:i + len(needle)] == needle and not any(taken[i:i + len(needle)]):
                    spans.append({"start": i, "end": i + len(needle), "replacement": item["replacement"]})
                    for j in range(i, i + len(needle)):
                        taken[j] = True
                    counts[n] += 1
        if spans:
            plan[k] = {"spans": spans, "whole": None}
    return plan, [{"item": n, "replacement": items[n].get("replacement"), "count": counts[n]} for n in range(len(items))]


def _masked_values(segments, plan):
    """What each edit removed, for checking the output. Never printed."""
    values = []
    for k, edit in plan.items():
        text = segments[k][2]
        if edit["whole"] is not None:
            values.append(text)
            continue
        cps = list(text)
        values.extend("".join(cps[s["start"]:s["end"]]) for s in edit["spans"])
    return values


def _verify(dst, kind, values):
    """Look for every masked value in the finished file's text.

    This replaces sending the whole file to `redact` a second time: the script knows
    exactly what it removed, so it can look for it locally, and the assistant does
    not have to write the document out again.
    """
    out = _pdf_segments(dst) if kind == "pdf" else _office_segments(dst, kind)
    text = "\n".join(seg[2] for seg in out)
    checked = [v for v in set(values) if len(v) >= MIN_CHECKED]
    return {"checked": len(checked), "remaining": sum(1 for v in checked if v in text)}


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("extract", "apply", "replace"):
        sys.exit(__doc__)
    cmd, src = sys.argv[1], sys.argv[2]
    kind = kind_of(src)
    segments = _pdf_segments(src) if kind == "pdf" else _office_segments(src, kind)
    if cmd == "extract":
        # Labels go with the segments when there are any, so the call to `redact`
        # can pass both. Only spreadsheets have them.
        order, _ = _sent(segments)
        out = {"segments": [text for text, _label in order]}
        if any(label for _text, label in order):
            out["labels"] = [label for _text, label in order]
        print(json.dumps(out, ensure_ascii=False))
        return
    dst, data_path = sys.argv[3], sys.argv[4]
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    if cmd == "replace":
        edits, found = _plan_replacements(segments, data)
    else:
        edits, found = _plan(segments, data), None
    report = _apply_pdf(src, dst, segments, edits) if kind == "pdf" else _apply_office(src, dst, kind, segments, edits)
    report["skipped_segments"] = _plan.skipped
    if cmd == "replace":
        # Approved strings are checked whatever their length: the user chose each one.
        out = _pdf_segments(dst) if kind == "pdf" else _office_segments(dst, kind)
        text = "\n".join(seg[2] for seg in out)
        approved = [i.get("text") for i in data if i.get("text")]
        report["verified"] = {"checked": len(approved), "remaining": sum(1 for v in approved if v in text)}
    else:
        report["verified"] = _verify(dst, kind, _masked_values(segments, edits))
    # One answer to "is it done". A skipped segment was never masked, so it has no
    # value to look for and `remaining` alone would read as clean.
    report["complete"] = not report["skipped_segments"] and report["verified"]["remaining"] == 0
    if found is not None:
        # Counts per approved string, by its position in LIST, without echoing the
        # string. A count of 0 means that form does not occur exactly, which is
        # worth telling the user.
        report["replaced"] = found
    print(json.dumps(report))


if __name__ == "__main__":
    main()
