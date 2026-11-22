#!/usr/bin/env python3
"""The form "Configure the manuscript": what a submitted form says, and what is said back.

A new copy of the template opens one issue by itself, "Set up this manuscript", with a
link to the form (.github/ISSUE_TEMPLATE/configure-manuscript.yml). Submitting the form
opens an issue whose text holds the answers, each under a heading of its question, the
way GitHub writes them. The workflow .github/workflows/configure-form.yml runs this:

    python3 scripts/issue_form.py read --reply FILE
        reads the issue's text (RSNA_ISSUE_BODY) and the permission of its author on the
        repository (RSNA_PERMISSION); checks the choice the way scripts/configure.py does,
        writing nothing; then
        writes go=true and the four answers to GITHUB_OUTPUT, or go=false and, in FILE, the
        answer to post on the issue
    python3 scripts/issue_form.py done       the answer once the manuscript is written
    python3 scripts/issue_form.py failed     the answer when the run did not finish
    python3 scripts/issue_form.py setup --issues FILE
        the text of the "Set up this manuscript" issue; nothing when the workflow opened one
        before (FILE: the repository's issues, one JSON object a line)
    python3 scripts/issue_form.py setup-title
    python3 scripts/issue_form.py setup-open --issues FILE
        the numbers of the setup issues still open, to close once the manuscript is written
    python3 scripts/issue_form.py setup-done --issue N
        what is said on the setup issue when it is closed

What a person typed is untrusted: it reaches this script in an environment variable and
is read as text, never run. Python standard library only.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import configure  # noqa: E402

FORM_FILE = "configure-manuscript.yml"
FORM_TITLE = "Configure the manuscript"
SETUP_TITLE = "Set up this manuscript"
BOT = "github-actions[bot]"
# The form's questions, by the label GitHub writes as the heading of each answer, and the
# name each answer goes by. The form uses exactly these labels, in this order (a test).
QUESTIONS = (
    ("Journal", "journal"),
    ("Article type", "article_type"),
    ("Title of the manuscript", "title"),
    ("Short description", "description"),
)
# What GitHub writes for a question left empty.
NO_RESPONSE = "_No response_"
HEADING = re.compile(r"^###[ \t]+(.+?)[ \t]*#*[ \t]*$")
# Who may configure: a person whose permission on the repository is admin or write (the
# "permission" GitHub's API gives for a collaborator, where maintain shows as write). The
# issue's author_association is not enough, either way: an organization's member may only
# read some of its repositories, and in a private repository GitHub's event has named an
# organization's owner with admin permission CONTRIBUTOR (seen in a trial, 2026-11-22).
PERMISSIONS = ("admin", "write")
ARTIFACT = "pdf-manuscript"


# ---------------------------------------------------------------------------- reading


def answers(body):
    """The form's answers by name, as the text under each question's heading.

    Only the form's own headings start an answer, so a heading typed inside the
    description stays part of it. An empty answer, GitHub's "_No response_", is "".
    """
    names = dict(QUESTIONS)
    found, current = {}, None
    for line in (body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        heading = HEADING.match(line)
        if heading and heading.group(1) in names and names[heading.group(1)] not in found:
            current = names[heading.group(1)]
            found[current] = []
        elif current is not None:
            found[current].append(line)
    result = {}
    for name in names.values():
        text = "\n".join(found.get(name, [])).strip()
        result[name] = "" if text == NO_RESPONSE else text
    return result


def is_form(body):
    """Does the text hold the form's two drop-downs?"""
    names = [HEADING.match(line) for line in (body or "").replace("\r\n", "\n").split("\n")]
    labels = set(match.group(1) for match in names if match)
    return "Journal" in labels and "Article type" in labels


def may_configure(permission):
    return (permission or "").strip().lower() in PERMISSIONS


# ---------------------------------------------------------------------------- what is said


def form_link(server, repository):
    return "%s/%s/issues/new?template=%s" % (server, repository, FORM_FILE)


def quoted(text):
    """Text as one fenced block: on GitHub it shows as typed, and nothing in it links,
    mentions anyone or ends the block."""
    return "```text\n%s\n```" % str(text).replace("`", "'").rstrip("\n")


NOT_ALLOWED = (
    "Only a person who can write to this repository can configure it from this form, "
    "so nothing was done.\n\n"
    "If this is your manuscript, ask the repository's owner to give you write access "
    "(**Settings**, **Collaborators**), or to fill in the form."
)


