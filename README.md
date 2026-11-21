<!-- rsna-template: the template's own README. scripts/configure.py replaces this file with the README of your manuscript. -->
# RSNA manuscript template (LaTeX)

A LaTeX template for manuscripts sent to the journals of the Radiological Society of North America (RSNA): Radiology, Radiology: Artificial Intelligence, Radiology: Cardiothoracic Imaging, Radiology: Imaging Cancer, RadioGraphics and Radiology Advances. You choose a journal and an article type, and one step rewrites the files into the skeleton that journal asks of that article type: the items of the title page, the abstract in the right form, the headings of the body with their word limits, the statements, and the full title page as a file of its own.

**This is a community template. It is not made, checked or endorsed by the RSNA.** The limits in it are what could be read of the journals' instructions on the date given below, and nobody has compared them with the live pages. **Before you submit, open the journal's own instructions and check every limit that matters to you.**

It is compiled with LuaLaTeX. The figures and tables go to the end, the pages carry no numbers, the text is double spaced in an 11-point Times font, and the references follow the journals' numbered style.

## Use it

### 1. On GitHub

1. On the front page of this repository press **Use this template**, then **Create a new repository**. A manuscript usually wants a private repository.
2. In the new repository open **Actions**, choose **Configure manuscript** in the list on the left, and press **Run workflow**. Choose the journal and the article type, type the title and a short description, and press **Run workflow**.
3. The run rewrites `main.tex`, `title_page.tex` and `README.md` for that journal and article type, commits them, and builds the first PDFs. Open the run and download the PDFs under **Artifacts**.

After that, every push builds the PDFs again (Actions, the latest run of **Build**).

The same run keeps an HTML copy of the manuscript, for the journals that take the text as a Word file: download the artifact `word-manuscript`, unpack it, open `main.html` in Microsoft Word and save it as a Word document. The copy is made by lwarp, as in the template this one descends from. It carries the text, the tables, the references and the list of abbreviations. How Word shows it has not been checked here: read it through before you upload it.

The article type must be one the journal takes. The list holds the names of all six journals together; if the journal you chose does not take the type you chose, the run stops and lists the types it takes. Nothing is written in that case.

### 2. On a laptop, with one command

    python scripts/configure.py --journal "Radiology: Artificial Intelligence" --type "Original Research" --title "Your title" --description "One or two sentences about the manuscript"

in a clone of your copy, then commit and push. Python 3.8 or later is all it needs. `python scripts/configure.py --list` prints the journals and their article types.

To compile on the laptop (TeX Live or MiKTeX with LuaLaTeX, latexmk and biber):

    latexmk

builds `main.pdf` and `title_page.pdf`, and then makes the same HTML copy for Microsoft Word, `main.html` (lwarp needs the poppler tools `pdftotext` and `pdftocairo` for it). For the PDFs alone, set the environment variable `RSNA_PDF_ONLY=1` first.

### 3. In Overleaf

Configure the repository first, in one of the two ways above. Then, in Overleaf, choose **New Project**, **Import from GitHub**, and your repository. If your Overleaf plan has no GitHub link, download the repository from GitHub as a ZIP (**Code**, **Download ZIP**) and choose **New Project**, **Upload Project**.

Overleaf reads `latexmkrc`, so the compiler is LuaLaTeX whatever its menu says. The main document is `main.tex`. To print the full title page, set the main document to `title_page.tex` in the menu and compile once.

## What the step writes

| File | What it is |
| --- | --- |
| `main.tex` | the manuscript: the abbreviated title page (anonymized), the abstract, the body, the statements that belong to the manuscript, the references and the figure legends. Every limit that was read stands as a comment where it applies, and all of them together at the top of the file |
| `title_page.tex` | the full title page, a file of its own and not anonymized: authors, institutions, word count, funding, disclosures, data sharing statement |
| `README.md` | the README of your manuscript, with its title and description and the limits of its article type. It replaces this page |
| `manuscript.json` | what was chosen |

Where nothing could be read for an item, the skeleton says so and tells you to check the journal's page. It never prints a number that was not read.

A file you have edited since it was written is never written over. If you run the step again after you have started to write, it stops and names the file; `--force` on a laptop writes over it.

