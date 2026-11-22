"""Tests of the form "Configure the manuscript": scripts/issue_form.py, the form itself
(.github/ISSUE_TEMPLATE/configure-manuscript.yml) and the two workflows around it
(.github/workflows/configure-form.yml and setup-issue.yml).

    python -m pytest tests

The issues below are made up, written the way GitHub writes a submitted form: each answer
under a heading of its question's label, and "_No response_" for a question left empty.
pytest and the Python standard library, nothing else.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import configure  # noqa: E402
import issue_form  # noqa: E402
import sync_workflow  # noqa: E402

DATA = configure.load_data()
FORM = REPO / ".github" / "ISSUE_TEMPLATE" / issue_form.FORM_FILE
WORKFLOWS = REPO / ".github" / "workflows"
SERVER, REPOSITORY = "https://github.com", "author/my-manuscript"
GOOD = dict(journal="Radiology: Artificial Intelligence", article_type="Original Research",
            title="Deep learning finds every vertebra", description="One sentence about it.")


def issue(**given):
    """An issue's text as GitHub writes a submitted form."""
    parts = []
    for label, name in issue_form.QUESTIONS:
        parts.append("### %s\n\n%s" % (label, given.get(name) or issue_form.NO_RESPONSE))
    return "\n\n".join(parts)


def check(body, tmp_path, permission="admin"):
    return issue_form.check(DATA, tmp_path, body, permission, SERVER, REPOSITORY)


def run(*arguments, **environment):
    env = dict(os.environ)
    for name in list(env):
        if name.startswith(("RSNA_", "GITHUB_")):
            env.pop(name)
    env.update(environment)
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "issue_form.py")] + list(arguments),
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, encoding="utf-8",
    )


def outputs(path):
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    return dict(line.split("=", 1) for line in lines if line)


def scripts_of(text):
    """Every line of a workflow that is part of a script a shell runs (run: and its block)."""
    lines, indent_of_block = [], None
    for line in text.split("\n"):
        indent = len(line) - len(line.lstrip())
        if indent_of_block is not None and line.strip() and indent <= indent_of_block:
            indent_of_block = None
        if indent_of_block is not None or re.match(r"\s+(- )?run: \S", line):
            lines.append(line)
        if re.match(r"\s+(- )?run: [|>]-?$", line):
            indent_of_block = indent
    return lines


def job(text, name):
    start = text.index("\n  %s:\n" % name)
    following = re.search(r"\n  [a-z_]+:\n", text[start + 1:])
    return text[start:start + 1 + following.start()] if following else text[start:]


# ---------------------------------------------------------------------------- the form


def test_the_form_asks_exactly_the_questions_the_script_reads():
    text = configure.read(FORM)
    labels = re.findall(r"(?m)^      label: (.+)$", text)
    assert labels == [label for label, _ in issue_form.QUESTIONS]
    assert re.findall(r"(?m)^    id: (.+)$", text) == [name for _, name in issue_form.QUESTIONS]
    assert re.findall(r"(?m)^  - type: (.+)$", text) == ["markdown", "dropdown", "dropdown", "markdown", "input", "textarea"]
    assert re.findall(r"(?m)^title: (.+)$", text) == [issue_form.FORM_TITLE]
    # every question says in plain words what it wants; the title is required like the
    # workflow's (GitHub enforces "required" in public repositories only: the script checks too)
    assert len(re.findall(r"(?m)^      description: \S", text)) == 4
    assert re.findall(r"(?m)^      required: (.+)$", text) == ["true", "true", "true", "false"]
    assert "not made or endorsed by the RSNA" in text and "Use this template" in text


