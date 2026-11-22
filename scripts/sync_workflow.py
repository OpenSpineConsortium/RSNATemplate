#!/usr/bin/env python3
"""Keep what is written out in the repository in step with journals/requirements.json.

    python scripts/sync_workflow.py           rewrite what is out of step
    python scripts/sync_workflow.py --check   change nothing; exit 1 if anything is out of step

Three things are made from the data and kept as files:

  1. the two drop-down lists of .github/workflows/configure.yml (journals; article types),
     and the same two lists in the form .github/ISSUE_TEMPLATE/configure-manuscript.yml,
     with the list under them of which journal takes which article type;
  2. the table of journals, article types and limits in the template's README.md;
  3. main.tex and title_page.tex as the template ships them: the skeleton of the default
     choice, so that the template itself always compiles.

Run it after a change to the data or to a template. A test (tests/test_configure.py)
fails while any of the three differs from the data. In a repository that has been
configured as a manuscript, only the first applies: the README and the two .tex files
are then the author's.

Python standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import configure  # noqa: E402

WORKFLOW = Path(".github") / "workflows" / "configure.yml"
FORM = Path(".github") / "ISSUE_TEMPLATE" / "configure-manuscript.yml"
README = Path("README.md")
SHIPPED = ("main.tex", "title_page.tex")
NOT_READ = "not read"
GRADE_ORDER = "ABCP"
# the facts of an article type that make up one row of the README table
ROW_FIELDS = (
    "body_word_limit",
    "body_words_count",
    "section_word_limits",
    "abstract_kind",
    "abstract_word_limit",
    "abstract_headings",
    "summary_statement",
    "key_points_label",
    "key_points_max",
    "key_points_word_limit",
    "references_limit",
    "figures_limit",
    "tables_limit",
)


# ---------------------------------------------------------------------------- blocks


def replace_block(text, name, lines):
    """Replace what stands between the lines 'BEGIN name' and 'END name'."""
    rows = text.split("\n")
    begin = [i for i, row in enumerate(rows) if re.search(r"\bBEGIN %s\b" % re.escape(name), row)]
    end = [i for i, row in enumerate(rows) if re.search(r"\bEND %s\b" % re.escape(name), row)]
    if len(begin) != 1 or len(end) != 1 or end[0] < begin[0]:
        raise ValueError("expected one 'BEGIN %s' line and one 'END %s' line after it" % (name, name))
    return "\n".join(rows[: begin[0] + 1] + list(lines) + rows[end[0]:])


def block(text, name):
    """The lines that stand between 'BEGIN name' and 'END name'."""
    rows = text.split("\n")
    begin = next(i for i, row in enumerate(rows) if re.search(r"\bBEGIN %s\b" % re.escape(name), row))
    end = next(i for i, row in enumerate(rows) if re.search(r"\bEND %s\b" % re.escape(name), row))
    return rows[begin + 1:end]


# ---------------------------------------------------------------------------- the workflow


def workflow_options(text, name):
    """The choices a drop-down of the workflow offers, read back from its text."""
    return [json.loads(row.strip()[2:]) for row in block(text, name) if row.strip().startswith("- ")]


def sync_workflow(data, text):
    for name, choices in (("journals", configure.journal_names(data)), ("article types", configure.type_names(data))):
        rows = text.split("\n")
        begin = next(row for row in rows if re.search(r"\bBEGIN %s\b" % re.escape(name), row))
        indent = begin[: len(begin) - len(begin.lstrip())]
        text = replace_block(text, name, [indent + "- " + json.dumps(choice, ensure_ascii=False) for choice in choices])
    return text


def form_pairs(data, indent):
    """The list under the form's drop-downs: each journal and the article types it takes."""
    lines = [""]
    for journal in data["journals"]:
        lines.append(indent + "- **%s**" % journal["name"])
        lines.extend(indent + "  - " + atype["name"] for atype in journal["article_types"])
    return lines + [""]


def sync_form(data, text):
    """The form's two drop-down lists, as in the workflow, and the list of pairs."""
    text = sync_workflow(data, text)
    begin = next(row for row in text.split("\n") if re.search(r"\bBEGIN pairs\b", row))
    return replace_block(text, "pairs", form_pairs(data, begin[: len(begin) - len(begin.lstrip())]))


# ---------------------------------------------------------------------------- the README table


def _value(fact):
    return fact.get("value") if isinstance(fact, dict) else None


def cell_body(atype):
    limit = configure.words(_value(atype["body_word_limit"]))
    if limit is None:
        return NOT_READ
    counted = _value(atype["body_words_count"])
    if counted:
        limit += " (%s)" % counted
    sections = _value(atype["section_word_limits"])
    if sections:
        limit += "; " + ", ".join("%s %s" % (name, count) for name, count in sections.items())
    return limit


def cell_abstract(atype):
    kind = _value(atype["abstract_kind"])
    if kind is None:
        return NOT_READ
    if kind == "none":
        return "none"
    text = kind
    limit = configure.words(_value(atype["abstract_word_limit"]))
    if limit is not None:
        text += ", %s words" % limit
    headings = _value(atype["abstract_headings"])
    if headings:
        text += ": " + ", ".join(headings)
    return text


