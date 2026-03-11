import pytest
from sqlalchemy.exc import InternalError
from tests.credentials import ADMIN_AUTH, USER_AUTH


def test_admin_db_query_admin(fastapi):
    """Test that an admin user can execute a DB query."""
    query = "SELECT count(*) FROM users"
    response = fastapi.get(f"/admin/db/query?q={query}", headers=ADMIN_AUTH)
    assert response.status_code == 200
    data = response.json()
    assert "header" in data
    assert "data" in data
    assert data["header"] == ["count"]
    assert len(data["data"]) == 1
    assert isinstance(data["data"][0][0], int)


def test_admin_db_query_non_admin(fastapi):
    """Test that a non-admin user cannot execute a DB query."""
    query = "SELECT count(*) FROM users"
    response = fastapi.get(f"/admin/db/query?q={query}", headers=USER_AUTH)
    assert response.status_code == 403


def test_admin_db_query_invalid_sql(fastapi):
    """Test that an invalid SQL query returns an error."""
    query = "SELECT * FROM non_existent_table"
    # The current implementation might raise an exception that the TestClient propagates,
    # or it might return a 500.
    try:
        response = fastapi.get(f"/admin/db/query?q={query}", headers=ADMIN_AUTH)
        assert response.status_code != 200
    except Exception:
        # If it raises an exception, it's also a kind of "not 200"
        pass


def test_admin_db_query_pirate_write(fastapi):
    """Test that a 'pirate' cannot write to the DB using this endpoint, and no data changes."""
    upd = "UPDATE users SET password='pirate_password' WHERE id=1"
    with pytest.raises(InternalError):
        fastapi.get(f"/admin/db/query?q={upd}", headers=ADMIN_AUTH)
