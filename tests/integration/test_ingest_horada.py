"""
End-to-end ingestion tests for the two real Ministry ZIPs we have on disk.

These tests load `Horada (3).zip` (muni 10406544 / 2026-03) and
`Horada (2).zip` (muni 10406544 / 2026-02) through FileParser.parse_zip
and assert the key invariants:

  * total breakdown amount matches the known CHESHBONIT gap
  * retro amount matches the sum of rows whose period differs from file month
  * breakdown row count is above a sentinel (detail files stayed wired)
  * Horada(3) has zero opaque CHESHBONIT rows — Phase 1 additive tie-out
    closes every code
  * Horada(2) has the expected residual opaque rows (no YADANIIM in the
    Feb ZIP → 15 codes fall through to CHESHBONIT)
  * Phase 2 formula-input tables are populated (class enrollments, staff
    positions, transport routes) with the counts we verified live.

Locks in Phase 1 + Phase 2 improvements — if someone regresses the
parser, these tests flip red immediately.
"""
from __future__ import annotations

import os
import pytest

from backend.services import FileParser


UPLOADS = "/sessions/brave-affectionate-darwin/mnt/cpa/uploads"

HORADA_3 = os.path.join(UPLOADS, "20260403_005517_Horada (3).zip")
HORADA_2 = os.path.join(UPLOADS, "20260417_163829_20260417_161841_Horada (2).zip")


AGORA = 0.01  # 1 agora tolerance (shekel = 100 agorot)


# ─── Horada (3).zip — 2026-03 — every code has detail ──────────────────────

@pytest.mark.skipif(not os.path.exists(HORADA_3), reason="Horada (3).zip not present")
class TestHorada3March2026:
    """March 2026 ZIP — full Phase 1+2 coverage, zero opaque."""

    @pytest.fixture(scope="class")
    def parsed(self):
        return FileParser.parse_zip(HORADA_3)

    def test_municipality_detected(self, parsed):
        assert parsed["municipalities"] == {10406544}

    def test_invoice_row_present(self, parsed):
        inv = parsed["invoice_df"]
        assert len(inv) == 1
        assert int(inv["municipality_code"].iloc[0]) == 10406544

    def test_breakdown_row_count(self, parsed):
        # Sentinel: if detail files unwire, this falls below 3000
        bd = parsed["breakdown_df"]
        assert len(bd) == 4951, (
            f"Expected 4951 breakdown rows, got {len(bd)} — "
            "a detail/aux file may have unwired"
        )

    def test_breakdown_total_ties_to_cheshbonit_gap(self, parsed):
        # CHESHBONIT total gap for 2026-03 is ₪4,702,530.10
        bd = parsed["breakdown_df"]
        total = bd["amount"].sum()
        assert abs(total - 4_702_530.10) < AGORA, (
            f"Breakdown total {total:,.2f} ≠ expected 4,702,530.10"
        )

    def test_retro_total(self, parsed):
        bd = parsed["breakdown_df"]
        retro = bd[bd["is_retro"]]["amount"].sum()
        assert abs(retro - 66_026.15) < AGORA, (
            f"Retro total {retro:,.2f} ≠ expected 66,026.15"
        )

    def test_zero_opaque_cheshbonit_rows(self, parsed):
        """Phase 1 invariant: every CHESHBONIT code resolves to detail/aux."""
        bd = parsed["breakdown_df"]
        opaque = bd[bd["line_type"] == "cheshbonit"]
        assert len(opaque) == 0, (
            f"{len(opaque)} opaque CHESHBONIT rows remain — "
            "detail/aux files aren't tying out"
        )

    def test_all_line_types_present(self, parsed):
        """Both Phase 1 aux types (yadaniim, moadon, sacal) should appear."""
        bd = parsed["breakdown_df"]
        types = set(bd["line_type"].unique())
        expected = {"gy", "hasaot", "moadon", "mucarim", "mutavim",
                    "sacal", "sharatim", "shefi", "yadaniim"}
        missing = expected - types
        assert not missing, f"Missing line types: {missing}"

    def test_phase2_formula_inputs_populated(self, parsed):
        fi = parsed.get("formula_inputs", {})
        assert fi.get("class_enrollments") is not None
        assert len(fi["class_enrollments"]) == 84

        assert fi.get("transport_routes") is not None
        assert len(fi["transport_routes"]) == 280

        assert fi.get("staff_positions_institution") is not None
        assert len(fi["staff_positions_institution"]) == 685

        assert fi.get("staff_positions_gy") is not None
        assert len(fi["staff_positions_gy"]) == 56

    def test_per_line_type_row_counts(self, parsed):
        """Per-file row counts — sentinels for each detail/aux file."""
        bd = parsed["breakdown_df"]
        counts = bd["line_type"].value_counts().to_dict()
        # Give a little slack on mucarim because it's huge and noisy (the
        # ministry occasionally re-issues some rows); others are tight.
        assert counts.get("sacal") == 930
        assert counts.get("sharatim") == 532
        assert counts.get("mutavim") == 95
        assert counts.get("gy") == 56
        assert counts.get("shefi") == 43
        assert counts.get("hasaot") == 29
        assert counts.get("moadon") == 19
        assert counts.get("yadaniim") == 2
        assert counts.get("mucarim", 0) > 3000