def cell_summary(atype):
    statement = _value(atype["summary_statement"])
    if statement is None:
        return NOT_READ
    if statement.get("required") is False:
        return "none"
    details = []
    if statement.get("max_words") is not None:
        details.append("%s words" % statement["max_words"])
    if statement.get("max_characters") is not None:
        details.append("%s characters" % statement["max_characters"])
    count = re.match(r"\d+(-\d+)?", str(statement.get("sentences") or ""))
    if count:
        details.append("%s sentence%s" % (count.group(), "" if count.group() == "1" else "s"))
    return "required" + (": " + ", ".join(details) if details else "")


def cell_key_points(atype):
    label = _value(atype["key_points_label"])
    if label is None:
        return NOT_READ
    if label.lower().startswith("none"):
        return "none"
    most = _value(atype["key_points_max"])
    limit = _value(atype["key_points_word_limit"])
    details = []
    if isinstance(most, int):
        details.append("up to %s" % most)
    elif most:
        details.append(str(most))
    if isinstance(limit, int) and limit > 0:
        details.append("%s words" % limit)
    elif isinstance(limit, str):
        details.append(limit)
    return label + (": " + ", ".join(details) if details else "")


def cell_plain(fact):
    return configure.words(_value(fact)) or NOT_READ


def how_sure(facts):
    grades = set(fact.get("grade") for fact in facts if _value(fact) is not None and fact.get("grade"))
    return ", ".join(sorted(grades, key=lambda grade: GRADE_ORDER.find(grade))) or "-"


def journal_table(data, journal):
    """The README section of one journal: its table and the sources of every row."""
    sources = []  # (address, route, date, official page)

    def number(fact):
        official = fact.get("official_page")
        for address in [fact.get("source")] + list(fact.get("also") or []):
            entry = (address, fact.get("via") if address == fact.get("source") else None, fact.get("read"),
                     official if address == fact.get("source") else None)
            known = [i for i, other in enumerate(sources) if other[0] == address]
            if known:
                # keep the fuller record of the same address
                if entry[1] and not sources[known[0]][1]:
                    sources[known[0]] = entry
                yield known[0] + 1
            else:
                sources.append(entry)
                yield len(sources)

    lines = [
        "### %s" % journal["name"],
        "",
        "The journal's instructions: <%s>" % journal["instructions_url"],
        "",
        "| Article type | Body words | Abstract | Summary statement | Key points | References | Figures | Tables | How sure | Sources |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for atype in journal["article_types"]:
        facts = [atype[field] for field in ROW_FIELDS]
        used = sorted(set(n for fact in facts if _value(fact) is not None for n in number(fact)))
        cells = [
            atype["name"],
            cell_body(atype),
            cell_abstract(atype),
            cell_summary(atype),
            cell_key_points(atype),
            cell_plain(atype["references_limit"]),
            cell_plain(atype["figures_limit"]),
            cell_plain(atype["tables_limit"]),
            how_sure(facts),
            ", ".join(str(n) for n in used) or "-",
        ]
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in cells) + " |")
    lines += ["", "Sources of this table:", ""]
    for index, (address, route, date, official) in enumerate(sources, 1):
        text = "%d. <%s>" % (index, address)
        if route or date:
            text += " (%s)" % ", ".join(part for part in (route, "read %s" % date if date else None) if part)
        if official:
            text += "; the official page it copies: <%s>" % official
        lines.append(text)
    return lines


def readme_table(data):
    lines = [""]
    for journal in data["journals"]:
        lines += journal_table(data, journal) + [""]
    return lines


def readme_legend(data):
    lines = ["", "How sure a line is:", ""]
    lines += ["- **%s**: %s" % (letter, meaning) for letter, meaning in data["grades"].items()]
    lines += ["", "How a page was read (the word in brackets after each source):", ""]
    lines += ["- **%s**: %s" % (route, meaning) for route, meaning in data["via"].items()]
    lines.append("")
    return lines


def sync_readme(data, text):
    text = replace_block(text, "legend", readme_legend(data))
    return replace_block(text, "limits", readme_table(data))


# ---------------------------------------------------------------------------- all three


def out_of_step(root=None, data=None):
    """{path: text it should have} for every file that differs from the data."""
    root = Path(root or configure.REPO)
    data = data or configure.load_data()
    wanted = {}
    workflow = configure.read(root / WORKFLOW)
    wanted[WORKFLOW] = sync_workflow(data, workflow)
    if (root / FORM).exists():
        wanted[FORM] = sync_form(data, configure.read(root / FORM))
    if configure.load_state(root) is None:
        wanted[README] = sync_readme(data, configure.read(root / README))
        default = configure.render_default(data)
        for name in SHIPPED:
            wanted[Path(name)] = default[name]
    stale = {}
    for path, text in wanted.items():
        target = root / path
        if not target.exists() or configure.read(target) != text:
            stale[path] = text
    return stale


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keep the workflow's lists, the README table and the shipped skeleton in step with journals/requirements.json.")
    parser.add_argument("--check", action="store_true", help="change nothing; exit 1 if anything is out of step")
    parser.add_argument("--root", default=str(configure.REPO), help="the repository (default: this one)")
    args = parser.parse_args(argv)
    stale = out_of_step(args.root)
    for path, text in stale.items():
        if args.check:
            print("out of step with journals/requirements.json: %s" % path.as_posix())
        else:
            configure.write(Path(args.root) / path, text)
            print("rewrote %s" % path.as_posix())
    if not stale:
        print("in step with journals/requirements.json")
    if args.check and stale:
        print("run: python scripts/sync_workflow.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
