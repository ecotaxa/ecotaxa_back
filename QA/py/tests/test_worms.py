import logging

import pytest


def test_worms_xlsx(config, database):
    from data.ToWorms import ToWorms

    to_worms = ToWorms()
    to_worms.pre_validate()
    to_worms.prepare()
    to_worms.validate_with_trees()
    to_worms.show_stats()
    to_worms.apply()
    to_worms.check_ancestors()
    to_worms.check_closure()
    to_worms.check_sums()