def edit_hint(server, repository):
    return (
        "To put it right, edit this issue: open the **···** menu at the top right of its first "
        "message, choose **Edit**, change the answer under its heading (a name exactly as the "
        "list above gives it), and save. The run starts again by itself. Or close this issue and "
        "[fill in the form again](%s)."
        % form_link(server, repository)
    )


def refused_reply(refusal, server, repository, hint=True):
    parts = [
        "**Nothing was written.** The reason, as the script that writes the manuscript gives it:",
        quoted(refusal),
    ]
    if hint:
        parts.append(edit_hint(server, repository))
    return "\n\n".join(parts)


def check(data, root, body, permission, server="https://github.com", repository=""):
    """What to configure, or what to say instead: (answers, None) or (None, reply)."""
    if not may_configure(permission):
        return None, NOT_ALLOWED
    given = answers(body)
    try:
        if not given["journal"]:
            raise configure.Refused(
                "No journal was chosen. The journals are:\n"
                + "\n".join("    " + name for name in configure.journal_names(data))
            )
        journal = configure.find_journal(data, given["journal"])
        if not given["article_type"]:
            raise configure.Refused(
                "No article type was chosen. %s has:\n%s"
                % (journal["name"], "\n".join("    " + atype["name"] for atype in journal["article_types"]))
            )
        atype = configure.find_type(data, journal, given["article_type"])
        title = configure.clean_line(given["title"])
        if not title:
            raise configure.Refused("The title is empty. Type the title of the manuscript under its heading.")
        description = configure.clean_line(given["description"])
    except configure.Refused as refusal:
        return None, refused_reply(str(refusal), server, repository)
    try:
        # a file the author has edited since it was written: the form cannot change that
        configure.configure(data, root, journal["name"], atype["name"], title, description, dry_run=True)
    except configure.Refused as refusal:
        return None, refused_reply(str(refusal), server, repository, hint=False)
    return {
        "journal": journal["name"],
        "article_type": atype["name"],
        "title": title,
        "description": description,
    }, None


def done_reply(data, journal_name, type_name, commit, artifact, server, repository, run_id):
    journal = configure.find_journal(data, journal_name)
    atype = configure.find_type(data, journal, type_name)
    base = "%s/%s" % (server, repository)
    run = "%s/actions/runs/%s" % (base, run_id)
    if commit:
        saved = "`main.tex`, `title_page.tex`, `README.md` and `manuscript.json` were written and saved in commit [%s](%s/commit/%s)." % (
            commit[:7], base, commit)
    else:
        saved = "`main.tex`, `title_page.tex`, `README.md` and `manuscript.json` were already written this way, so nothing new was saved."
    if artifact:
        pdf = "The first PDF: **[%s](%s/artifacts/%s)**, a zip file that holds `main.pdf` and `title_page.pdf`. It is also under **Artifacts** at the bottom of [the run](%s)." % (
            ARTIFACT, run, artifact, run)
    else:
        pdf = "The first PDF: under **Artifacts** at the bottom of [the run](%s), named **%s**." % (run, ARTIFACT)
    return "\n".join([
        "**Done.** This repository is now the manuscript of *%s*, article type **%s**." % (journal["name"], atype["name"]),
        "",
        "- " + saved,
        "- " + pdf,
        "- From now on, write in `main.tex`. Every change you save builds the PDF again: **Actions**, the newest **Build** run, **Artifacts**.",
        "- The limits written into the files were read second-hand on %s. Check them against the journal's own instructions before you submit: <%s>"
        % (data["meta"]["made_on"], journal["instructions_url"]),
        "",
        "This issue is closed. To choose again, [fill in the form again](%s): a file you have edited since it was written is never written over."
        % form_link(server, repository),
    ])


def failed_reply(commit, server, repository, run_id):
    base = "%s/%s" % (server, repository)
    run = "%s/actions/runs/%s" % (base, run_id)
    if commit:
        state = "The files were written and saved in commit [%s](%s/commit/%s), but the first PDF was not made." % (commit[:7], base, commit)
    else:
        state = "Nothing was saved in the repository."
    return "\n\n".join([
        "**The run did not finish**, so this issue stays open. Open [the run](%s) to see where it stopped." % run,
        state,
        "Once the cause is put right, edit this issue (any change to its text) and the run starts again.",
    ])


