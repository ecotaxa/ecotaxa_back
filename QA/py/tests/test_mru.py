from BO.User import UserBO


def test_mru():
    # Basic addition
    before = [2, 4, 6, 7]
    new = [8, 9, 9]
    after = UserBO.merge_mru(before, new)
    assert after == [9, 8, 2, 4, 6, 7]
    # Already there
    before = [8, 9, 2, 4, 6, 7]
    new = [8, 9, 9]
    after = UserBO.merge_mru(before, new)
    assert after == [9, 8, 2, 4, 6, 7]
    # Already there further
    before = [8, 9, 2, 4, 6, 7]
    new = [8, 9, 9, 7]
    after = UserBO.merge_mru(before, new)
    assert after == [7, 9, 8, 2, 4, 6]
    # Over the limit
    before = [8, 9, 2, 4, 6, 7]
    new = [10, 11, 12, 13, 14, 17, 19]
    after = UserBO.merge_mru(before, new)
    assert after == [19, 17, 14, 13, 12, 11, 10, 8, 9, 2]
