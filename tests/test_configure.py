"""Tests of scripts/configure.py and scripts/sync_workflow.py.

    python -m pytest tests

pytest and the Python standard library, nothing else. No LaTeX is run here: the
compile of every journal and article type is the job of .github/workflows/build.yml.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import configure  # noqa: E402
import sync_workflow  # noqa: E402

DATA = configure.load_data()
PAIRS = configure.pairs(DATA)
IDS = ["%s--%s" % (journal["key"], atype["key"]) for journal, atype in PAIRS]
SPECIAL_TITLE = "Check: 100% of A & B, under_score, #1, {braces}, ~tilde, ^caret, \\backslash, $dollar"

# The tests of the template's own README and shipped skeleton do not apply in a repository
# that has been configured as a manuscript: those files are then the author's.
template_only = pytest.mark.skipif(
    configure.load_state(REPO) is not None, reason="this repository is configured as a manuscript"
)


def type_fields():
    """The facts of an article type, as the data itself lists them."""
    return [name.split(" ")[0] for name in DATA["meta"]["article_type_fields"]]


def leaves(value):
    """Every number and every phrase inside a value of the data."""
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [str(value)]
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [leaf for item in value for leaf in leaves(item)]
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in leaves(item)]
    raise TypeError(type(value))


def flat(text):
    """Text with its wrapped comment lines joined: one line, single blanks."""
    return " ".join(re.sub(r"(?m)^%+", " ", text).split())


def has(text, leaf):
    """Is the number or phrase there, whole (35 is not found inside 350)?"""
    leaf = " ".join(leaf.split())
    if re.fullmatch(r"[0-9.]+", leaf):
        return re.search(r"(?<![0-9.])%s(?![0-9])" % re.escape(leaf), text) is not None
    return leaf in text


def top_block(main):
    """The block of comments at the top of main.tex, where every fact is listed."""
    first = main.index(configure.RULE)
    second = main.index(configure.RULE, first + 1)
    return main[first:second]


def code_lines(text):
    """The lines of a .tex file that LaTeX reads, each without its trailing comment."""
    lines = []
    for line in text.split("\n"):
        if line.lstrip().startswith("%"):
            continue
        lines.append(re.sub(r"(?<!\\)%.*$", "", line))
    return lines


@pytest.fixture(scope="module")
def rendered():
    return {
        pair_id: configure.render(DATA, journal, atype, "A title", "A description.")
        for pair_id, (journal, atype) in zip(IDS, PAIRS)
    }


# ---------------------------------------------------------------------------- the data


def test_the_data_has_six_journals_and_their_types():
    assert len(DATA["journals"]) == 6
    assert len(PAIRS) == 55
    assert len(set(IDS)) == len(IDS)
    assert configure.DEFAULT_JOURNAL in configure.journal_names(DATA)
    journal = configure.find_journal(DATA, configure.DEFAULT_JOURNAL)
    assert configure.find_type(DATA, journal, configure.DEFAULT_TYPE)["name"] == configure.DEFAULT_TYPE


def test_every_fact_names_its_source_and_date():
    def walk(node, path):
        if isinstance(node, dict):
            assert "quote" not in node, "the pages' own sentences are not reproduced: %s" % path
            if "value" in node and node["value"] is not None:
                assert str(node.get("source", "")).startswith("https://"), path
                assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(node.get("read", ""))), path
                assert node.get("via") in DATA["via"], path
                assert node.get("grade") in DATA["grades"], path
            for key, inner in node.items():
                walk(inner, path + "/" + key)
        elif isinstance(node, list):
            for index, inner in enumerate(node):
                walk(inner, "%s/%d" % (path, index))

    walk(DATA["journals"], "journals")
    walk(DATA["rsna_wide"], "rsna_wide")


def test_every_article_type_has_every_field():
    for journal, atype in PAIRS:
        for field in type_fields():
            assert isinstance(atype.get(field), dict) and "value" in atype[field], (journal["key"], atype["key"], field)
    assert [field for field, _ in configure.TYPE_FIELDS] == type_fields()


# ---------------------------------------------------------------------------- every pair


@pytest.mark.parametrize("pair", PAIRS, ids=IDS)
def test_every_pair_generates(pair, tmp_path):
    journal, atype = pair
    state = configure.configure(DATA, tmp_path, journal["name"], atype["name"], "A title", "A description.")
    assert state["journal"] == journal["name"] and state["article_type"] == atype["name"]
    for name in configure.OUTPUTS + (configure.STATE_FILE,):
        assert (tmp_path / name).stat().st_size > 0, name
    main = configure.read(tmp_path / "main.tex")
    title_page = configure.read(tmp_path / "title_page.tex")
    readme = configure.read(tmp_path / "README.md")
    for text in (main, title_page):
        assert text.count("\\begin{document}") == 1 and text.rstrip().endswith("\\end{document}")
        assert "\\title{A title}" in text
        assert journal["instructions_url"] in text
        assert "not made or endorsed by the RSNA" in flat(text)
    assert "\\textbf{Article type}: " + configure.tex(atype["name"]) in main
    assert "\\input{rsnastyle}" in main and "\\input{rsnafont}" in title_page
    assert readme.startswith("# A title\n\nA description.\n")
    assert journal["name"] in readme and atype["name"] in readme
    assert journal["instructions_url"] in readme
    assert "not made or endorsed by the RSNA" in readme
    assert "https://github.com/cai4cai/RSNATemplate" in readme
    assert configure.TEMPLATE_README_MARK not in readme


@pytest.mark.parametrize("pair", PAIRS, ids=IDS)
def test_every_limit_of_the_data_appears(pair, rendered):
    journal, atype = pair
    main = rendered["%s--%s" % (journal["key"], atype["key"])]["main.tex"]
    block = flat(top_block(main))
    facts = [(field, atype[field]) for field in type_fields()]
    facts += [(field, journal["journal_level"][field]) for field in ("title_word_limit", "abbreviations")]
    labels = dict(configure.TYPE_FIELDS)
    labels.update(configure.JOURNAL_LABELS)
    for field, fact in facts:
        if fact["value"] is None:
            # no answer in the data: the skeleton says so and prints no number
            assert "%s: %s" % (labels[field], configure.NOT_READ) in block, field
            continue
        found = leaves(fact["value"])
        for leaf in found:
            assert has(block, leaf), "%s: %r is not in the skeleton" % (field, leaf)
        if found and fact.get("grade"):
            assert "[%s]" % fact["grade"] in block


@pytest.mark.parametrize("pair", PAIRS, ids=IDS)
def test_the_limits_stand_where_they_apply(pair, rendered):
    journal, atype = pair
    main = rendered["%s--%s" % (journal["key"], atype["key"])]["main.tex"]
    body = flat(main[main.index("\\maketitle"):])
    for field in ("body_word_limit", "abstract_word_limit", "references_limit", "figures_limit", "tables_limit",
                  "key_points_max", "key_points_word_limit"):
        for leaf in leaves(atype[field]["value"]):
            assert has(body, leaf), "%s: %r is not repeated in the body of the file" % (field, leaf)
    # the headings the data names are sections, in its order, each with its own limit
    headings = atype["body_headings"]["value"] or []
    places = [main.index("\\section*{%s}" % configure.tex(heading)) for heading in headings]
    assert places == sorted(places)
    limits = atype["section_word_limits"]["value"] or {}
    for heading, limit in limits.items():
        if heading in headings:
            start = main.index("\\section*{%s}" % heading)
            assert "Words in this section: %s" % limit in main[start:start + 400]
    # a structured abstract carries the headings of the data, in its order
    if atype["abstract_kind"]["value"] == "structured" and atype["abstract_headings"]["value"]:
        places = [main.index("\n%s: " % heading) for heading in atype["abstract_headings"]["value"]]
        assert places == sorted(places)
    if atype["abstract_kind"]["value"] == "none":
        assert "\\section*{Abstract}" not in main
    label = atype["key_points_label"]["value"]
    if label and not label.lower().startswith("none"):
        assert "\\textbf{%s}:" % label in main


@pytest.mark.parametrize("pair", PAIRS, ids=IDS)
def test_no_unfilled_placeholder_is_left(pair, rendered):
    journal, atype = pair
    for name, text in rendered["%s--%s" % (journal["key"], atype["key"])].items():
        assert not configure.PLACEHOLDER.search(text), name
        assert "<<" not in text and ">>" not in text, name
        assert "%[" not in text, "a note kept its tag in %s" % name
        assert "None" not in text and "null" not in flat(text).split(), name


@pytest.mark.parametrize("pair", PAIRS, ids=IDS)
def test_the_latex_is_balanced(pair, rendered):
    journal, atype = pair
    files = rendered["%s--%s" % (journal["key"], atype["key"])]
    for name in ("main.tex", "title_page.tex"):
        code = "\n".join(code_lines(files[name]))
        for environment in ("document", "itemize", "figure", "table", "tabular", "center"):
            assert code.count("\\begin{%s}" % environment) == code.count("\\end{%s}" % environment), (name, environment)
        bare = re.sub(r"\\[{}\\]", "", code)
        assert bare.count("{") == bare.count("}"), name
    main = "\n".join(code_lines(files["main.tex"]))
    # the sample abbreviation is used once, so the list of abbreviations is never empty
    assert main.count("\\acrfull{MRI}") == 1
    assert "\\printglossary" in main
    # figures, tables and references are laid out only where the article type takes them
    assert ("\\begin{figure}" in main) == configure.allowed(atype["figures_limit"])
    assert ("Figure Legend(s)" in main) == configure.allowed(atype["figures_limit"])
    assert ("\\begin{table}" in main) == configure.allowed(atype["tables_limit"])
    assert ("\\printbibliography" in main) == configure.allowed(atype["references_limit"])


def test_the_statements_and_the_checklist_are_there(rendered):
    for pair_id, files in rendered.items():
        main, title_page = files["main.tex"], files["title_page.tex"]
        for statement in ("Funding", "Disclosures", "Data sharing", "Code availability", "Use of AI tools in writing"):
            assert statement + ": " in top_block(main), (pair_id, statement)
        assert "\\textbf{Use of AI tools in writing}: TODO" in main, pair_id
        assert "\\textbf{Code availability}: TODO" in main, pair_id
        assert "% Reporting checklist: " in main, pair_id
        for line in ("\\textbf{Funding}: TODO", "\\textbf{Disclosures}: TODO", "\\textbf{Data sharing statement}: TODO"):
            assert line in title_page, (pair_id, line)
        # the manuscript is anonymized: no author is named in it
        assert "\\author" not in main and "\\affil" not in main, pair_id
        assert "\\author" in title_page, pair_id


def test_the_kept_notes_go_where_they_hold(rendered):
    radiology = rendered["radiology--original-research"]["main.tex"]
    other = rendered["radiology-ai--original-research"]["main.tex"]
    for main in (radiology, other):
        assert "% Typically contains background information" in main
        assert "No more than 400 words" not in main, "the limit comes from the data, not from the note"
    assert "Radiology recommends that authors seek statistical consultation" in radiology
    assert "Radiology recommends" not in other
    assert "Key Results will translate directly to visual abstracts" in radiology
    assert "visual abstracts" not in other
    # the notes were written for a research article: a letter does not get them
    assert "Typically contains background information" not in rendered["radiology--letter"]["main.tex"]


def test_radiology_ai_original_research_is_as_read(rendered):
    main = rendered["radiology-ai--original-research"]["main.tex"]
    block = flat(top_block(main))
    for line in (
        "Body words: 3000 [B]",
        "What the body count covers: Introduction to Discussion [B]",
        "Abstract: structured [B]",
        "Abstract words: 250 [B]",
        "Abstract headings: Purpose, Materials and Methods, Results, Conclusion [P]",
        "characters at most: 255",
        "Key points box: Key Points [B]",
        "References: 35 [B]",
        "Figures: 6 [B]",
        "Tables: 4 [B]",
        "CLAIM: for AI manuscripts in medical imaging",
    ):
        assert line in block, line
    assert "Background:" not in "\n".join(code_lines(main)), "this journal's abstract has four headings"
    assert "\\textbf{Keywords}: TODO" in main
    radiology = rendered["radiology--original-research"]["main.tex"]
    assert "Abstract words: 300 [B]" in flat(top_block(radiology))
    assert "\nBackground: " in radiology and "\\textbf{Key Results}:" in radiology
    assert "\\textbf{Keywords}" not in radiology


# ---------------------------------------------------------------------------- refusals


def test_running_twice_gives_the_same_files(tmp_path):
    arguments = (DATA, tmp_path, "Radiology", "Technical Developments", SPECIAL_TITLE, "Twice.")
    configure.configure(*arguments)
    first = {name: (tmp_path / name).read_bytes() for name in configure.OUTPUTS + (configure.STATE_FILE,)}
    configure.configure(*arguments)
    second = {name: (tmp_path / name).read_bytes() for name in configure.OUTPUTS + (configure.STATE_FILE,)}
    assert first == second
    assert all(b"\r" not in content for content in first.values())


def test_an_unknown_pair_is_refused_with_what_exists(tmp_path):
    with pytest.raises(configure.Refused) as refusal:
        configure.configure(DATA, tmp_path, "Radiology: Artificial Intelligence", "Radiology Diagnosis Please")
    journal = configure.find_journal(DATA, "Radiology: Artificial Intelligence")
    for atype in journal["article_types"]:
        assert atype["name"] in str(refusal.value)
    with pytest.raises(configure.Refused) as refusal:
        configure.configure(DATA, tmp_path, "Journal of Nothing", "Original Research")
    for name in configure.journal_names(DATA):
        assert name in str(refusal.value)
    assert list(tmp_path.iterdir()) == [], "a refusal writes nothing"


def test_the_names_of_the_drop_down_resolve_or_are_refused():
    for journal in DATA["journals"]:
        for atype in journal["article_types"]:
            assert configure.find_type(DATA, journal, atype["name"]) is atype
            assert configure.find_type(DATA, journal, atype["name"].upper()) is atype
            assert configure.find_type(DATA, journal, atype["key"]) is atype
        for name in configure.type_names(DATA):
            try:
                found = configure.find_type(DATA, journal, name)
            except configure.Refused:
                continue
            assert found in journal["article_types"]
    # the name another journal gives the same kind of article
    journal = configure.find_journal(DATA, "radiology: artificial intelligence")
    assert configure.find_type(DATA, journal, "Review articles")["name"] == "Review"


def test_an_edited_file_is_not_written_over(tmp_path):
    configure.configure(DATA, tmp_path, "Radiology", "Original Research", "First title")
    main = tmp_path / "main.tex"
    written = configure.read(main)
    configure.write(main, written + "\nMy own words.\n")
    with pytest.raises(configure.Refused) as refusal:
        configure.configure(DATA, tmp_path, "Radiology", "Review articles", "Second title")
    assert "main.tex" in str(refusal.value) and "--force" in str(refusal.value)
    assert configure.read(main).endswith("My own words.\n")
    assert configure.load_state(tmp_path)["title"] == "First title", "a refusal writes nothing"
    configure.configure(DATA, tmp_path, "Radiology", "Review articles", "Second title", force=True)
    assert "My own words." not in configure.read(main)
    assert configure.load_state(tmp_path)["article_type"] == "Review articles"
    # untouched files of an earlier configuration are replaced without --force
    configure.configure(DATA, tmp_path, "Radiology", "Letters to the Editor and Replies", "Third title")
    assert configure.load_state(tmp_path)["title"] == "Third title"


@template_only
def test_a_fresh_copy_of_the_template_is_configured_without_force(tmp_path):
    for name in configure.OUTPUTS:
        shutil.copy(str(REPO / name), str(tmp_path / name))
    configure.configure(DATA, tmp_path, "Radiology", "Original Research", "A title")
    assert configure.load_state(tmp_path)["journal"] == "Radiology"
    assert configure.TEMPLATE_README_MARK not in configure.read(tmp_path / "README.md")


@template_only
def test_a_template_file_someone_edited_is_not_written_over(tmp_path):
    for name in configure.OUTPUTS:
        shutil.copy(str(REPO / name), str(tmp_path / name))
    configure.write(tmp_path / "main.tex", configure.read(tmp_path / "main.tex") + "\nMy own words.\n")
    with pytest.raises(configure.Refused):
        configure.configure(DATA, tmp_path, "Radiology", "Original Research", "A title")
    assert not (tmp_path / configure.STATE_FILE).exists()


def test_a_typed_title_cannot_break_latex_or_the_readme(tmp_path):
    configure.configure(DATA, tmp_path, "Radiology", "Original Research", SPECIAL_TITLE + "\n\\input{/etc/passwd}", "Line one\nline two <b>")
    title = (
        "\\title{Check: 100\\% of A \\& B, under\\_score, \\#1, \\{braces\\}, \\textasciitilde{}tilde, "
        "\\textasciicircum{}caret, \\textbackslash{}backslash, \\$dollar \\textbackslash{}input\\{/etc/passwd\\}}"
    )
    for name in ("main.tex", "title_page.tex"):
        text = configure.read(tmp_path / name)
        assert title in text, name
        assert "\\input{/etc" not in text
    readme = configure.read(tmp_path / "README.md")
    assert readme.split("\n")[0].startswith("# Check: 100% of A &amp; B, under\\_score, \\#1")
    assert readme.split("\n")[2] == "Line one line two &lt;b&gt;"
    assert configure.load_state(tmp_path)["title"].startswith("Check: 100% of A & B")


# ---------------------------------------------------------------------------- the command


def run(*arguments, **environment):
    env = dict(os.environ)
    for name in ("RSNA_JOURNAL", "RSNA_TYPE", "RSNA_TITLE", "RSNA_DESCRIPTION", "GITHUB_STEP_SUMMARY"):
        env.pop(name, None)
    env.update(environment)
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "configure.py")] + list(arguments),
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )


def test_list_prints_the_choices():
    result = run("--list")
    assert result.returncode == 0
    lines = result.stdout.split("\n")
    for journal in DATA["journals"]:
        assert journal["name"] in lines
        for atype in journal["article_types"]:
            assert "    " + atype["name"] in lines


def test_the_workflow_hands_the_choices_over_in_the_environment(tmp_path):
    summary = tmp_path / "summary.md"
    root = tmp_path / "copy"
    root.mkdir()
    result = run(
        "--root", str(root),
        RSNA_JOURNAL="Radiology: Artificial Intelligence", RSNA_TYPE="AI in Brief",
        RSNA_TITLE=SPECIAL_TITLE, RSNA_DESCRIPTION="From the environment.", GITHUB_STEP_SUMMARY=str(summary),
    )
    assert result.returncode == 0, result.stderr
    state = configure.load_state(root)
    assert (state["journal"], state["article_type"]) == ("Radiology: Artificial Intelligence", "AI in Brief")
    assert state["title"] == SPECIAL_TITLE and state["description"] == "From the environment."
    assert "AI in Brief" in summary.read_text(encoding="utf-8")
    # a pair that does not exist: refused, with the list, and nothing written
    other = tmp_path / "other"
    other.mkdir()
    result = run("--root", str(other), RSNA_JOURNAL="RadioGraphics", RSNA_TYPE="AI in Brief")
    assert result.returncode == 2
    assert "Manuscript (full length)" in result.stderr
    assert list(other.iterdir()) == []
    assert run("--root", str(other)).returncode == 2, "no journal and no type is refused too"


def test_the_matrix_is_every_pair_then_the_manuscript_alone(tmp_path):
    def matrix():
        result = run("--matrix", "--root", str(tmp_path))
        assert result.returncode == 0, result.stderr
        lines = dict(line.split("=", 1) for line in result.stdout.strip().split("\n"))
        return lines["configured"], json.loads(lines["matrix"])

    configured, entries = matrix()
    assert configured == "false"
    assert [(entry["journal"], entry["type"]) for entry in entries] == [(j["name"], t["name"]) for j, t in PAIRS]
    assert [entry["slug"] for entry in entries] == IDS
    assert all(entry["configure"] is True for entry in entries)
    configure.configure(DATA, tmp_path, "Radiology", "Original Research")
    configured, entries = matrix()
    assert configured == "true"
    assert len(entries) == 1 and entries[0]["configure"] is False and entries[0]["slug"] == "manuscript"


# ---------------------------------------------------------------------------- the workflows


def test_the_choices_of_the_workflow_equal_the_data():
    text = configure.read(REPO / sync_workflow.WORKFLOW)
    journals = sync_workflow.workflow_options(text, "journals")
    types = sync_workflow.workflow_options(text, "article types")
    assert journals == [journal["name"] for journal in DATA["journals"]]
    assert set(types) == set(atype["name"] for _, atype in PAIRS)
    assert len(types) == len(set(types))
    # nothing is offered outside the two lists
    assert len(re.findall(r'(?m)^\s+- "', text)) == len(journals) + len(types)
    defaults = re.findall(r'(?m)^\s+default: "(.*)"$', text)
    assert defaults == [configure.DEFAULT_JOURNAL, configure.DEFAULT_TYPE]
    assert defaults[0] in journals and defaults[1] in types


def test_the_configure_workflow_is_safe():
    text = configure.read(REPO / sync_workflow.WORKFLOW)
    assert "workflow_dispatch:" in text
    # the one permission it has
    assert re.findall(r"(?m)^permissions:\n((?:  .*\n)+)", text) == ["  contents: write\n"]
    assert "write-all" not in text
    # what was typed reaches the script in the environment, never in a command line
    typed = [line.strip() for line in text.split("\n") if "inputs." in line]
    assert len(typed) == 6
    for line in typed:
        assert re.fullmatch(r"RSNA_[A-Z]+: \$\{\{ inputs\.[a-z_]+ \}\}", line), line
    for line in text.split("\n"):
        if "${{" in line and "inputs." not in line:
            assert re.search(r"\$\{\{ github\.(token|ref_name) \}\}", line), line
    # it refuses to run in the template itself
    assert "is_template" in text and "TEMPLATE_REPOSITORY" in text and "exit 1" in text
    assert text.index("Stop if this is the template itself") < text.index("actions/checkout")
    assert "github-actions[bot]" in text


def test_the_actions_are_pinned_by_version():
    for name in ("configure.yml", "build.yml"):
        text = configure.read(REPO / ".github" / "workflows" / name)
        used = re.findall(r"(?m)^\s+(?:- )?uses: (\S+)", text)
        assert used, name
        for action in used:
            if action.startswith("./"):
                continue
            assert re.fullmatch(r"[\w.-]+/[\w./-]+@v?\d+\.\d+\.\d+", action), "%s in %s is not pinned by version" % (action, name)


def test_the_build_compiles_every_pair_and_keeps_the_pdfs():
    text = configure.read(REPO / ".github" / "workflows" / "build.yml")
    for needed in ("push:", "pull_request:", "ubuntu-latest", "configure.py --matrix", "fromJSON(needs.plan.outputs.matrix)",
                   "python3 scripts/configure.py", "latexmk_use_lualatex: true", "RSNA_PDF_ONLY=1", "upload-artifact",
                   "main.pdf", "title_page.pdf"):
        assert needed in text, needed
    assert re.findall(r"(?m)^permissions:\n((?:  .*\n)+)", text) == ["  contents: read\n"]
    # the check of the template compiles the PDFs alone; the tests run there too
    pdf = text[text.index("\n  pdf:"):text.index("\n  word:")]
    assert "export RSNA_PDF_ONLY=1" in pdf
    assert "needs.plan.outputs.configured == 'false'" in text[text.index("\n  tests:"):text.index("\n  pdf:")]
    # in a manuscript, and only there, a second job keeps the HTML copy; it cannot fail the run
    word = text[text.index("\n  word:"):]
    assert "needs.plan.outputs.configured == 'true'" in word and "continue-on-error: true" in word
    assert "RSNA_PDF_ONLY" not in "\n".join(line for line in word.split("\n") if not line.strip().startswith("#"))
    assert "main.html" in word and "poppler-utils" in word
    latexmkrc = configure.read(REPO / "latexmkrc")
    assert "RSNA_PDF_ONLY" in latexmkrc and "lwarpmk html" in latexmkrc, "the HTML copy stays for authors"
    assert "biber output" in latexmkrc, "the line written for Overleaf stays"
    assert "system('biber', $html)" in latexmkrc and "htmlglossary" in latexmkrc
    assert "$? = $build" in latexmkrc, "the HTML steps do not replace the result of the PDF build"
    font = configure.read(REPO / "rsnafont.tex")
    assert "\\IfFontExistsTF{Times New Roman}" in font and "\\setmainfont{Times New Roman}" in font
    assert "texgyretermes" in font
    assert "\\input{rsnafont}" in configure.read(REPO / "rsnastyle.tex")


def test_everything_made_from_the_data_is_in_step_with_it():
    stale = sync_workflow.out_of_step(REPO, DATA)
    assert not stale, "run: python scripts/sync_workflow.py (out of step: %s)" % ", ".join(
        path.as_posix() for path in stale
    )


@template_only
def test_the_readme_of_the_template_says_what_it_must():
    readme = configure.read(REPO / "README.md")
    assert configure.TEMPLATE_README_MARK in readme
    assert "It is not made, checked or endorsed by the RSNA" in readme
    assert "Use this template" in readme and "Configure manuscript" in readme and "Run workflow" in readme
    assert "python scripts/configure.py --journal" in readme
    assert "Overleaf" in readme and "Import from GitHub" in readme
    assert "check every limit" in readme
    assert "https://github.com/cai4cai/RSNATemplate" in readme
    for journal in DATA["journals"]:
        assert "### %s\n" % journal["name"] in readme
        assert journal["instructions_url"] in readme
        for atype in journal["article_types"]:
            assert "\n| %s | " % atype["name"] in readme, (journal["key"], atype["key"])
    assert "read %s" % DATA["meta"]["made_on"] in readme


@template_only
def test_the_template_ships_the_default_skeleton():
    default = configure.render_default(DATA)
    for name in sync_workflow.SHIPPED:
        assert configure.read(REPO / name) == default[name], "run: python scripts/sync_workflow.py"
    assert "\\title{%s}" % configure.DEFAULT_TITLE in default["main.tex"]
