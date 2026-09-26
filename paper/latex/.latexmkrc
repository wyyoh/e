# Run from paper/latex: latexmk -xelatex main.tex
# Ready PDFs need neither Python nor plotting dependencies.
my @common_pdfs = map { "figures/common_model/$_.pdf" } qw(
    fig1_1_decision_inheritance fig3_1_terrain_and_demand
    fig3_2_transport_physics figA1_dem_cells
);
if (grep { !-f $_ } @common_pdfs) {
    my $python = $ENV{'PYTHON'} || 'python3';
    if (system($python, 'scripts/build_common_figures.py') != 0) {
        die "Common figure preparation failed. Install the documented dependencies or copy the reviewed PDFs.\n";
    }
}
$pdf_mode = 5;
