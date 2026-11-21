# A manuscript configured for the check

The repository in the state the Configure manuscript workflow leaves it in.

A manuscript for *Radiology: Artificial Intelligence*, article type **Original Research**, written in LaTeX (LuaLaTeX).

## What the journal asks of this article type

As read on 2026-11-21, in plain words. These are not the journal's own words, and nobody has compared them with the live page: **check the journal's instructions before you submit**: https://pubs.rsna.org/page/ai/author-instructions

| | As read | How sure |
|---|---|---|
| Title words | not read; check the journal's page |  |
| By invitation | no | B |
| Body words | 3000 | B |
| What the body count covers | Introduction to Discussion | B |
| Words by section | Introduction: 400; Materials and Methods: 800; Results: 1000; Discussion: 800 | C |
| Abstract | structured | B |
| Abstract words | 250 | B |
| Abstract headings | Purpose, Materials and Methods, Results, Conclusion | P |
| Summary statement | required: yes; characters at most: 255; sentences: 1 (the manuscript-type entries say 1-2 sentences; the title-page entry and the checklist say a single sentence of no more than 255 characters, in boldface) | B |
| Key points box | Key Points | B |
| Key points, how many | 3 | B |
| Key points, words | not read; check the journal's page |  |
| Body headings | Introduction, Materials and Methods, Results, Discussion | P |
| References | 35 | B |
| Figures | 6 | B |
| Tables | 4 | B |
| Reporting checklist | when: at first submission of Original Research and Technical Development papers that involve human subjects; not for animal studies; mark items that do not apply N/A; CLAIM: for AI manuscripts in medical imaging; STARD: diagnostic accuracy; CONSORT: randomized controlled trials; PRISMA: meta-analyses; STROBE: observational studies (cohort, case-control, cross-sectional) | B |
| Also | systematic reviews and meta-analyses are submitted as Original Research | B |
| Abbreviations | at most: 10; listed on: abbreviated title page; not in: the Key Points (obvious ones like CT and MRI are fine) | B |

How sure:

- **A**: read on the official site itself on the date given
- **B**: read in a full copy of the official page (the browser print of 2025-09-18), or the same value in two or more separate answers of the search tool about the official page, or one such answer in the page's own words that the journal's printed articles agree with. Agreement between answers shows that the copy was read steadily, not that the copy is current
- **C**: one answer of the search tool only, or an answer that was ambiguous; confirm on the live page first
- **P**: measured from the journal's printed articles; shows what is printed after editing, not what the instructions ask

The same lines, and the ones that hold for every article type of the journal (title pages, anonymisation, statements, file type), stand as comments at the top of `main.tex`. Their sources, each with its address and date, are in `journals/requirements.json`.

## Files

| File | What it is |
|---|---|
| `main.tex` | the manuscript: abbreviated title page (anonymized), abstract, body, references, figure legends |
| `title_page.tex` | the full title page (authors, institutions, funding, disclosures, data sharing statement): a separate file, not anonymized |
| `rsnastyle.tex`, `rsnafont.tex`, `rsnastyle.css` | the style: an 11-point Times font, double spacing, no page numbers, figures and tables at the end |
| `nejm.bbx`, `nejm.cbx` | the reference style |
| `sample_bibliography.bib` | sample references: replace them with yours |
| `latexmkrc` | the build settings |
| `manuscript.json` | what this repository was configured as |

## Build

On GitHub: every push builds `main.pdf` and `title_page.pdf`. Open Actions, the latest run of "Build", and download the PDFs under Artifacts.

On a laptop with TeX Live or MiKTeX (LuaLaTeX, latexmk, biber):

    latexmk

builds both PDFs and then makes the HTML copy of the manuscript that opens in Microsoft Word (lwarp). For the PDFs alone, set `RSNA_PDF_ONLY=1` first:

    RSNA_PDF_ONLY=1 latexmk             (Linux, macOS)
    $env:RSNA_PDF_ONLY=1; latexmk       (Windows PowerShell)

The font is Times New Roman where it is installed, and TeX Gyre Termes, a free font of the same shape that every TeX Live has, where it is not.

In Overleaf: New Project, Import from GitHub, this repository (or download it as a ZIP and use Upload Project). Overleaf reads `latexmkrc`, so the compiler is LuaLaTeX whatever the menu says. The main document is `main.tex`; to print the full title page, set the main document to `title_page.tex` in the menu and compile once.

## Another journal or article type

    python scripts/configure.py --list
    python scripts/configure.py --journal "Radiology: Artificial Intelligence" --type "Original Research" --title "..." --description "..."

or Actions, "Configure manuscript", Run workflow. A file you have edited since the last configuration is never written over: the run stops and names it, unless you add `--force` on a laptop.

## Credit

Made from a community LaTeX template for manuscripts sent to the journals of the Radiological Society of North America (RSNA). It is not made or endorsed by the RSNA. The template descends from https://github.com/cai4cai/RSNATemplate, whose style files, reference style and writing notes it keeps.
