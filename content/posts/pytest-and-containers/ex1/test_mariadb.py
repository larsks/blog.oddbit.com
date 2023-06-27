import mysql.connector


def test_simple_select(mariadb_container):
    # get the address of the mariadb container
    mariadb_container.reload()
    addr = mariadb_container.attrs["NetworkSettings"]["Networks"]["bridge"]["IPAddress"]

    # create a connection objects
    conn = mysql.connector.connect(
        host=addr, user="root", password="secret", database="testdb"
    )

    # try a simple select statement
    curs = conn.cursor()
    curs.execute("select 1")
    res = curs.fetchone()
    assert res[0] == 1