def test_the_form_offers_the_choices_of_the_data():
    text = configure.read(FORM)
    journals = sync_workflow.workflow_options(text, "journals")
    types = sync_workflow.workflow_options(text, "article types")
    assert journals == configure.journal_names(DATA)
    assert types == configure.type_names(DATA)
    workflow = configure.read(REPO / sync_workflow.WORKFLOW)
    assert journals == sync_workflow.workflow_options(workflow, "journals")
    assert types == sync_workflow.workflow_options(workflow, "article types")
    # the first choice is chosen at the start: the same as the workflow's defaults
    assert re.findall(r"(?m)^      default: (.+)$", text) == ["0", "0"]
    assert (journals[0], types[0]) == (configure.DEFAULT_JOURNAL, configure.DEFAULT_TYPE)
    # the list of which journal takes which type: every pair of the data, once
    listed = sync_workflow.block(text, "pairs")
    for journal in DATA["journals"]:
        start = listed.index("        - **%s**" % journal["name"])
        names = [row.strip()[2:] for row in listed[start + 1:start + 1 + len(journal["article_types"])]]
        assert names == [atype["name"] for atype in journal["article_types"]]
    assert sum(1 for row in listed if row.startswith("          - ")) == len(configure.pairs(DATA))


def test_the_sync_writes_the_lists_of_the_form(tmp_path):
    text = configure.read(FORM)
    emptied = sync_workflow.replace_block(text, "pairs", [])
    emptied = sync_workflow.replace_block(emptied, "journals", ["        - \"Nothing\""])
    assert sync_workflow.sync_form(DATA, emptied) == text
    assert sync_workflow.FORM.as_posix() == ".github/ISSUE_TEMPLATE/" + issue_form.FORM_FILE


# ---------------------------------------------------------------------------- reading


def test_the_answers_are_read_as_github_writes_them():
    assert issue_form.answers(issue(**GOOD)) == GOOD
    empty = issue_form.answers(issue(journal="Radiology"))
    assert empty == dict(journal="Radiology", article_type="", title="", description="")
    # an issue edited in a browser comes back with Windows line ends
    assert issue_form.answers(issue(**GOOD).replace("\n", "\r\n")) == GOOD
    # a heading typed in the description stays part of it; only the form's headings count
    text = issue(**dict(GOOD, description="First line.\n\n### Journal\n\nRadiology\n\n### Notes\nmore"))
    found = issue_form.answers(text)
    assert found["journal"] == GOOD["journal"]
    assert found["description"] == "First line.\n\n### Journal\n\nRadiology\n\n### Notes\nmore"
    # words written above the answers are not an answer
    assert issue_form.answers("Some words first.\n\n" + issue(**GOOD)) == GOOD
    assert issue_form.is_form(issue(**GOOD)) and not issue_form.is_form("### Journal\n\nRadiology")
    assert not issue_form.is_form("A blank issue about something else.")


def test_a_good_pair_is_checked_without_writing_anything(tmp_path):
    values, reply = check(issue(**GOOD), tmp_path)
    assert reply is None
    assert values == GOOD
    assert list(tmp_path.iterdir()) == [], "the check writes nothing"
    # names as typed by hand in an edit are found as the script finds them
    values, _ = check(issue(**dict(GOOD, journal="radiology: artificial intelligence", article_type="original research")), tmp_path)
    assert (values["journal"], values["article_type"]) == (GOOD["journal"], GOOD["article_type"])
    # a title and a description of several lines become one line each
    values, _ = check(issue(**dict(GOOD, title="Two\nlines", description="Line one\nline two")), tmp_path)
    assert (values["title"], values["description"]) == ("Two lines", "Line one line two")
    values, _ = check(issue(**dict(GOOD, description="")), tmp_path)
    assert values["description"] == ""


def test_a_pair_that_does_not_go_together_is_refused_with_the_types_of_the_journal(tmp_path):
    values, reply = check(issue(**dict(GOOD, article_type="Radiology Diagnosis Please")), tmp_path)
    assert values is None
    assert reply.startswith("**Nothing was written.**")
    assert 'Radiology: Artificial Intelligence has no article type "Radiology Diagnosis Please". It has:' in reply
    journal = configure.find_journal(DATA, GOOD["journal"])
    listed = reply.split("```text\n", 1)[1].split("\n```", 1)[0].split("\n")
    assert listed[1:] == ["    " + atype["name"] for atype in journal["article_types"]]
    assert "edit this issue" in reply and "**Edit**" in reply
    assert "%s/%s/issues/new?template=%s" % (SERVER, REPOSITORY, issue_form.FORM_FILE) in reply
    assert list(tmp_path.iterdir()) == [], "a refusal writes nothing"


