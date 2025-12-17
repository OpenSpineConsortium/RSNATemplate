# Always create PDFs and set default engine to LuaLaTeX.
$pdf_mode = 4;

END {
  system('echo "Running pdftosvg"; lwarpmk pdftosvg *.pdf');
  system('echo "Running lwarpmk"; lwarpmk html');
  system('echo "Running lwarpmk"; lwarpmk html');
  system('echo "Running biber"; biber output');
  system('echo "Running lwarpmk"; lwarpmk html1');
  system('echo "Running lwarpmk"; lwarpmk html1');
  # pandoc doesn't work very well here. Best to open ht ehtml in MS Word directly
  # system('command -v pandoc > /dev/null 2>&1 && { echo "Running pandoc"; pandoc -s main.html -o main.docx; } || { echo "pandoc not found";}');
}