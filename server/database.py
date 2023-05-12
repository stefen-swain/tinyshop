import sqlite3

import queries

def get_list(set):

    return [element.decode('utf-8') for element in set.split(b';')]

def get_connection(database_filename):
    
    sqlite3.register_converter("list", get_list)

    connection = sqlite3.connect(database_filename, timeout=10, detect_types=sqlite3.PARSE_COLNAMES)

    connection.execute(queries.wal)

    connection.row_factory = sqlite3.Row

    return connection
