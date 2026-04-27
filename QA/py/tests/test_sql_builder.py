from DB.helpers.SQL import *


def test_sql_wrap():
    where = WhereClause()
    where *= "obh.classif_id = any (:taxo)"
    where *= "obh.latitude between :MapS and :MapN"
    where *= "obh.n57 >= :freenumst"
    where *= "obh.n57 >= obh.n56"
    where *= "obf.orig_id = :img"
    assert list(where.conds_and_refs()) == [
        ("obh.classif_id = any (:taxo)", {"obh.classif_id"}),
        ("obh.latitude between :MapS and :MapN", {"obh.latitude"}),
        ("obh.n57 >= :freenumst", {"obh.n57"}),
        ("obh.n57 >= obh.n56", {"obh.n56", "obh.n57"}),
        ("obf.orig_id = :img", {"obf.orig_id"}),
    ]


def test_select_clause():
    select = SelectClause()
    select.add_expr("obh.id")
    select.add_expr("obh.name", "o_name")
    assert select.get_sql() == "SELECT obh.id, obh.name AS o_name"


def test_select_clause_refs():
    select = SelectClause()
    select.add_expr("obh.id")
    select.add_expr("obj.name")
    assert select.table_refs() == {"obh", "obj"}


def test_select_clause_transfer():
    source = SelectClause()
    source.add_expr("obh.id")
    source.add_expr("obj.name", "o_name")
    source.add_expr("img.width")

    target = SelectClause()

    SelectClause.transfer(source, target, "obh")

    assert target.expressions == ["obh.id"]
    assert target.aliases == [None]

    assert source.expressions == ["obj.name", "img.width"]
    assert source.aliases == ["o_name", None]


def test_select_clause_complex_refs():
    select = SelectClause()
    expressions = [
        "obh.objid",
        "acq.acquisid",
        "sam.sampleid",
        "0 AS total",
        "obh.objid",
        "obh.classif_qual",
        "(SELECT COUNT(img2.imgrank) FROM images img2 WHERE img2.objid = obh.objid) AS imgcount",
        "obh.complement_info",
        "img.height",
        "img.width",
        "(img.thumb_height,img.imgid) AS thumb_file_name",
        "img.thumb_height",
        "img.thumb_width",
        "(img.imgid,img.orig_file_name) AS file_name",
        "txo.name",
        "txo.display_name",
        "txo.taxostatus",
        "obf.n06",
    ]
    for expr in expressions:
        select.add_expr(expr)

    assert select.table_refs() == {"obh", "acq", "sam", "img2", "img", "txo", "obf"}


def test_order_clause_refs():
    order = OrderClause()
    order.add_expression("obh", "id", "DESC")
    order.add_expression("obj", "name", "ASC")
    assert order.table_refs() == {"obh", "obj"}


def test_from_clause():
    from_clause = FromClause("table1")
    from_clause += "table2 ON table1.id = table2.id"
    from_clause += "table3 ON table1.id = table3.id"

    assert (
        from_clause.get_sql()
        == "table1\n JOIN table2 ON table1.id = table2.id\n JOIN table3 ON table1.id = table3.id"
    )

    from_clause.set_outer("table2")
    assert "LEFT JOIN table2 ON table1.id = table2.id" in from_clause.get_sql()

    from_clause.set_lateral("table3")
    assert "JOIN LATERAL table3 ON table1.id = table3.id" in from_clause.get_sql()


def test_from_clause_refs():
    from_clause = FromClause("table1")
    from_clause += "table2 AS t2 ON table1.id = t2.id"
    from_clause += "(SELECT * FROM table3) AS t3 ON table1.id = t3.id"

    assert from_clause.table_refs() == ["table1", "t2", "t3"]


def test_from_clause_refs_tricky():
    from_clause = FromClause("table1")
    from_clause += "(SELECT * FROM table4) t4 ON table1.id = t4.id"

    # Check if t4 is correctly identified as an alias
    assert "t4" in from_clause.table_refs()


def test_from_clause_refs_tricky_no_on():
    from_clause = FromClause("table1")
    from_clause += "(SELECT * FROM table5) t5"

    # Check if t5 is correctly identified as an alias
    assert "t5" in from_clause.table_refs()


def test_from_clause_refs_tricky_on_true():
    from_clause = FromClause("table1")
    from_clause += "(SELECT * FROM table5) t5 on True"

    # Check if t5 is correctly identified as an alias
    assert "t5" in from_clause.table_refs()


