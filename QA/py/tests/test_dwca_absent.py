#
# Absent occurrences computation in DwCA export, no DB needed.
#
from types import SimpleNamespace

from API_operations.exports.DarwinCore import DarwinCoreExport
from BO.Sample import SampleAggregForTaxon


def _worms(aphia_id: int):
    return SimpleNamespace(aphia_id=aphia_id, name="t%d" % aphia_id)


def _aggreg(occ_id: str, taxo_id: int, aphia_id: int):
    return {
        str(aphia_id): (
            occ_id,
            SampleAggregForTaxon(taxo_id, 1, None, None),
            _worms(aphia_id),
        )
    }


def _absents(samples):
    presence = ({}, {}, {})
    for event_id, written in samples:
        DarwinCoreExport.note_present_occurrences(event_id, written, presence)
    warnings = []
    ret = DarwinCoreExport.compute_absent_occurrences(presence, warnings)
    return {(evt, occ_id, worms.aphia_id) for evt, occ_id, worms in ret}, warnings


def test_absent_not_issued_for_emof_covered_taxon():
    # Sample A: 12873 is kept in occurrence space, but recast to 11509 in eMoF space,
    # so a 'present' record A_11509 is issued for eMoF coverage.
    # Sample B: 11509 directly present.
    absents, warnings = _absents(
        [
            (
                "A",
                (
                    _aggreg("A_12873", 12873, 99),
                    {},
                    _aggreg("A_11509", 11509, 1806),
                ),
            ),
            ("B", (_aggreg("B_11509", 11509, 1806), {}, {})),
        ]
    )
    # Before fix, ("A", "A_11509", 1806) was produced, duplicating the 'present' one
    assert absents == {("B", "B_12873", 99)}
    assert warnings == []


def test_absent_per_worms_taxon_not_per_ecotaxa_taxon():
    # Two EcoTaxa taxa mapping to same WoRMS taxon in different samples
    absents, _ = _absents(
        [
            ("A", (_aggreg("A_92230_72396", 92230, 135338), {}, {})),
            ("B", (_aggreg("B_72396", 72396, 135338), {}, {})),
            ("C", (_aggreg("C_5", 5, 1), {}, {})),
        ]
    )
    # 135338 is present in A and B, so never absent there, whatever the EcoTaxa ID
    assert absents == {
        ("A", "A_5", 1),
        ("B", "B_5", 1),
        ("C", "C_92230", 135338),
    }


def test_absent_id_collision_is_skipped():
    # Pathological: an occurrence ID already written for another WoRMS taxon
    absents, warnings = _absents(
        [
            ("A", (_aggreg("A_7", 8, 80), {}, {})),
            ("B", (_aggreg("B_7", 7, 70), {}, {})),
        ]
    )
    assert ("A", "A_7", 70) not in absents
    assert len(warnings) == 1