The font is Times New Roman where the computer has it, and TeX Gyre Termes, a free font of the same shape that comes with every TeX Live, where it does not (on GitHub's machines, for instance). An author who has Times New Roman gets what the template always gave.

## The journals and article types

**How these limits were read.** On 2026-11-21 the journals' instruction pages would not open to an automated reader. The numbers below were read through a web search tool's copy of each page, through a browser print of Radiology's page dated 2025-09-18 that a third party keeps, and from the articles the journals printed in 2025 and 2026. They are given as plain facts with the address of the page they were read from; the pages' own sentences are not reproduced here. Each row says how sure it is and names its sources.

"not read" means that nothing could be read for that item: check the journal's page. A number is an upper limit unless the row says otherwise.

<!-- BEGIN legend (written by scripts/sync_workflow.py from journals/requirements.json: do not edit by hand) -->

How sure a line is:

- **A**: read on the official site itself on the date given
- **B**: read in a full copy of the official page (the browser print of 2025-09-18), or the same value in two or more separate answers of the search tool about the official page, or one such answer in the page's own words that the journal's printed articles agree with. Agreement between answers shows that the copy was read steadily, not that the copy is current
- **C**: one answer of the search tool only, or an answer that was ambiguous; confirm on the live page first
- **P**: measured from the journal's printed articles; shows what is printed after editing, not what the instructions ask

How a page was read (the word in brackets after each source):

- **direct**: the page itself, read on the date given (HTTP 200)
- **search-copy**: the web search tool's copy of the official page; the live page refused automated reading on the date given (HTTP 403, Cloudflare challenge), so the date is the day the copy was consulted, and the copy may be older than the live page
- **print-2025-09-18**: a browser print of the official page dated 2025-09-18 (PDF metadata), kept by a third party and read in full on the date given; the live page refused automated reading
- **measured**: measured on the date given from the journal's printed articles through the public NCBI interface (PubMed records, PubMed Central full texts); practice, not an instruction

<!-- END legend -->

<!-- BEGIN limits (written by scripts/sync_workflow.py from journals/requirements.json: do not edit by hand) -->

### Radiology: Artificial Intelligence

The journal's instructions: <https://pubs.rsna.org/page/ai/author-instructions>

| Article type | Body words | Abstract | Summary statement | Key points | References | Figures | Tables | How sure | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Original Research | 3000 (Introduction to Discussion); Introduction 400, Materials and Methods 800, Results 1000, Discussion 800 | structured, 250 words: Purpose, Materials and Methods, Results, Conclusion | required: 255 characters, 1 sentence | Key Points: up to 3 | 35 | 6 | 4 | B, C, P | 1, 2, 3 |
| Technical Developments | 2000 (Introduction to Discussion) | structured, 250 words: Purpose, Materials and Methods, Results, Conclusion | required: 255 characters, 1 sentence | Key Points: up to 3 | 25 | 6 | 2 | B, C, P | 1, 2, 4 |
| AI in Brief | 1500 | unstructured, 200 words | required: 255 characters, 1-2 sentences | Key Points: up to 3 | 20 | figures and tables together: 4 | figures and tables together: 4 | B | 1 |
| Data Resources | 1200 (Introduction to Discussion) | none | required: 1-2 sentences | Key Points | 25 | 3 | 2 | B, C, P | 1, 4 |
| Special Report | 6500 (Introduction to Conclusion) | structured or unstructured, 250 words | required: 255 characters, 1-2 sentences | not read | 100 | 6 | 2 | B, C | 1 |
| Review | 3000 (Introduction to Conclusion) | unstructured, 200 words | required: 1 sentence | Essentials: 3 to 5, one sentence each | 50 | 6 | 4 | B, C | 1 |
| Editorial (Invited Commentary; Editorial Opinion) | 1200-1500 (Invited Commentary); 2000 (Editorial Opinion) | none | not read | not read | 35 (Editorial Opinion); not returned for an Invited Commentary | not read | not read | C | 1 |
| Letter to the Editor and Reply | 350 | none | not read | not read | 5 | 0 | 0 | C | 1 |

Sources of this table:

1. <https://pubs.rsna.org/page/ai/author-instructions> (search-copy, read 2026-11-21)
2. <https://pubs.rsna.org/page/ai/author-instructions/checklist> (search-copy, read 2026-11-21)
3. <https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed> (measured, read 2026-11-21)
4. <https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc> (measured, read 2026-11-21)

### Radiology

The journal's instructions: <https://pubs.rsna.org/page/radiology/author-instructions>

| Article type | Body words | Abstract | Summary statement | Key points | References | Figures | Tables | How sure | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Original Research | 3000 (Introduction to Discussion); Introduction 400, Materials and Methods 800, Results 1000, Discussion 800 | structured, 300 words: Background, Purpose, Materials and Methods, Results, Conclusion | required: 30 words, 1 sentence | Key Results: up to 3, 75 words | 35 | 6 | 4 | B | 1 |
| Technical Developments | 2000 (Introduction to Discussion) | structured, 300 words: Background, Purpose, Materials and Methods, Results, Conclusion | required: 30 words, 1 sentence | Key Results: up to 3, 75 words | 25 | 6 | 2 | B | 1 |
| Research Letters | 600 (Introduction to Discussion) | none | required: 30 words, 1 sentence | none | 6 | tables and figures together: 2 | tables and figures together: 2 | B | 1 |
| Review articles | 4500 (Introduction to Conclusion) | unstructured, 200 words | required: 1 sentence | Essentials: 3 to 5, one sentence each | 100 | 12 | 4 | B | 1 |
| Radiology in Focus | 3000 (Introduction to Conclusion) | unstructured, 200 words | required: 1 sentence | Essentials: 3 to 5, one sentence each | 60 | 6 | 3 | B | 1 |
| How I Do It | 3000 (Introduction to Conclusion) | unstructured, 200 words | required: 1 sentence | Essentials: 3 to 5, one sentence each | 60 | 10 | 3 | B | 1 |
| Best Practice | 3000 | unstructured, 200 words | required: 1 sentence | Essentials: 3 to 5, one sentence each | 60 | 6 | 3 | B | 1 |
| Special Reports | 3000 (Introduction to Discussion) | unstructured, 300 words | required: 30 words, 1 sentence | Essentials: up to 3 | 35 | 6 | 4 | B | 1 |
| Radiology Scientific Expert Panel | 4500 (Introduction to Discussion) | unstructured, 300 words | required: 30 words, 1 sentence | Essentials: up to 3 | 35 | 6 | 4 | B | 1 |
| Statements/Guidelines | 4500 recommended (flexible) | unstructured, 200 words | required: 1 sentence | Key Results: 3 to 5, encouraged | varies | encouraged, no number | encouraged, no number | B | 1 |
| Editorials | 1200-1500 (Targeted Editorial on one article); 2000 (Editorial Opinion) | none | not read | not read | 5-10 (Targeted Editorial); 35 (Editorial Opinion) | typically none | typically none (Targeted Editorial); 2 (Editorial Opinion) | B | 1 |
| Letters to the Editor and Replies | 350 | none | not read | not read | 5 | 0 | 0 | B | 1 |
| Images in Radiology | 150 (the main body) | none | not read | not read | 1 to 3 | 1 to 2 | not read | B | 1 |
| Radiology Diagnosis Please | 1500 | none | not read | not read | 10 (none in part 1) | 6 | 0 | B | 1 |
| Radiology In Training: Perspective | 1200-1500 | none | required: 30 words, 1 sentence | none | 5-10 | one summary graphic (table, chart, graph or image) | one summary graphic (table, chart, graph or image) | B | 1 |
| Radiology In Training: Research in Practice | under 3000 | unstructured, under 50 words | required: 30 words, 1 sentence | Teaching Points: 3 to 5, each under 25 words | 80 | 12 | 2 | B | 1 |
| Data Resources | 1200 (Introduction to Discussion) | none | not read | not read | 25 | not read | 2 | C | 2 |

Sources of this table:

1. <https://pubrica.com/wp-content/uploads/2025/09/Radiology_Instructions-for-Authors.pdf> (print-2025-09-18, read 2026-11-21); the official page it copies: <https://pubs.rsna.org/page/radiology/author-instructions>
2. <https://pubs.rsna.org/page/radiology/author-instructions> (search-copy, read 2026-11-21)

### Radiology: Cardiothoracic Imaging

The journal's instructions: <https://pubs.rsna.org/page/cardiothoracic/author-instructions>

| Article type | Body words | Abstract | Summary statement | Key points | References | Figures | Tables | How sure | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Original Research | 3000 (Introduction to Discussion) | structured, 250 words: Purpose, Materials and Methods, Results, Conclusion | required: 255 characters, 1-2 sentences | Key Points: up to 3 | 35 | 6 | 4 | C, P | 1, 2, 3 |
| Technical Developments | 2000 (Introduction to Discussion) | structured, 250 words: Purpose, Materials and Methods, Results, Conclusion | required: 255 characters, 1-2 sentences | Key Points | 25 | 6 | 2 | C, P | 1, 3, 4 |
| Research Letters | 600 | none | not read | none | 6 | tables and figures together: 2 | tables and figures together: 2 | C | 1 |
| Review articles | 3000 (Introduction to Conclusion) | unstructured, 200 words | required: 1 sentence | Essentials: 3 to 5 | 50 | 12 | 4 | C | 1 |
| Case Reports | 1200 | unstructured, 100 words | none | Key Points | 20 | 5 | 0 | C, P | 1, 4 |
| Case Series | 2000 | unstructured, 150 words | required | not read | 30 | 8 | 2 | C | 1 |
| Images in Cardiothoracic Imaging | 150 (the legend) | none | not read | not read | not read | 1 to 2 | not read | C | 1 |
| Editorials (invited commentary) | 1200-1500 | none | not read | not read | 5-10 | typically none | not read | C | 1 |
| Letters to the Editor and Replies | 350 | none | not read | not read | 5 | 0 | 0 | C | 1 |
| Special Reports | not read | not read | required: 1-2 sentences | not read | not read | not read | not read | C | 1 |
| Imaging Essays | not read | not read | not read | not read | not read | not read | not read | - | - |
| Debate | not read | not read | not read | not read | not read | not read | not read | - | - |

Sources of this table:

1. <https://pubs.rsna.org/page/cardiothoracic/author-instructions> (search-copy, read 2026-11-21)
2. <https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed> (measured, read 2026-11-21)
3. <https://pubs.rsna.org/page/cardiothoracic/author-instructions/checklist> (search-copy, read 2026-11-21)
4. <https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc> (measured, read 2026-11-21)

### Radiology: Imaging Cancer

The journal's instructions: <https://pubs.rsna.org/page/imaging-cancer/author-instructions>

| Article type | Body words | Abstract | Summary statement | Key points | References | Figures | Tables | How sure | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Original Research | 3000-5000 (Introduction to Discussion) | structured, 250 words: Purpose, Materials and Methods, Results, Conclusion | required | Key Points: up to 3 | 35 | 8 | 4 | C, P | 1, 2, 3, 4 |
| Technical Developments | 3500 | structured, 250 words: Purpose, Materials and Methods, Results, Conclusion | required | Key Points | 40 | 6 | 2 | C, P | 1, 3 |
| Brief Reports | 2000 | unstructured, 200 words | required | Key Points | 20 | 4 | 4 | C, P | 1, 3 |
| Review articles | 5000 | unstructured, 200 words | required | Essentials | 50 | 12 | 4 | C, P | 1, 3 |
| Images in Cancer | 300 (legend and text) | none | not read | not read | 5 | 4 display panels | not read | C | 1 |
| Editorials and Commentaries | 1200-1500 (invited commentary); 2000 (editorial opinion) | none | not read | not read | 5-10 (invited commentary); 35 (editorial opinion) | about one (invited commentary) | not read | C | 1 |
| Letters to the Editor and Replies | 350 | none | not read | not read | 5 | 0 | 0 | C | 1 |

Sources of this table:

1. <https://pubs.rsna.org/page/imaging-cancer/author-instructions> (search-copy, read 2026-11-21)
2. <https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed> (measured, read 2026-11-21)
3. <https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc> (measured, read 2026-11-21)
4. <https://pubs.rsna.org/page/imaging-cancer/author-instructions/checklist> (search-copy, read 2026-11-21)

### RadioGraphics

The journal's instructions: <https://pubs.rsna.org/page/radiographics/rgauthor_instructions>

| Article type | Body words | Abstract | Summary statement | Key points | References | Figures | Tables | How sure | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Manuscript (full length) | 5000 (the body, without the abstract, summary statement, references and figure legends) | unstructured, 225-250 words | required: 60 words, 1 sentence | Teaching Points: up to 5, 50 words each | 75 | 50 parts, and up to 20 supplemental parts | not read | C | 1 |
| Fundamental / Tutorial | not read | expanded abstract, 500 words | required: 60 words, 1 sentence | Teaching Points: up to 3 | 10 suggested readings | 2 images | not read | C | 1 |
| Update | 1000 | not read | not read | not read | 10 | four figure parts, tables included | four figure parts, tables included | C | 1 |
| Commentary | 1500 | none | not read | not read | 10 | 0 | 0 | C | 1 |
| Editorial | 1500 | none | not read | not read | 10 | 0 | 0 | C | 1 |

Sources of this table:

1. <https://pubs.rsna.org/page/radiographics/rgauthor_instructions> (search-copy, read 2026-11-21)

### Radiology Advances

The journal's instructions: <https://academic.oup.com/radadv/pages/general-instructions>

| Article type | Body words | Abstract | Summary statement | Key points | References | Figures | Tables | How sure | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Original Research | 3000; Materials and Methods 800 | structured, 300 words: Background, Purpose, Materials and Methods, Results, Conclusion | required: 30 words, 1 sentence | Key Results: 3 to 5, 75 words | 35 | 6 figures or 20 figure parts | 4 | B, C, P | 1, 2 |
| Review | 4500 | unstructured, 200 words | required: 30 words, 1 sentence | Essentials: 3 to 5, 75 words | 70 | not read | not read | C | 1 |
| Statements and Guidelines | 4500 | unstructured, 200 words | required: 30 words, 1 sentence | not read | 70 | not read | not read | C | 1 |
| Editorial | 1500 | none | not read | not read | 10 | 1 figure or 3 figure parts | 1 | C | 1 |
| Letter to the Editor and Reply | 350 (the main text) | none | not read | not read | 5 | 0 | 0 | C | 1 |
| Art of Imaging | 20 (the caption) | none | not read | not read | not read | a single image or video | not read | C | 1 |

Sources of this table:

1. <https://academic.oup.com/radadv/pages/general-instructions> (search-copy, read 2026-11-21)
2. <https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc> (measured, read 2026-11-21)

<!-- END limits -->

The same facts, and more (title pages, anonymisation, file types, statements, reporting checklists, what could not be read), each with its address, the date it was read and how it was read, are in [`journals/requirements.json`](journals/requirements.json). That file is the one place where a limit or a required section is written: the skeletons, the drop-down lists of the workflow and the table above are all made from it.

## Check before you submit

The journals change their instructions, and this template was not read from the live pages. Before you submit, open the journal's instructions (the address stands above each table and at the top of your `main.tex`) and check the limits, the title page, the file type the journal takes, and the statements it wants.

## To change the template

- `journals/requirements.json`: the facts. Change a limit here and nowhere else.
- `templates/`: the parts the skeletons are made from. `templates/notes/` holds the writing notes kept from the template this one descends from.
- `python scripts/sync_workflow.py`: after a change to the data or to a template, rewrites the drop-down lists of the workflow, the table above, and `main.tex` and `title_page.tex` as the template ships them (the skeleton of Radiology: Artificial Intelligence, Original Research).
- `python -m pytest tests`: every journal and article type generates, every limit of the data appears in its skeleton, no placeholder is left unfilled, and the three things above are in step with the data.
- `.github/workflows/build.yml`: on every push and pull request, writes and compiles the skeleton of every journal and article type on GitHub's machines. In a repository that has been configured as a manuscript, the same workflow compiles the manuscript alone and makes its HTML copy.

## Credit

This template descends from [cai4cai/RSNATemplate](https://github.com/cai4cai/RSNATemplate), "an attempt at making a latex template to ease submission to RSNA journals". Its style files, its reference style, its route to Microsoft Word and its writing notes are kept.
