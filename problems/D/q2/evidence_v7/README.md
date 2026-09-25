# Q2-EVIDENCE-V7-FOCUSED

## Final status

**5433.956428 <= T* <= 5693.231490 seconds** under the V6 fixed numerical model.
The original 23-sortie zero-tardiness incumbent is unchanged. UB-normalized interval: 4.554093092%.
**The intended material breakthrough was NOT achieved. Further proof search is stopped.**

This package includes successful and unsuccessful experiments. Read `RESULTS_中文说明.md` before interpreting bounds. Only `results/status.json` is the release summary.

## Verify (does not resume optimization)

Requires Python 3.10+, NumPy/SciPy, g++ with C++17.

```bash
python -m pip install -r requirements.lock.txt
python code/check_package.py
python -m unittest discover -s tests -v
python code/verify_v7.py --out audit_new --workers 4
```

Global optimality, complete original C=5 infeasibility, and a sub-4% gap are NOT claimed.
No input DEM extraction, no new incumbent, no edits to Q1/Q3/Q4.
