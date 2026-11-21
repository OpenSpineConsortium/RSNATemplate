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

# The HTML copy of the manuscript, made through lwarp after the PDF, to open in Microsoft
# Word. It takes several more runs of LuaLaTeX at every build (about as long again as the
# PDF itself), so it is made only when it is asked for:
#   on a laptop   RSNA_HTML=1 latexmk       (in PowerShell: $env:RSNA_HTML=1; latexmk)
#   in Overleaf   no environment variable can be set there: change the 0 below to 1
#   on GitHub     the job "HTML copy for Microsoft Word" asks for it by itself
# RSNA_HTML=0 builds the PDFs alone, whatever the line below says.
our $rsna_html = 0;

END {
  my $build = $?;  # the result of the PDF build: the HTML steps below must not replace it
  my $html_copy = $rsna_html;
  if (defined $ENV{RSNA_HTML} && $ENV{RSNA_HTML} ne '') {
    $html_copy = $ENV{RSNA_HTML} !~ /^(0|no|false|off)$/i;
  }
  if ($html_copy) {
    # Every program is called with its arguments as a list, so that no shell stands in
    # between: the same lines run on Linux, macOS and Windows.
    local $| = 1;  # each progress line is printed before the program it announces
    print "Running pdftosvg\n";
    system('lwarpmk', 'pdftosvg', glob('*.pdf'));
    for my $pass (1, 2) {
      print "Running lwarpmk html\n";
      system('lwarpmk', 'html');
    }
    # Written for Overleaf, which builds under the name output. Elsewhere it finds nothing.
    print "Running biber\n";
    system('biber', 'output');
    # The references and the list of abbreviations of the HTML copy. lwarp builds that copy
    # under the name of the document followed by _html: main_html on a laptop and on GitHub.
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
    for my $pass (1, 2) {
      print "Running lwarpmk html1\n";
      system('lwarpmk', 'html1');
    }
    # pandoc doesn't work very well here. Best to open ht ehtml in MS Word directly
    # system('command -v pandoc > /dev/null 2>&1 && { echo "Running pandoc"; pandoc -s main.html -o main.docx; } || { echo "pandoc not found";}');
  }
  $? = $build;
}
