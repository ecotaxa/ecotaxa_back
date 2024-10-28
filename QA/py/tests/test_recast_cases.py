"""
Partial test of a class used during DwCA export
"""

from BO.WoRMSification import WoRMSifier


def test_exhaustive_recast_for_EmoF_generation():
    wrmsier = WoRMSifier()
    wrmsier.phylo2worms = {}
    wrmsier.morpho2phylo = {
        84974: 83278,
        84975: 83278,
        92012: 83278,
        92107: 90386,
        92108: 90386,
        92109: 90386,
    }
    recast = {
        83278: 72398,
        84975: 72398,
        92012: 72398,
        92107: 72398,
        92108: 72398,
        92231: 56789,
        92873: 56789,
    }
    wrmsier.apply_recast(recast)
    # No rule source should appear as a target
    left = set(wrmsier.morpho2phylo.values()).intersection(recast.keys())
    assert len(left) == 0, f"Recast rule source still in m2p target :{left}"
    assert wrmsier.morpho2phylo == {
        83278: 72398,
        84974: 72398,
        84975: 72398,
        92012: 72398,
        92107: 72398,
        92108: 72398,
        92109: 90386,
        92231: 56789,
        92873: 56789,
    }


def test_implied_recast_for_EmoF_generation():
    wrmsier = WoRMSifier()
    wrmsier.phylo2worms = {}
    wrmsier.morpho2phylo = {
        84974: 83278,
        84975: 83278,
        92012: 83278,
        92107: 90386,
        92108: 90386,
        92109: 90386,
    }
    recast = {
        83278: 72398,
        # 84975: 72398, Should be applied rule #1 above
        # 92012: 72398, Should be applied rule #1 above
        92107: 83278,  # Chain of rules
        92108: 92107,
        92231: 56789,
        92873: 56789,
    }
    wrmsier.apply_recast(recast)
    # No rule source should appear as a target
    left = set(wrmsier.morpho2phylo.values()).intersection(recast.keys())
    assert len(left) == 0, f"Recast rule source still in m2p target :{left}"
    assert wrmsier.morpho2phylo == {
        83278: 72398,
        84974: 72398,
        84975: 72398,
        92012: 72398,
        92107: 72398,
        92108: 72398,
        92109: 90386,
        92231: 56789,
        92873: 56789,
    }