def test_every_other_wrong_answer_is_refused_and_says_why(tmp_path):
    cases = {
        "journal": ("Journal of Nothing", ['Unknown journal "Journal of Nothing". The journals are:'] + configure.journal_names(DATA)),
        "no journal": ("", ["No journal was chosen. The journals are:"] + configure.journal_names(DATA)),
        "no type": ("", ["No article type was chosen. Radiology: Artificial Intelligence has:", "AI in Brief"]),
        "no title": ("", ["The title is empty."]),
    }
    for case, (value, said) in cases.items():
        given = dict(GOOD)
        given[{"journal": "journal", "no journal": "journal", "no type": "article_type", "no title": "title"}[case]] = value
        values, reply = check(issue(**given), tmp_path)
        assert values is None, case
        for words in said:
            assert words in reply, (case, words)
        assert "edit this issue" in reply, case
    assert list(tmp_path.iterdir()) == []


def test_only_a_person_who_can_write_may_configure(tmp_path):
    # the permission GitHub's API gives (maintain shows as write, triage as read); what
    # the issue's author_association says is not asked
    for permission in ("admin", "write", "ADMIN", " write\n"):
        values, reply = check(issue(**GOOD), tmp_path, permission)
        assert values == GOOD and reply is None, permission
    for permission in ("read", "none", "triage", "maintain-ish", "", None):
        values, reply = check(issue(**GOOD), tmp_path, permission)
        assert values is None and reply == issue_form.NOT_ALLOWED, permission
    # the answer to a stranger says nothing of what was typed
    values, reply = check(issue(**dict(GOOD, article_type="Radiology Diagnosis Please")), tmp_path, "read")
    assert reply == issue_form.NOT_ALLOWED
    assert "Only a person who can write to this repository can configure it" in reply and "nothing was done" in reply


def test_an_edited_file_is_refused_and_the_answer_says_how(tmp_path):
    configure.configure(DATA, tmp_path, "Radiology", "Original Research", "First title")
    main = tmp_path / "main.tex"
    configure.write(main, configure.read(main) + "\nMy own words.\n")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    values, reply = check(issue(**GOOD), tmp_path)
    assert values is None
    assert "main.tex changed since" in reply and "--force" in reply
    assert "edit this issue" not in reply, "editing the issue cannot put this right"
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_what_was_typed_cannot_reach_a_command_or_become_a_link(tmp_path):
    typed = "x```\n@someone [a link](https://example.com) <b>"
    values, reply = check(issue(**dict(GOOD, article_type=typed)), tmp_path)
    assert values is None
    fenced = reply.split("```text\n", 1)[1]
    assert fenced.count("```") == 1, "what was typed cannot end the fenced block"
    assert "@someone [a link](https://example.com)" in fenced.split("```")[0]
    # the outputs for GitHub are one line each, whatever was typed
    out = tmp_path / "output.txt"
    reply_file = tmp_path / "reply.md"
    title = "A title\ngo=false\r\njournal=Radiology\u2028article_type=Review"
    result = run("read", "--reply", str(reply_file), "--root", str(tmp_path / "empty"),
                 RSNA_ISSUE_BODY=issue(**dict(GOOD, title=title)), RSNA_ASSOCIATION="CONTRIBUTOR", RSNA_PERMISSION="admin",
                 GITHUB_OUTPUT=str(out))
    assert result.returncode == 0, result.stderr
    lines = out.read_text(encoding="utf-8").split("\n")
    assert [line.split("=", 1)[0] for line in lines if line] == ["go", "journal", "article_type", "title", "description"]
    assert outputs(out) == dict(go="true", journal=GOOD["journal"], article_type=GOOD["article_type"],
                                title="A title go=false journal=Radiology article_type=Review",
                                description=GOOD["description"])
    assert not reply_file.exists()