# ─── Horada (2).zip — 2026-02 — no YADANIIM → 15 opaque codes ──────────────

@pytest.mark.skipif(not os.path.exists(HORADA_2), reason="Horada (2).zip not present")
class TestHorada2Feb2026:
    """February 2026 ZIP — Phase 1 coverage minus YADANIIM (file absent)."""

    @pytest.fixture(scope="class")
    def parsed(self):
        return FileParser.parse_zip(HORADA_2)

    def test_municipality_detected(self, parsed):
        assert parsed["municipalities"] == {10406544}

    def test_breakdown_row_count(self, parsed):
        bd = parsed["breakdown_df"]
        assert len(bd) == 4806, (
            f"Expected 4806 breakdown rows, got {len(bd)}"
        )

    def test_breakdown_total_ties_to_cheshbonit_gap(self, parsed):
        bd = parsed["breakdown_df"]
        total = bd["amount"].sum()
        assert abs(total - 4_312_375.29) < AGORA, (
            f"Breakdown total {total:,.2f} ≠ expected 4,312,375.29"
        )

    def test_retro_total(self, parsed):
        bd = parsed["breakdown_df"]
        retro = bd[bd["is_retro"]]["amount"].sum()
        # Feb retro is negative (reversed prior-period adjustments)
        assert abs(retro - (-104_801.28)) < AGORA, (
            f"Retro total {retro:,.2f} ≠ expected -104,801.28"
        )

    def test_opaque_cheshbonit_is_feb_known_gap(self, parsed):
        """Feb has no YADANIIM so ~15 CHESHBONIT codes remain opaque.
        This is a known source-data limitation, not a parser bug.
        The count is pinned so if the ministry ships YADANIIM next Feb
        and we close more codes, the test reminds us to lower the cap."""
        bd = parsed["breakdown_df"]
        opaque = bd[bd["line_type"] == "cheshbonit"]
        assert len(opaque) == 15, (
            f"Feb opaque count changed: got {len(opaque)}, was 15. "
            "If the Ministry started shipping YADANIIM, lower this cap."
        )

    def test_line_types_no_yadaniim(self, parsed):
        """Feb ZIP lacks YADANIIM, so that line_type should not appear."""
        bd = parsed["breakdown_df"]
        types = set(bd["line_type"].unique())
        assert "yadaniim" not in types, (
            "Feb ZIP doesn't have YADANIIM file — line type should be absent"
        )
        # Everything else should be there
        for expected in ("gy", "mucarim", "mutavim", "sharatim", "shefi",
                         "hasaot", "sacal", "moadon", "cheshbonit"):
            assert expected in types, f"Missing line_type {expected}"

    def test_phase2_formula_inputs_populated(self, parsed):
        fi = parsed.get("formula_inputs", {})
        # Enrollments is same file content (school-year scoped), so same count
        assert len(fi["class_enrollments"]) == 84
        assert len(fi["transport_routes"]) == 280
        # Feb reports fewer staff positions than March (staff onboarded
        # during the school year → count grows month-over-month)
        assert len(fi["staff_positions_institution"]) == 510
        assert len(fi["staff_positions_gy"]) == 42


# ─── Cross-ZIP sanity: staff grows through the school year ─────────────────

@pytest.mark.skipif(
    not (os.path.exists(HORADA_2) and os.path.exists(HORADA_3)),
    reason="both Horada ZIPs needed for cross-zip invariant",
)
def test_staff_positions_grow_between_feb_and_march():
    """Sanity: March should have ≥ February staff positions (people don't
    usually un-onboard mid-year)."""
    feb = FileParser.parse_zip(HORADA_2)
    mar = FileParser.parse_zip(HORADA_3)

    feb_inst = len(feb["formula_inputs"]["staff_positions_institution"])
    mar_inst = len(mar["formula_inputs"]["staff_positions_institution"])
    assert mar_inst >= feb_inst, (
        f"March ({mar_inst}) has fewer institution staff rows than "
        f"Feb ({feb_inst}) — unexpected"
    )