def setup_body(server, repository):
    base = "%s/%s" % (server, repository)
    return "\n".join([
        "This repository is a copy of a LaTeX template for the journals of the RSNA. It is not set up yet: "
        "`main.tex` still holds the sample (Radiology: Artificial Intelligence, Original Research).",
        "",
        "### **[Open the form: choose the journal and the article type](%s)**" % form_link(server, repository),
        "",
        "1. Press the link above. A form opens.",
        "2. Choose the journal and the article type, type the title of the manuscript and, if you like, a short "
        "description. Press the green button at the bottom to create the issue.",
        "3. Wait a few minutes. A run on GitHub writes `main.tex`, `title_page.tex` and `README.md` for your choice, "
        "saves them here, builds the first PDF, answers on your issue with a link to the PDF, and closes it. "
        "It closes this issue too.",
        "",
        "If the journal you chose does not take that article type, the answer lists the types it takes. "
        "Edit your issue to choose one of them, and the run starts again.",
        "",
        "Only a person who can write to this repository can configure it.",
        "",
        "The other way, without the form: **[Actions](%s/actions/workflows/configure.yml)**, **Configure manuscript**, "
        "**Run workflow**. If you configure it that way, close this issue yourself." % base,
        "",
        "The limits written into the files were read second-hand. Check them against the journal's own "
        "instructions before you submit. This is a community template, not made or endorsed by the RSNA.",
    ])


def read_issues(path):
    """The issues a file lists, one JSON object a line (what the workflow's gh call prints)."""
    issues = []
    for line in Path(path).read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if line:
            issues.append(json.loads(line))
    return issues


def setup_issues(issues, state=None):
    """The setup issues the workflow opened, in any state or in the one named."""
    return [
        issue for issue in issues
        if issue.get("title") == SETUP_TITLE and issue.get("login") == BOT and not issue.get("pull")
        and (state is None or issue.get("state") == state)
    ]


# ---------------------------------------------------------------------------- the command


def write_outputs(values, env):
    """name=value lines for GitHub's GITHUB_OUTPUT (or stdout off GitHub). Every value is
    one line: the answers were made one line by clean_line, the rest is from the data."""
    lines = []
    for name, value in values.items():
        value = str(value)
        if "\n" in value or "\r" in value:
            raise ValueError("an output of more than one line: %s" % name)
        lines.append("%s=%s" % (name, value))
    target = env.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


def main(argv=None):
    env = os.environ
    parser = argparse.ArgumentParser(description="Read the form \"Configure the manuscript\" and word the answers.")
    parser.add_argument("command", choices=["read", "done", "failed", "setup", "setup-title", "setup-open", "setup-done"])
    parser.add_argument("--reply", help="read: where to write the answer when nothing is configured")
    parser.add_argument("--issues", help="setup, setup-open: the repository's issues, one JSON object a line")
    parser.add_argument("--issue", help="setup-done: the number of the form's issue")
    parser.add_argument("--root", default=str(configure.REPO), help="the repository (default: this one)")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    server = env.get("GITHUB_SERVER_URL") or "https://github.com"
    repository = env.get("GITHUB_REPOSITORY") or "OWNER/REPOSITORY"
    data = configure.load_data()

    if args.command == "read":
        body = env.get("RSNA_ISSUE_BODY") or ""
        if not is_form(body):
            write_outputs({"go": "false"}, env)
            print("This issue does not hold the form's answers: nothing to do.")
            return 0
        values, reply = check(data, args.root, body, env.get("RSNA_PERMISSION"), server, repository)
        if values is None:
            write_outputs({"go": "false"}, env)
            if args.reply:
                Path(args.reply).write_text(reply + "\n", encoding="utf-8")
            print(reply)
            return 0
        write_outputs(dict(go="true", **values), env)
        print("To configure: %s, %s" % (values["journal"], values["article_type"]))
        return 0
    if args.command == "done":
        print(done_reply(
            data, env.get("RSNA_JOURNAL"), env.get("RSNA_TYPE"), env.get("RSNA_COMMIT") or "",
            env.get("RSNA_ARTIFACT") or "", server, repository, env.get("GITHUB_RUN_ID") or "",
        ))
        return 0
    if args.command == "failed":
        print(failed_reply(env.get("RSNA_COMMIT") or "", server, repository, env.get("GITHUB_RUN_ID") or ""))
        return 0
    if args.command == "setup-title":
        print(SETUP_TITLE)
        return 0
    if args.command == "setup":
        earlier = setup_issues(read_issues(args.issues)) if args.issues else []
        if earlier:
            print("The setup issue was opened before (#%s): nothing to do." % earlier[0]["number"], file=sys.stderr)
            return 0
        print(setup_body(server, repository))
        return 0
    if args.command == "setup-open":
        for issue in setup_issues(read_issues(args.issues), state="open"):
            print(issue["number"])
        return 0
    if args.command == "setup-done":
        print("Configured from the form in #%s. This issue is done." % int(args.issue))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
