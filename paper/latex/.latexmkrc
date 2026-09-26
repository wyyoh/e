# Run from paper/latex: latexmk -xelatex main.tex
# Existing PDFs are used directly; the script does not install packages or run solvers.
my $python = $ENV{'PYTHON'} || 'python3';
if (system($python, 'scripts/build_common_figures.py') != 0) {
    die "Common figure preparation failed. See scripts/build_common_figures.py or copy the reviewed PDFs.\n";
}
$pdf_mode = 5;