def test_the_command_says_go_or_writes_the_answer(tmp_path):
    out, reply_file = tmp_path / "output.txt", tmp_path / "reply.md"
    root = tmp_path / "copy"
    root.mkdir()
    environment = dict(RSNA_ASSOCIATION="CONTRIBUTOR", RSNA_PERMISSION="write", GITHUB_OUTPUT=str(out),
                       GITHUB_SERVER_URL=SERVER, GITHUB_REPOSITORY=REPOSITORY)
    result = run("read", "--reply", str(reply_file), "--root", str(root),
                 RSNA_ISSUE_BODY=issue(**dict(GOOD, article_type="Radiology Diagnosis Please")), **environment)
    assert result.returncode == 0, result.stderr
    assert outputs(out) == {"go": "false"}
    assert "Radiology Diagnosis Please" in reply_file.read_text(encoding="utf-8")
    assert list(root.iterdir()) == []
    out.unlink()
    reply_file.unlink()
    result = run("read", "--reply", str(reply_file), "--root", str(root), RSNA_ISSUE_BODY=issue(**GOOD),
                 **dict(environment, RSNA_PERMISSION="read"))
    assert outputs(out) == {"go": "false"}
    assert reply_file.read_text(encoding="utf-8") == issue_form.NOT_ALLOWED + "\n"
    out.unlink()
    reply_file.unlink()
    # an issue that is not the form's: nothing to say
    result = run("read", "--reply", str(reply_file), "--root", str(root), RSNA_ISSUE_BODY="A note to myself.", **environment)
    assert result.returncode == 0 and outputs(out) == {"go": "false"} and not reply_file.exists()
    out.unlink()


def test_an_edit_is_acted_on_only_when_the_text_changed(tmp_path):
    out, reply_file = tmp_path / "output.txt", tmp_path / "reply.md"
    root = tmp_path / "copy"
    root.mkdir()
    bad = issue(**dict(GOOD, article_type="Radiology Diagnosis Please"))
    environment = dict(RSNA_PERMISSION="admin", GITHUB_OUTPUT=str(out), RSNA_ACTION="edited")
    # the title alone was edited: GitHub's event carries an empty previous text (seen in a
    # trial), or the same text; nothing is said a second time
    for previous in ("", bad, bad.replace("\n", "\r\n") + "\n"):
        result = run("read", "--reply", str(reply_file), "--root", str(root), RSNA_ISSUE_BODY=bad,
                     RSNA_PREVIOUS_BODY=previous, **environment)
        assert result.returncode == 0 and outputs(out) == {"go": "false"} and not reply_file.exists(), repr(previous)
        assert "not its text" in result.stdout
        out.unlink()
    # the text was edited: the new answers are read
    result = run("read", "--reply", str(reply_file), "--root", str(root), RSNA_ISSUE_BODY=issue(**GOOD),
                 RSNA_PREVIOUS_BODY=bad, **environment)
    assert outputs(out)["go"] == "true" and not reply_file.exists()
    assert issue_form.unchanged(None, "x") and issue_form.unchanged("a\r\nb", "a\nb\n") and not issue_form.unchanged("a", "b")


# ---------------------------------------------------------------------------- what is said


