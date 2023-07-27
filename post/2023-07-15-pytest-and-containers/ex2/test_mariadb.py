def test_simple_select(mariadb_cursor):
    mariadb_cursor.execute("select 1")
    res = mariadb_cursor.fetchone()
    assert res[0] == 1
