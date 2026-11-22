#!/usr/bin/env python3
"""Configure this repository as the manuscript of one RSNA journal and article type.

    python scripts/configure.py --list
    python scripts/configure.py --journal "Radiology: Artificial Intelligence" \\
        --type "Original Research" --title "My title" --description "One line about it"

It writes, from the parts under templates/ and the facts in journals/requirements.json:

    main.tex         the manuscript: abbreviated title page, abstract, body, statements
    title_page.tex   the full title page: authors, funding, disclosures, data sharing
    README.md        the README of the manuscript repository, with the title and description
    manuscript.json  what was chosen, and the fingerprints of the three files above

Every limit and every required section comes from journals/requirements.json. None is
written in this script or in a template. Where the data has no answer, the skeleton says
"check the journal's page" and prints no number.

The journal, the article type, the title and the description may also come from the
environment (RSNA_JOURNAL, RSNA_TYPE, RSNA_TITLE, RSNA_DESCRIPTION): that is how the
GitHub workflow hands them over, so that nothing a person typed reaches a command line.

A file the author has edited since it was written is never written over: the run stops
and names it. --force writes over it.

Python standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_FILE = REPO / "journals" / "requirements.json"
TEMPLATES = REPO / "templates"

STATE_FILE = "manuscript.json"
OUTPUTS = ("main.tex", "title_page.tex", "README.md")

DEFAULT_JOURNAL = "Radiology: Artificial Intelligence"
DEFAULT_TYPE = "Original Research"
DEFAULT_TITLE = "Manuscript title"

# The template's own README carries this mark; the README of a manuscript does not.
TEMPLATE_README_MARK = "rsna-template: the template's own README"
NOT_READ = "not read; check the journal's page"
PLACEHOLDER = re.compile(r"<<([a-z_]+)>>")
NOTE_TAG = re.compile(r"^%\[([a-z0-9,-]+)\] ?")
WIDTH = 100
RULE = "% " + "=" * 76
THIN = "% " + "-" * 76

# The four headings of a research article. The writing notes kept from the template this
# one descends from were written for them, so they go with these headings and no others.
RESEARCH_HEADINGS = ["Introduction", "Materials and Methods", "Results", "Discussion"]
SECTION_LABELS = {
    "Introduction": "sec:intro",
    "Materials and Methods": "sec:methods",
    "Results": "sec:results",
    "Discussion": "sec:discussion",
}
ABBREVIATION_SAMPLE = "We will talk about \\acrfull{MRI} or \\acrshort{MRI}."

# What each fact of an article type is called in the skeleton and in the README.
TYPE_FIELDS = (
    ("invited_only", "By invitation"),
    ("body_word_limit", "Body words"),
    ("body_words_count", "What the body count covers"),
    ("section_word_limits", "Words by section"),
    ("abstract_kind", "Abstract"),
    ("abstract_word_limit", "Abstract words"),
    ("abstract_headings", "Abstract headings"),
    ("summary_statement", "Summary statement"),
    ("key_points_label", "Key points box"),
    ("key_points_max", "Key points, how many"),
    ("key_points_word_limit", "Key points, words"),
    ("body_headings", "Body headings"),
    ("references_limit", "References"),
    ("figures_limit", "Figures"),
    ("tables_limit", "Tables"),
    ("reporting_checklist", "Reporting checklist"),
    ("other", "Also"),
)
# Facts of the journal that hold for every article type. Keys not named here are printed
# under their own name, so a fact added to the data shows up without a change here.
JOURNAL_LABELS = {
    "title_word_limit": "Title words",
    "abbreviations": "Abbreviations",
    "title_page_split": "Title pages",
    "anonymisation": "Anonymisation",
    "manuscript_file_order": "Order of the manuscript file",
    "separate_files": "Separate files",
    "file_type": "File type",
    "font": "Font",
    "spacing": "Spacing",
    "page_numbers": "Page numbers",
    "line_numbers": "Line numbers",
    "authorship": "Authors",
    "peer_review": "Peer review",
    "references_style": "Reference style",
    "tables_and_figures": "Tables and figures",
    "preprints": "Preprints",
    "manuscript_source": "Where manuscripts come from",
}
JOURNAL_SKIP = ("manuscript_types_listed", "manuscript_types_printed_2025_2026", "whats_new", "statements")
STATEMENT_LABELS = {
    "funding": "Funding",
    "disclosures": "Disclosures",
    "data_sharing": "Data sharing",
    "code_availability": "Code availability",
    "generative_ai": "Use of AI tools in writing",
    "reporting_checklists": "Reporting checklists",
    "trial_registration": "Trial registration",
    "ethics_approval": "Ethics approval",
    "author_contributions": "Author contributions",
}
INNER_WORDS = {
    "max_words": "words at most",
    "max_characters": "characters at most",
    "max": "at most",
}


class Refused(Exception):
    """The request cannot be met; the message says why and what would work."""


# ---------------------------------------------------------------------------- files


def read(path):
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def fingerprint(text):
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def load_data(path=None):
    with open(path or DATA_FILE, encoding="utf-8") as handle:
        return json.load(handle)


def load_state(root):
    path = Path(root) / STATE_FILE
    if not path.exists():
        return None
    return json.loads(read(path))


# ---------------------------------------------------------------------------- choices


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def pairs(data):
    """Every (journal, article type) of the data, in its order."""
    return [(journal, atype) for journal in data["journals"] for atype in journal["article_types"]]


def journal_names(data):
    return [journal["name"] for journal in data["journals"]]


def type_names(data):
    """Every name an article type has in any journal, once, in the order of the data."""
    names = []
    for _, atype in pairs(data):
        if atype["name"] not in names:
            names.append(atype["name"])
    return names


def list_choices(data):
    lines = []
    for journal in data["journals"]:
        lines.append(journal["name"])
        lines.extend("    " + atype["name"] for atype in journal["article_types"])
    return "\n".join(lines)


def find_journal(data, name):
    wanted = _norm(name)
    for journal in data["journals"]:
        if wanted and wanted in (_norm(journal["name"]), _norm(journal["key"])):
            return journal
    raise Refused(
        'Unknown journal "%s". The journals are:\n%s'
        % (clean_line(name), "\n".join("    " + other for other in journal_names(data)))
    )


def find_type(data, journal, name):
    wanted = _norm(name)
    types = journal["article_types"]
    for atype in types:
        if wanted and wanted in (_norm(atype["name"]), _norm(atype["key"])):
            return atype
    # The name another RSNA journal gives the same kind of article ("Review articles" for
    # "Review"): the drop-down of the workflow lists every journal's names together.
    same_kind = set(
        other["key"] for _, other in pairs(data) if wanted and _norm(other["name"]) == wanted
    )
    matches = [atype for atype in types if atype["key"] in same_kind]
    if len(matches) == 1:
        return matches[0]
    raise Refused(
        '%s has no article type "%s". It has:\n%s'
        % (journal["name"], clean_line(name), "\n".join("    " + atype["name"] for atype in types))
    )


# ---------------------------------------------------------------------------- words


def words(value):
    """A value of the data in plain words; None where the data has no answer."""
    if value is None:
        return None
    if value is True:
        return "yes"
    if value is False:
        return "no"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        items = [text for text in (words(item) for item in value) if text]
        if not items:
            return "none"
        short = all(len(item) <= 40 and "," not in item and ";" not in item for item in items)
        return (", " if short else "; ").join(items)
    if isinstance(value, dict):
        items = []
        for key, inner in value.items():
            text = words(inner)
            if text is None:
                continue
            if isinstance(inner, list) and len(inner) > 1:
                text = "(" + text + ")"
            items.append("%s: %s" % (INNER_WORDS.get(key, key.replace("_", " ")), text))
        return "; ".join(items) or None
    return str(value)


def said(fact):
    """A fact of the data as one phrase with its grade, or the words for 'no answer'."""
    text = words(fact.get("value")) if isinstance(fact, dict) else None
    if text is None:
        return NOT_READ
    if fact.get("grade"):
        return "%s [%s]" % (text, fact["grade"])
    return text


def comment(text, first="% ", rest=None):
    """A LaTeX comment, wrapped; addresses and long words are never broken."""
    lines = textwrap.wrap(
        " ".join(str(text).split()),
        width=WIDTH,
        initial_indent=first,
        subsequent_indent=first if rest is None else rest,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return "\n".join(lines) if lines else first.rstrip()


def tex(text):
    """Plain text made safe as LaTeX text: what a person typed is never run as LaTeX."""
    table = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
    }
    return "".join(table.get(char, char) for char in " ".join(str(text).split()))


def markdown(text):
    """Plain text made safe as one line of Markdown."""
    text = " ".join(str(text).split())
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*_\[\]|#])", r"\\\1", text)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def fill(template, values):
    def replace(match):
        if match.group(1) not in values:
            raise KeyError("the template asks for <<%s>>, which nothing fills" % match.group(1))
        return values[match.group(1)]

    return PLACEHOLDER.sub(replace, template)


def part(name):
    return read(TEMPLATES / "parts" / (name + ".tex")).rstrip("\n").split("\n")


def note(name, journal_key):
    """The writing note kept for a heading, if there is one.

    A line that starts with %[key] is kept for the journal of that key alone.
    """
    path = TEMPLATES / "notes" / (name + ".tex")
    if not path.exists():
        return []
    lines = []
    for line in read(path).rstrip("\n").split("\n"):
        tag = NOTE_TAG.match(line)
        if tag:
            if journal_key not in tag.group(1).split(","):
                continue
            line = ("% " + line[tag.end():]).rstrip()
        lines.append(line)
    return lines


def how_many(most, default=3):
    """How many empty points to lay out: the number read, or its first number."""
    if isinstance(most, int) and not isinstance(most, bool) and most > 0:
        return min(most, 9)
    if isinstance(most, str):
        found = re.search(r"\d+", most)
        if found and int(found.group()) > 0:
            return min(int(found.group()), 9)
    return default


def allowed(fact):
    """False only where the data says none at all (a limit of 0)."""
    value = fact.get("value")
    return not (isinstance(value, int) and not isinstance(value, bool) and value == 0)


# ---------------------------------------------------------------------------- main.tex


def header(data, journal, atype):
    level = journal["journal_level"]
    lines = [
        RULE,
        comment("%s: %s" % (journal["name"], atype["name"])),
        "% Written by scripts/configure.py from journals/requirements.json.",
        "%",
        comment(
            "A community template: not made or endorsed by the RSNA. The lines below are what was "
            "read on %s, in plain words. They are not the journal's own words, and nobody has "
            "compared them with the live page. Check the journal's instructions before you submit:"
            % data["meta"]["made_on"]
        ),
        "%   " + journal["instructions_url"],
        "%",
        "% How sure each line is, in [brackets]:",
    ]
    for letter, meaning in data["grades"].items():
        lines.append(comment("%s: %s" % (letter, meaning), first="%   ", rest="%      "))
    lines += [
        "%",
        "% A number is an upper limit unless its line says otherwise.",
        "%",
        "% This article type:",
    ]
    for field, label in TYPE_FIELDS:
        lines.append(comment("%s: %s" % (label, said(atype[field])), first="%   ", rest="%       "))
    lines += ["%", "% This journal, every article type:"]
    for field, fact in level.items():
        if field in JOURNAL_SKIP:
            continue
        label = JOURNAL_LABELS.get(field, field.replace("_", " ").capitalize())
        lines.append(comment("%s: %s" % (label, said(fact)), first="%   ", rest="%       "))
    lines += ["%", "% Statements, for every article type of this journal:"]
    for field, fact in level["statements"].items():
        label = STATEMENT_LABELS.get(field, field.replace("_", " ").capitalize())
        lines.append(comment("%s: %s" % (label, said(fact)), first="%   ", rest="%       "))
    lines += [
        "%",
        comment(
            "The writing notes under the four headings of a research article are kept from the "
            "template this one descends from. They were written for Radiology; the limits in them "
            "were replaced by the lines read for this journal."
        ),
        RULE,
    ]
    return lines


def abbreviated_title_page(journal, atype, research):
    key = journal["key"]
    level = journal["journal_level"]
    split = level["title_page_split"]
    page = (split.get("value") or {}).get("abbreviated_title_page")
    asked = "%s [%s]" % (page, split["grade"]) if page and split.get("grade") else (page or NOT_READ)
    lines = [
        THIN,
        "% The first page of the manuscript file: the abbreviated title page.",
        comment("What goes on it: " + asked),
        THIN,
        "",
        "\\textbf{Article type}: " + tex(atype["name"]),
        "",
    ]
    if page and "keyword" in page.lower():
        lines += [
            "% Keywords: named among the items of this page (see the line above).",
            "\\textbf{Keywords}: TODO",
            "",
        ]

    # the summary statement
    fact = atype["summary_statement"]
    statement = fact.get("value")
    lines.append(comment("Summary statement: " + said(fact)))
    if statement is None:
        lines += [
            "% If the journal's page asks for one, uncomment the next line.",
            "%\\textbf{Summary statement: TODO}",
        ]
    elif statement.get("required") is not False:
        if research:
            lines += note("summary-statement", key)
        lines.append("\\textbf{Summary statement: TODO}")
    lines.append("")

    # the key points, under the name the journal gives the box
    label = atype["key_points_label"].get("value")
    most = atype["key_points_max"].get("value")
    lines.append(comment("Key points box: " + said(atype["key_points_label"])))
    lines.append(comment("Key points, how many: " + said(atype["key_points_max"])))
    lines.append(comment("Key points, words: " + said(atype["key_points_word_limit"])))
    none = (isinstance(label, str) and label.lower().startswith("none")) or not allowed(atype["key_points_max"])
    if not none:
        box = ["\\textbf{%s}:" % tex(label or "Key points"), "\\begin{itemize}"]
        box += ["    \\item TODO"] * how_many(most)
        box.append("\\end{itemize}")
        if label is None:
            lines.append("% If the journal's page asks for them, uncomment the next lines.")
            lines += ["%" + line for line in box]
        else:
            if research and label in ("Key Points", "Key Results"):
                lines += note("key-points", key)
            lines += box
    lines.append("")

    # the list of abbreviations
    lines.append(comment("Abbreviations: " + said(level["abbreviations"])))
    lines += note("abbreviations", key)
    lines += part("abbreviations")
    return lines


def abstract(journal, atype, state):
    key = journal["key"]
    kind = atype["abstract_kind"].get("value")
    headings = atype["abstract_headings"].get("value")
    facts = [
        comment("Abstract: " + said(atype["abstract_kind"])),
        comment("Abstract words: " + said(atype["abstract_word_limit"])),
        comment("Abstract headings: " + said(atype["abstract_headings"])),
    ]
    if kind is None:
        return facts + [
            "% If the journal's page asks for an abstract, uncomment the next lines.",
            "%\\clearpage",
            "%\\section*{Abstract}",
            "%TODO",
        ]
    if kind == "none":
        return facts
    lines = ["\\clearpage"] + facts + ["", "\\section*{Abstract}", ""]
    state["abbreviation_used"] = True
    if kind == "structured" and headings:
        for index, heading in enumerate(headings):
            lines += note("abstract-" + slug(heading), key)
            text = "\\blindtext"
            if index == 0:
                text = ABBREVIATION_SAMPLE + " " + text
            lines += ["%s: %s" % (tex(heading), text), ""]
        lines.pop()
    else:
        lines.append(ABBREVIATION_SAMPLE + " \\blindtext")
    return lines


def body(journal, atype, research, state):
    key = journal["key"]
    headings = atype["body_headings"].get("value")
    counted = atype["body_words_count"].get("value")
    section_limits = atype["section_word_limits"]
    by_section = section_limits.get("value") or {}
    whole = "The body as a whole: body words: %s; what the count covers: %s." % (
        said(atype["body_word_limit"]),
        said(atype["body_words_count"]),
    )

    # what the body is made of: headings the data names, one run of text, or headings of
    # the author's choosing between the two ends the word count names
    if headings:
        blocks = [("section", heading) for heading in headings]
    elif headings == []:
        blocks = [("text", None)]
    else:
        ends = re.match(r"^(Introduction) to (Discussion|Conclusion)$", counted or "")
        if ends:
            blocks = [("section", ends.group(1)), ("own", None), ("section", ends.group(2))]
        else:
            blocks = [("own", None)]

    names = [name for _, name in blocks]
    figure_at = names.index("Materials and Methods") if "Materials and Methods" in names else 0
    cite_at = names.index("Results") if "Results" in names else len(blocks) - 1
    with_figure = allowed(atype["figures_limit"])
    with_table = allowed(atype["tables_limit"])
    with_references = allowed(atype["references_limit"])

    lines = [
        "\\clearpage",
        THIN,
        comment("The body. Body words: " + said(atype["body_word_limit"])),
        comment("What the body count covers: " + said(atype["body_words_count"])),
        comment("Body headings: " + said(atype["body_headings"])),
        comment("References: " + said(atype["references_limit"])),
        comment("Figures: " + said(atype["figures_limit"])),
        comment("Tables: " + said(atype["tables_limit"])),
        THIN,
    ]
    for index, (kind, name) in enumerate(blocks):
        lines.append("")
        if kind == "section":
            lines.append("\\section*{%s}" % tex(name))
            lines.append("\\label{%s}" % SECTION_LABELS.get(name, "sec:" + slug(name)))
            if name in by_section:
                grade = " [%s]" % section_limits["grade"] if section_limits.get("grade") else ""
                lines.append(comment("Words in this section: %s%s" % (by_section[name], grade)))
            else:
                lines.append(comment("No limit was read for this section alone. " + whole))
            if research:
                lines += note(slug(name), key)
        elif kind == "own":
            lines.append(
                comment(
                    "The headings of this part are yours: none were read for this article type. "
                    "Check the journal's page."
                )
            )
            lines.append("\\section*{Section heading}")
        else:
            lines.append(comment("No headings in the body of this article type. " + whole))
        text = "\\blindtext"
        if not state.get("abbreviation_used"):
            text = ABBREVIATION_SAMPLE + " " + text
            state["abbreviation_used"] = True
        lines.append(text)
        if index == figure_at and with_figure:
            lines += [""] + part("figure") + ["", "\\blindtext"]
        if index == cite_at:
            if with_references:
                lines += [""] + part("citations")
            if with_table:
                lines += [""] + part("table")
    return lines


def acknowledgments_place(journal):
    """Where the acknowledgments go, from the order of the manuscript file as read."""
    level = journal["journal_level"]
    order = [str(item).lower() for item in (level["manuscript_file_order"].get("value") or [])]
    separate = [str(item).lower() for item in (level["separate_files"].get("value") or [])]

    def position(word):
        return next((index for index, item in enumerate(order) if word in item), None)

    acknowledgments, references = position("acknowledg"), position("reference")
    if acknowledgments is not None:
        if references is not None and acknowledgments > references:
            return "after the references"
        return "before the references"
    if any("acknowledg" in item for item in separate):
        return "a separate file"
    return None


def back(journal, atype):
    level = journal["journal_level"]
    statements = level["statements"]
    lines = [
        THIN,
        "% Statements. Funding, disclosures and the data sharing statement are on the full title",
        "% page (title_page.tex), which is not anonymized. The two below belong to the manuscript:",
        "% delete the one that does not apply.",
        THIN,
        "",
        comment("Use of AI tools in writing: " + said(statements["generative_ai"])),
        "\\textbf{Use of AI tools in writing}: TODO (the tool, its version and maker, and what it was used for)",
        "",
        comment("Code availability: " + said(statements["code_availability"])),
        "\\textbf{Code availability}: TODO (where the code is kept, with a link)",
        "",
    ]
    checklist = atype["reporting_checklist"]
    if checklist.get("value") is None:
        checklist = statements["reporting_checklists"]
    lines += [
        comment("Reporting checklist: " + said(checklist)),
        "% The completed checklist is a file of its own: it is not part of this manuscript.",
        "",
    ]

    place = acknowledgments_place(journal)
    order = level["manuscript_file_order"]
    grade = " [%s]" % order["grade"] if order.get("grade") else ""
    section = ["\\section*{Acknowledgments}", "TODO"]
    if place == "a separate file":
        grade = " [%s]" % level["separate_files"]["grade"] if level["separate_files"].get("grade") else ""
        acknowledgments = [comment("Acknowledgments: a separate file for this journal, not part of this one%s." % grade)]
    elif place is None:
        acknowledgments = [
            comment("Acknowledgments: where they go was " + NOT_READ + "."),
            "% If they belong in this file, uncomment the next lines.",
        ] + ["%" + line for line in section]
    else:
        acknowledgments = [
            comment("Acknowledgments: in this file, %s, anonymized%s." % (place, grade))
        ] + section

    references = part("references") if allowed(atype["references_limit"]) else [
        comment("References: " + said(atype["references_limit"]))
    ]
    if place == "after the references":
        lines += references + [""] + acknowledgments
    else:
        lines += acknowledgments + [""] + references
    if allowed(atype["figures_limit"]):
        lines += [""] + part("figure-legends")
    return lines


def render_main(data, journal, atype, title):
    research = atype["body_headings"].get("value") == RESEARCH_HEADINGS
    state = {}
    title_note = [comment("Title words: " + said(journal["journal_level"]["title_word_limit"]))]
    if research:
        title_note += note("title", journal["key"])
    values = {
        "header": "\n".join(header(data, journal, atype)),
        "title_note": "\n".join(title_note),
        "title": tex(title),
        "abbreviated_title_page": "\n".join(abbreviated_title_page(journal, atype, research)),
        "abstract": "\n".join(abstract(journal, atype, state)),
        "body": "\n".join(body(journal, atype, research, state)),
        "back": "\n".join(back(journal, atype)),
    }
    return fill(read(TEMPLATES / "main.tex.in"), values)


# ---------------------------------------------------------------------------- title_page.tex


def render_title_page(data, journal, atype, title):
    level = journal["journal_level"]
    statements = level["statements"]
    split = level["title_page_split"]
    page = (split.get("value") or {}).get("full_title_page")
    asked = "%s [%s]" % (page, split["grade"]) if page and split.get("grade") else (page or NOT_READ)
    head = [
        RULE,
        comment("Full title page. %s: %s" % (journal["name"], atype["name"])),
        "% A file of its own, apart from the manuscript (main.tex), and NOT anonymized.",
        "% Written by scripts/configure.py from journals/requirements.json.",
        "%",
        comment(
            "A community template: not made or endorsed by the RSNA. The lines below are what was "
            "read on %s, in plain words. Check the journal's instructions before you submit:"
            % data["meta"]["made_on"]
        ),
        "%   " + journal["instructions_url"],
        "%",
        comment("What goes on this page: " + asked),
        "% The letters in [brackets] say how sure a line is: see the top of main.tex.",
        RULE,
    ]
    # Disclosures: laid out on this page unless what was read names another place for them
    # (the cover letter). There the line stays as a comment, for the author to uncomment.
    disclosures = [comment("Disclosures: " + said(statements["disclosures"]))]
    line = "\\textbf{Disclosures}: TODO"
    if "cover letter" in (words(statements["disclosures"].get("value")) or "").lower():
        disclosures += [
            "% As read, they go in the cover letter. If the journal's page asks for them on this page",
            "% as well, uncomment the next line.",
            "%" + line,
        ]
    else:
        disclosures += [
            "% If the journal wants them somewhere else (the cover letter, a form of its own), delete the next line.",
            line,
        ]
    # Data sharing: the journal's own line, then the line read for all RSNA journals where
    # it says something else (for Radiology the two are one and the same fact).
    sharing = [comment("Data sharing: " + said(statements["data_sharing"]))]
    wide = data.get("rsna_wide", {}).get("data_sharing_statement")
    if wide and "pubs.rsna.org" in journal["instructions_url"]:
        if wide.get("value") != statements["data_sharing"].get("value"):
            sharing.append(comment("RSNA journals: " + said(wide)))
        if wide.get("official_page"):
            sharing.append("% The sentences to choose from are on this page: " + wide["official_page"])
    values = {
        "header": "\n".join(head),
        "title_note": comment("Title words: " + said(level["title_word_limit"])),
        "title": tex(title),
        "article_type": tex(atype["name"]),
        "word_count_note": comment(
            "The word count of the text. Body words: %s; what the count covers: %s"
            % (said(atype["body_word_limit"]), said(atype["body_words_count"]))
        ),
        "funding_note": comment("Funding: " + said(statements["funding"])),
        "disclosures": "\n".join(disclosures),
        "data_sharing_note": "\n".join(sharing),
    }
    return fill(read(TEMPLATES / "title_page.tex.in"), values)


# ---------------------------------------------------------------------------- README.md


def limit_rows(journal, atype):
    """(what, as read, how sure) for every fact the README of a manuscript shows."""
    level = journal["journal_level"]
    rows = [("Title words", level["title_word_limit"])]
    rows += [(label, atype[field]) for field, label in TYPE_FIELDS]
    rows.append(("Abbreviations", level["abbreviations"]))
    return [
        (label, words(fact.get("value")) or NOT_READ, fact.get("grade") or "")
        for label, fact in rows
    ]


def render_readme(data, journal, atype, title, description):
    cell = lambda text: markdown(text).replace("\n", " ")
    rows = ["| %s | %s | %s |" % (cell(a), cell(b), cell(c)) for a, b, c in limit_rows(journal, atype)]
    grades = ["- **%s**: %s" % (letter, markdown(meaning)) for letter, meaning in data["grades"].items()]
    values = {
        "title": markdown(title),
        "description": markdown(description) if description else "*(Add a short description of the manuscript here.)*",
        "journal": journal["name"],
        "article_type": atype["name"],
        "read_date": data["meta"]["made_on"],
        "instructions_url": journal["instructions_url"],
        "limits_rows": "\n".join(rows),
        "grades_list": "\n".join(grades),
    }
    return fill(read(TEMPLATES / "README.md.in"), values)


# ---------------------------------------------------------------------------- configure


def clean_line(text):
    return " ".join(str(text or "").split())


def render(data, journal, atype, title=None, description=None):
    """The three files of a manuscript, as {name: text}."""
    title = clean_line(title) or DEFAULT_TITLE
    description = clean_line(description)
    files = {
        "main.tex": render_main(data, journal, atype, title),
        "title_page.tex": render_title_page(data, journal, atype, title),
        "README.md": render_readme(data, journal, atype, title, description),
    }
    for name, text in files.items():
        if not text.endswith("\n"):
            files[name] = text + "\n"
    return files


def render_default(data):
    journal = find_journal(data, DEFAULT_JOURNAL)
    return render(data, journal, find_type(data, journal, DEFAULT_TYPE))


def edited(root, files, state, data):
    """The files an author has changed since they were written: these are not written over."""
    recorded = (state or {}).get("files", {})
    defaults = None
    names = []
    for name in OUTPUTS:
        path = Path(root) / name
        if not path.exists():
            continue
        present = read(path)
        if present == files[name] or recorded.get(name) == fingerprint(present):
            continue
        if state is None:
            # never configured: the files are the template's own
            if name == "README.md":
                if TEMPLATE_README_MARK in present:
                    continue
            else:
                defaults = defaults or render_default(data)
                if present == defaults[name]:
                    continue
        names.append(name)
    return names


def configure(data, root, journal_name, type_name, title=None, description=None, force=False, dry_run=False):
    """Write the manuscript files into root. Returns the state that was written.

    dry_run: every check, nothing written (the issue form checks a choice this way first).
    """
    root = Path(root)
    journal = find_journal(data, journal_name)
    atype = find_type(data, journal, type_name)
    title = clean_line(title) or DEFAULT_TITLE
    description = clean_line(description)
    files = render(data, journal, atype, title, description)
    if not force:
        changed = edited(root, files, load_state(root), data)
        if changed:
            raise Refused(
                "%s changed since the template or this script wrote %s, so nothing was written.\n"
                "To write a fresh skeleton over %s, run this on a laptop with --force "
                "(the present text stays in the git history):\n"
                '    python scripts/configure.py --journal "%s" --type "%s" --title "..." --force'
                % (
                    " and ".join(changed),
                    "it" if len(changed) == 1 else "them",
                    "it" if len(changed) == 1 else "them",
                    journal["name"],
                    atype["name"],
                )
            )
    state = {
        "journal": journal["name"],
        "journal_key": journal["key"],
        "article_type": atype["name"],
        "article_type_key": atype["key"],
        "title": title,
        "description": description,
        "instructions": journal["instructions_url"],
        "requirements_read_on": data["meta"]["made_on"],
        "files": {name: fingerprint(files[name]) for name in OUTPUTS},
    }
    if dry_run:
        return state
    for name in OUTPUTS:
        write(root / name, files[name])
    write(root / STATE_FILE, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    return state


def matrix(data, root, repository=None, template=None, is_template=False):
    """What the build compiles, and which of three states the repository is in.

    "manuscript"  configured (manuscript.json is there): the manuscript alone.
    "copy"        a copy of the template that nobody has configured yet: main.tex and
                  title_page.tex as they came, in one job. Without this state the first
                  commit of every new copy would compile all the journals, which is the
                  template's own check and none of the copy's business.
    "template"    the template itself (it has the template's name, or its template switch is
                  on), and any place where the name of the repository is not known (a
                  laptop): every journal and article type.

    repository is the name the build runs in (GITHUB_REPOSITORY), template the name of
    the template (TEMPLATE_REPOSITORY in the workflow), is_template the template switch.
    """
    state = load_state(root)
    if state:
        return "manuscript", [
            {
                "name": "%s / %s" % (state["journal"], state["article_type"]),
                "slug": "manuscript",
                "journal": state["journal"],
                "type": state["article_type"],
                "configure": False,
            }
        ]
    if repository and template and repository.lower() != template.lower() and not is_template:
        return "copy", [
            {
                "name": "Not configured yet: the skeleton as it came",
                "slug": "manuscript",
                "journal": "",
                "type": "",
                "configure": False,
            }
        ]
    return "template", [
        {
            "name": "%s / %s" % (journal["name"], atype["name"]),
            "slug": "%s--%s" % (journal["key"], atype["key"]),
            "journal": journal["name"],
            "type": atype["name"],
            "configure": True,
        }
        for journal, atype in pairs(data)
    ]


def tell_github(refusal, env):
    """On GitHub, put a refusal where a person looks: on the page of the run.

    Without this the page says only that the step ended with exit code 2, and the reason
    stands in the step's log alone. The annotation is one workflow command, so its line
    ends and percent signs are written the way GitHub asks. The summary takes it whole.
    """
    if env.get("GITHUB_ACTIONS") == "true":
        escaped = refusal.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print("::error title=Nothing was written::%s" % escaped)
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("**Nothing was written.**\n\n```text\n%s\n```\n" % refusal.replace("`", "'"))


def main(argv=None):
    env = os.environ
    parser = argparse.ArgumentParser(
        description="Configure this repository as the manuscript of one RSNA journal and article type.",
        epilog="A community template: not made or endorsed by the RSNA. "
        "Check the journal's instructions before you submit.",
    )
    parser.add_argument("--journal", default=env.get("RSNA_JOURNAL") or None, help="the journal, as --list prints it")
    parser.add_argument("--type", dest="article_type", default=env.get("RSNA_TYPE") or None, help="the article type, as --list prints it")
    parser.add_argument("--title", default=env.get("RSNA_TITLE") or None, help="the title of the manuscript")
    parser.add_argument("--description", default=env.get("RSNA_DESCRIPTION") or None, help="one or two sentences for the README")
    parser.add_argument("--list", action="store_true", help="print the journals and their article types")
    parser.add_argument("--force", action="store_true", help="write over files edited since they were written")
    parser.add_argument("--matrix", action="store_true", help="print what the build compiles (for the GitHub workflow)")
    parser.add_argument("--root", default=str(REPO), help="where to write (default: this repository)")
    parser.add_argument("--data", default=None, help="another requirements file (default: journals/requirements.json)")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    data = load_data(args.data)
    if args.list:
        print(list_choices(data))
        return 0
    if args.matrix:
        state, entries = matrix(
            data,
            args.root,
            repository=env.get("GITHUB_REPOSITORY"),
            template=env.get("TEMPLATE_REPOSITORY"),
            is_template=str(env.get("IS_TEMPLATE") or "").strip().lower() == "true",
        )
        print("state=%s" % state)
        print("matrix=%s" % json.dumps(entries, separators=(",", ":")))
        return 0
    try:
        if not args.journal or not args.article_type:
            raise Refused(
                "Give the journal and the article type (--journal, --type). The choices are:\n"
                + list_choices(data)
            )
        state = configure(data, args.root, args.journal, args.article_type, args.title, args.description, args.force)
    except Refused as refusal:
        print("Refused: %s" % refusal, file=sys.stderr)
        tell_github(str(refusal), env)
        return 2
    report = ["Configured: %s, %s" % (state["journal"], state["article_type"]), "Title: %s" % state["title"]]
    report += ["Wrote %s" % name for name in OUTPUTS + (STATE_FILE,)]
    report.append(
        "The limits in the files are what was read on %s. Check the journal's instructions before you submit: %s"
        % (state["requirements_read_on"], state["instructions"])
    )
    print("\n".join(report))
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        # the page of the workflow run on GitHub: the same report, as plain text
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("```text\n%s\n```\n" % "\n".join(report).replace("`", "'"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