def test_the_answer_once_it_is_done_says_where_everything_is():
    done = issue_form.done_reply(DATA, GOOD["journal"], GOOD["article_type"], "0123456789abcdef" * 2 + "01234567",
                                 "4242", SERVER, REPOSITORY, "99")
    base = "%s/%s" % (SERVER, REPOSITORY)
    assert done.startswith("**Done.** This repository is now the manuscript of *Radiology: Artificial Intelligence*, article type **Original Research**.")
    assert "[0123456](%s/commit/0123456789abcdef" % base in done
    assert "**[pdf-manuscript](%s/actions/runs/99/artifacts/4242)**" % base in done
    assert "[the run](%s/actions/runs/99)" % base in done
    assert configure.find_journal(DATA, GOOD["journal"])["instructions_url"] in done
    assert DATA["meta"]["made_on"] in done and "This issue is closed." in done
    again = issue_form.done_reply(DATA, GOOD["journal"], GOOD["article_type"], "", "", SERVER, REPOSITORY, "99")
    assert "nothing new was saved" in again and "/artifacts/" not in again and "**pdf-manuscript**" in again
    failed = issue_form.failed_reply("", SERVER, REPOSITORY, "99")
    assert "**The run did not finish**" in failed and "Nothing was saved" in failed and "/actions/runs/99" in failed
    assert "but the first PDF was not made" in issue_form.failed_reply("abcdef1234", SERVER, REPOSITORY, "99")


def test_the_setup_issue_says_what_to_do_and_opens_once(tmp_path):
    text = issue_form.setup_body(SERVER, REPOSITORY)
    assert "(%s/%s/issues/new?template=configure-manuscript.yml)" % (SERVER, REPOSITORY) in text
    assert FORM.exists()
    assert "Configure manuscript" in text and "Run workflow" in text, "the other way stays"
    assert "Only a person who can write to this repository can configure it." in text
    assert "not made or endorsed by the RSNA" in text
    listing = tmp_path / "issues.jsonl"

    def made(number, title=issue_form.SETUP_TITLE, state="open", login=issue_form.BOT, pull=False):
        return json.dumps(dict(number=number, title=title, state=state, login=login, pull=pull))

    # no setup issue yet: one by a person with the same title, a pull request, another issue
    listing.write_text("\n".join([
        made(1, login="someone"), made(2, pull=True), made(3, title="Configure the manuscript"),
    ]) + "\n", encoding="utf-8")
    result = run("setup", "--issues", str(listing), GITHUB_SERVER_URL=SERVER, GITHUB_REPOSITORY=REPOSITORY)
    assert result.returncode == 0 and result.stdout.strip() == text.strip()
    assert run("setup-open", "--issues", str(listing)).stdout == ""
    # opened before, and closed since: not again
    listing.write_text(made(4, state="closed") + "\n", encoding="utf-8")
    result = run("setup", "--issues", str(listing))
    assert result.returncode == 0 and result.stdout == "" and "#4" in result.stderr
    # still open: closed once the manuscript is written
    listing.write_text(made(5) + "\n" + made(6, state="closed") + "\n", encoding="utf-8")
    assert run("setup-open", "--issues", str(listing)).stdout.split() == ["5"]
    assert run("setup-title").stdout.strip() == issue_form.SETUP_TITLE
    assert run("setup-done", "--issue", "7").stdout.strip() == "Configured from the form in #7. This issue is done."


# ---------------------------------------------------------------------------- the workflows


