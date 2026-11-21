# Always create PDFs and set default engine to LuaLaTeX.
$pdf_mode = 4;

# "latexmk" with no file name builds the manuscript and the full title page.
@default_files = ('main.tex', 'title_page.tex');

# The list of abbreviations (glossaries package) is made by makeglossaries between two
# runs of LuaLaTeX. Overleaf does this by itself; a laptop has to be told.
add_cus_dep('acn', 'acr', 0, 'rsna_makeglossaries');
add_cus_dep('glo', 'gls', 0, 'rsna_makeglossaries');
$clean_ext .= ' acr acn alg glo gls glg ist';
sub rsna_makeglossaries {
  my ($base_name, $path) = fileparse($_[0]);
  pushd $path;
  my $return = system 'makeglossaries', $base_name;
  popd;
  return $return;
}

# After the PDF: an HTML copy of the manuscript, made through lwarp, to open in Microsoft Word.
# Set the environment variable RSNA_PDF_ONLY=1 to skip it and build the PDFs alone.
END {
  my $build = $?;  # the result of the PDF build: the HTML steps below must not replace it
  unless ($ENV{RSNA_PDF_ONLY}) {
    system('echo "Running pdftosvg"; lwarpmk pdftosvg *.pdf');
    system('echo "Running lwarpmk"; lwarpmk html');
    system('echo "Running lwarpmk"; lwarpmk html');
    system('echo "Running biber"; biber output');
    # The references and the list of abbreviations of the HTML copy. lwarp builds that copy
    # under the name of the document followed by _html: main_html on a laptop and on GitHub,
    # where the line above (written for Overleaf's name, output) finds nothing.
    my $html = 'main_html';
    if (open(my $conf, '<', 'lwarpmk.conf')) {
      while (my $line = <$conf>) {
        $html = $1 . '_html' if $line =~ /^sourcename = \[\[(.+)\]\]/;
      }
      close($conf);
    }
    print "Running biber and makeglossaries for $html\n";
    system('biber', $html);
    system('lwarpmk', 'htmlglossary');
    system('echo "Running lwarpmk"; lwarpmk html1');
    system('echo "Running lwarpmk"; lwarpmk html1');
    # pandoc doesn't work very well here. Best to open ht ehtml in MS Word directly
    # system('command -v pandoc > /dev/null 2>&1 && { echo "Running pandoc"; pandoc -s main.html -o main.docx; } || { echo "pandoc not found";}');
  }
  $? = $build;
}
