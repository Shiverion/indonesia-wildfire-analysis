"""Freeze local provenance for peat and drainage sensitivity inputs.

This command records byte hashes and source limitations only.  It does not
promote either layer to a primary exposure or unlock Phase 1/2.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PEAT = ROOT / "data/raw/peat/global/peatland.extent_multi_p_1km_s_2000_2020_go_epsg4326_v20260423.tif"
DRAINAGE = ROOT / "data/raw/peat_and_drainage/dadap_2017_geotiffs.zip"
OUT = ROOT / "outputs/quality/peat_sensitivity_provenance.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in (PEAT, DRAINAGE) if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing sensitivity input(s): " + ", ".join(missing))
    with zipfile.ZipFile(DRAINAGE) as archive:
        member_count = len(archive.infolist())
    payload = {
        "schema_version": "peat-sensitivity-provenance/v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary_phase1_ready": False,
        "phase2_unlock": False,
        "assets": {
            "peat_baseline": {
                "path": PEAT.relative_to(ROOT).as_posix(),
                "sha256": sha256(PEAT),
                "source_url": "https://zenodo.org/records/19731872",
                "license": "CC-BY-4.0",
                "release_date": "2026-04-24",
                "reference_period": "2000-2020",
                "role": "static sensitivity stratum; not 2026 land cover",
            },
            "drainage_sensitivity": {
                "path": DRAINAGE.relative_to(ROOT).as_posix(),
                "sha256": sha256(DRAINAGE),
                "member_count": member_count,
                "source_url": "https://purl.stanford.edu/yj761xk5815",
                "license": "CC-BY-3.0",
                "source_reference_year": 2017,
                "role": "canal/road sensitivity; not a dated 2014 construction series",
            },
        },
        "interpretation": "These files support sensitivity and provenance checks only; they do not establish peat vulnerability or a causal effect.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))
        # Keep an existing freeze immutable apart from the retrieval timestamp.
        if {key: value for key, value in existing.items() if key != "recorded_at_utc"} != {key: value for key, value in payload.items() if key != "recorded_at_utc"}:
            raise RuntimeError(f"Refusing to overwrite changed provenance lock: {OUT}")
        payload["recorded_at_utc"] = existing.get("recorded_at_utc", payload["recorded_at_utc"])
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote immutable peat sensitivity provenance: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
