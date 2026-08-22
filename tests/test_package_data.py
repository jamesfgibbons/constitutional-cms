"""Packaged data must stay byte-identical to the canonical repository files.

The wheel ships copies of schemas/ and the check catalog inside
constitutional_cms/data/ so a uvx or pip user needs no checkout. The repository
files remain canonical; this test fails the build if the copies drift.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DATA = ROOT / "constitutional_cms" / "data"

PAIRS = [
    ("schemas", PACKAGE_DATA / "schemas", "*.json"),
    ("contracts", PACKAGE_DATA / "catalog", "check_catalog_v1.yaml"),
]


class PackageDataSyncTest(unittest.TestCase):
    def test_packaged_copies_match_canonical_files(self):
        for canonical_dir, packaged_dir, pattern in PAIRS:
            canonical = {path.name: path for path in sorted((ROOT / canonical_dir).glob(pattern))}
            packaged = {path.name: path for path in sorted(packaged_dir.glob(pattern))}
            if pattern == "*.json":
                self.assertEqual(
                    set(canonical), set(packaged),
                    f"package data out of sync with {canonical_dir}/ (file set differs)",
                )
            for name, packaged_path in packaged.items():
                self.assertIn(name, canonical, f"{name} packaged but not canonical")
                self.assertEqual(
                    packaged_path.read_bytes(),
                    canonical[name].read_bytes(),
                    f"{name}: packaged copy differs from {canonical_dir}/{name}; "
                    f"re-copy the canonical file into constitutional_cms/data/",
                )

    def test_catalog_copy_present(self):
        self.assertTrue((PACKAGE_DATA / "catalog" / "check_catalog_v1.yaml").exists())


if __name__ == "__main__":
    unittest.main()