def test_from_clause_transfer_lateral_and_outer():
    source = FromClause("table1")
    source += "table2 AS t2 ON table1.id = t2.id"
    source += "table3 AS t3 ON table1.id = t3.id"
    source.set_outer("table2")
    source.set_lateral("table3")

    assert "LEFT JOIN" in source.get_sql()
    assert "JOIN LATERAL" in source.get_sql()

    target = FromClause("other_table")

    # Transfer both
    FromClause.transfer(source, target, "t2")
    FromClause.transfer(source, target, "t3")

    target_sql = target.get_sql()
    assert "LEFT JOIN table2 AS t2 ON table1.id = t2.id" in target_sql
    assert "JOIN LATERAL table3 AS t3 ON table1.id = t3.id" in target_sql

    # Ensure source no longer has them
    assert "LEFT JOIN" not in source.get_sql()
    assert "JOIN LATERAL" not in source.get_sql()


def test_from_clause_transfer_lateral_issue():
    # Scenario: The user adds a join that already starts with LATERAL, and marks it as lateral.
    # This leads to double LATERAL in the output.
    source = FromClause("table1")
    source += "LATERAL (SELECT * FROM table2) t2"
    source.set_lateral("LATERAL")

    # We want to see if this is preserved in transfer
    target = FromClause("other_table")
    FromClause.transfer(source, target, "table2")

    assert "LATERAL LATERAL" not in target.get_sql()


def test_lateral_loss_after_replace():
    source = FromClause("table1")
    source += "(SELECT * FROM table2) t2"
    source.set_lateral("(SELECT")

    # Verify lateral
    assert "JOIN LATERAL" in source.get_sql()

    # Replace table2 with table3
    source.replace_table("table2", "table3")

    # Verify lateral is lost!
    assert "JOIN LATERAL" in source.get_sql(), "LATERAL was lost!"


def test_from_clause_transfer_lateral_proper():
    # Scenario: User adds a join, marks it lateral properly.
    source = FromClause("table1")
    source += "(SELECT * FROM table2) t2"
    source.set_lateral("(SELECT")

    # Check if get_sql produces correct lateral
    assert "JOIN LATERAL (SELECT * FROM table2) t2" in source.get_sql()

    # Transfer
    target = FromClause("other_table")
    FromClause.transfer(source, target, "t2")

    # Verify lateral is transferred
    target_sql = target.get_sql()
    assert "JOIN LATERAL (SELECT * FROM table2) t2" in target_sql


def test_from_clause_transfer_lateral_loss_after_replace_2():
    # Scenario: User adds a join, marks it lateral, then modifies the join string.
    # The lateral status should be preserved.
    source = FromClause("table1")
    source += "table2 JOIN other"
    source.set_lateral("table2")

    # Verify lateral
    assert "JOIN LATERAL table2 JOIN other" in source.get_sql()

    # Replace table2 with table3
    # This will search for "table2 "
    source.replace_table("table2", "table3")

    # Verify lateral is still there
    sql = source.get_sql()
    assert "JOIN LATERAL table3 JOIN other" in sql, "LATERAL lost in source after replace!"

    # Transfer
    target = FromClause("other_table")
    FromClause.transfer(source, target, "other")

    # Verify lateral is transferred
    target_sql = target.get_sql()
    assert "JOIN LATERAL table3 JOIN other" in target_sql, "LATERAL was lost in transfer!"


def test_from_clause_transfer_lateral_loss_after_replace():
    # Scenario: User adds a join, marks it lateral, then modifies the join string.
    # The lateral status should be preserved.
    source = FromClause("table1")
    source += "table2"
    source.set_lateral("table2")

    # Verify lateral
    assert "JOIN LATERAL table2" in source.get_sql()

    # Replace table2 with table3
    source.replace_table("table2", "table3")

    # Transfer
    target = FromClause("other_table")
    FromClause.transfer(source, target, "table3")

    # Verify lateral is transferred
    target_sql = target.get_sql()
    assert "JOIN LATERAL table3" in target_sql, "LATERAL was lost in transfer!"


def test_from_clause_transfer_lateral_loss():
    # Scenario: User adds a join, marks it lateral properly.
    source = FromClause("table1")
    source += "(SELECT * FROM table2) t2"
    source.set_lateral("(SELECT")

    # Verify lateral
    assert "JOIN LATERAL" in source.get_sql()

    # Transfer
    target = FromClause("other_table")
    FromClause.transfer(source, target, "t2")

    # Verify lateral is transferred
    target_sql = target.get_sql()
    assert "JOIN LATERAL" in target_sql, "LATERAL was lost in transfer!"


def test_from_clause_transfer_lateral():
    source = FromClause("table1")
    source += "LATERAL (SELECT * FROM table2) t2"
    source.set_lateral("LATERAL")

    # Verify lateral join is set
    assert "LATERAL (SELECT * FROM table2) t2" in source.get_sql()

    target = FromClause("other_table")

    # Transfer the lateral join
    FromClause.transfer(source, target, "t2")

    # Verify the lateral join is present in target
    assert "LATERAL (SELECT * FROM table2) t2" in target.get_sql()
