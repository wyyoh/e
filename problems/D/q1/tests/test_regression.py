"""Historical comparison only; excluded from optimizer inputs."""
import ast
from model.io import ROOT
from scripts.regression import regression


def test_final_external_regression():
    assert regression(ROOT/'results')['status']=='MATCH'


def test_solver_does_not_import_historical_targets():
    for folder in ('model','solver'):
        for path in (ROOT/folder).glob('*.py'):
            source=path.read_text(encoding='utf-8')
            assert 'regression_targets' not in source
            assert '59.131296' not in source and '59.033942' not in source
