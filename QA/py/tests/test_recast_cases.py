"""
Partial test of a class used during DwCA export
"""

from BO.WoRMSification import WoRMSifier


def test_exhaustive_recast_for_EmoF_generation():
    recast = {
        83278: 72398,
        84975: 72398,
        92012: 72398,
        92107: 92108,
        92108: 72398,
        92231: 92232,
        92232: 56789,
        92873: 56789,
    }
    recasted = WoRMSifier.apply_recast(recast)
    # No rule source should appear as a target
    left = set(recasted.values()).intersection(recast.keys())
    assert len(left) == 0, f"Recast rule source still in m2p target :{left}"
    assert recasted == {
        83278: 72398,
        84975: 72398,
        92012: 72398,
        92107: 72398,
        92108: 72398,
        92231: 56789,
        92232: 56789,
        92873: 56789,
    }
