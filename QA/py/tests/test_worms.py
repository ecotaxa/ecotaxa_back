import logging

import pytest
from API_operations.helpers.Service import Service


def test_worms_xlsx(database):
    from data.ToWorms import ToWorms

    with Service() as sce:
        to_worms = ToWorms(sce.session)
        to_worms.pre_validate()
        to_worms.prepare()
        to_worms.validate_with_trees()
        to_worms.show_stats()
        to_worms.apply()
        to_worms.check_ancestors()
        to_worms.check_closure()
        to_worms.check_sums()
