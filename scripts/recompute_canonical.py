"""Fill in missing canonical values (#11). Dry-run by default.

    uv run python -m scripts.recompute_canonical            # report only
    uv run python -m scripts.recompute_canonical --apply    # write

Run it after adding synonyms/conversions, or after an import that wrote observations directly.
"""
from __future__ import annotations

import sys

from core.db import engine
from core.recompute import recompute_canonical


def main() -> None:
    apply = "--apply" in sys.argv
    with engine.begin() as conn:
        rep = recompute_canonical(conn, apply=apply)
    print(f"Rows without a canonical value: {rep.scanned}")
    print(f"{'Updated' if apply else 'Would update'}: {rep.n_fixed}")
    for (code, unit), n in rep.fixed.most_common(15):
        print(f"  {n:6}  {code} [{unit}]")
    if rep.n_unconvertible:
        print(f"Still unconvertible (fix the unit or add a conversion): {rep.n_unconvertible}")
        for (code, unit, cu), n in rep.unconvertible.most_common(15):
            print(f"  {n:6}  {code}: {unit!r} → {cu!r}")
    if not apply and rep.n_fixed:
        print("Dry run — re-run with --apply to write.")


if __name__ == "__main__":
    main()
