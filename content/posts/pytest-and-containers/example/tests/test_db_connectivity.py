from sqlalchemy import text


def test_db_connect(mariadb_connection):
    res = mariadb_connection.execute(text("select 1"))
    assert res.fetchall() == [(1,)]