def test_the_form_workflow_runs_the_configure_steps_and_is_safe():
    text = configure.read(WORKFLOWS / "configure-form.yml")
    assert "\non:\n  issues:\n    types: [opened, edited]\n" in text
    assert "\npermissions: {}\n" in text
    template = re.findall(r"(?m)^  TEMPLATE_REPOSITORY: (\S+)$", configure.read(WORKFLOWS / "configure.yml"))
    check_job = job(text, "check")
    for condition in ("github.event.repository.is_template == false",
                      "github.repository != '%s'" % template[0],
                      "github.event.issue.state == 'open'",
                      "contains(github.event.issue.body, '### Journal')",
                      "contains(github.event.issue.body, '### Article type')",
                      "(github.event.action == 'opened' || github.event.changes.body.from != '')"):
        assert re.search(r"\n      (&& )?%s\n" % re.escape(condition), check_job.split("runs-on:")[0]), condition
    # the least each job needs
    permissions = {name: re.findall(r"(?m)^    permissions:\n((?:      .*\n)+)", job(text, name)) for name in ("check", "configure", "answer")}
    assert permissions == {
        "check": ["      contents: read\n      issues: write\n"],
        "configure": ["      contents: write\n"],
        "answer": ["      actions: read\n      contents: read\n      issues: write\n"],
    }
    # the same steps as "Configure manuscript": that workflow, called with the answers
    configure_job = job(text, "configure")
    assert "    uses: ./.github/workflows/configure.yml\n" in configure_job
    assert "    if: needs.check.outputs.go == 'true'\n" in configure_job
    for name in ("journal", "article_type", "title", "description"):
        assert "      %s: ${{ needs.check.outputs.%s }}\n" % (name, name) in configure_job
    assert "python3 scripts/configure.py" not in text, "one copy of the steps, in configure.yml"
    # the issue's text and the author's name reach the script in the environment alone
    expressions = re.findall(r"(?m)^(.*)\$\{\{ (github\.event\.issue\.[a-z_.]+) \}\}$", text)
    assert sorted(set(name for _, name in expressions)) == [
        "github.event.issue.author_association", "github.event.issue.body", "github.event.issue.number",
        "github.event.issue.user.login"]
    for before, name in expressions:
        if name != "github.event.issue.number":
            assert re.fullmatch(r" {10}RSNA_[A-Z_]+: ", before), before + name
    assert text.count("${{ github.event.issue.body }}") == 1
    assert "          RSNA_ISSUE_BODY: ${{ github.event.issue.body }}\n" in text
    for line in scripts_of(text):
        assert "${{" not in line, line
    assert "python3 scripts/issue_form.py read --reply" in text
    assert "--jq '.permission'" in text
    assert "gh issue close \"$ISSUE\"" in text and "python3 scripts/issue_form.py setup-open" in text
    assert "    if: always() && needs.check.outputs.go == 'true'\n" in job(text, "answer")


def test_the_configure_workflow_can_be_called_with_the_same_inputs():
    text = configure.read(WORKFLOWS / "configure.yml")
    call = text.split("  workflow_call:\n", 1)[1].split("  workflow_dispatch:\n", 1)[0]
    dispatch = text.split("  workflow_dispatch:\n", 1)[1].split("\npermissions:", 1)[0]
    names = lambda block: re.findall(r"(?m)^      ([a-z_]+):$", block)  # noqa: E731
    assert names(call.split("\n    outputs:\n")[0]) == names(dispatch) == ["journal", "article_type", "title", "description"]
    assert names(call.split("\n    outputs:\n")[1]) == ["commit"]
    assert "        value: ${{ jobs.configure.outputs.commit }}\n" in call
    assert "      commit: ${{ steps.commit.outputs.sha }}\n" in job(text, "configure")
    assert 'echo "sha=$(git rev-parse HEAD)" >> "$GITHUB_OUTPUT"' in text


def test_the_setup_workflow_opens_the_issue_in_a_new_copy_alone():
    text = configure.read(WORKFLOWS / "setup-issue.yml")
    assert "\non:\n  push:\n" in text and "\npermissions: {}\n" in text
    template = re.findall(r"(?m)^  TEMPLATE_REPOSITORY: (\S+)$", configure.read(WORKFLOWS / "configure.yml"))
    condition = job(text, "open").split("runs-on:")[0]
    for part in ("github.event.repository.is_template == false", "github.event.repository.fork == false",
                 "github.repository != '%s'" % template[0],
                 "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)"):
        assert part in condition, part
    assert re.findall(r"(?m)^    permissions:\n((?:      .*\n)+)", text) == ["      contents: read\n      issues: write\n"]
    assert "if [ -f manuscript.json ]; then" in text
    assert "python3 scripts/issue_form.py setup --issues" in text
    assert "gh issue create" in text and text.count("gh issue create") == 1
    for line in scripts_of(text):
        assert "${{" not in line, line
