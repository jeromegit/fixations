import sqlite3
import sys
from datetime import datetime
from sqlite3 import Error

from fixations.fix_utils import get_store_path
from fixations.short_str_id import get_short_str_id


class Store:
    conn = None
    curs = None

    TABLE_NAME = 'str_id_to_lines'

    def __init__(self, store_path) -> None:
        try:
            self.conn = sqlite3.connect(store_path, check_same_thread=False)
        except Error as e:
            print(f"ERROR: creating sqlite3 db with path:{store_path} with exception:{e}. Using in-memory db instead")
            self.conn = sqlite3.connect(':memory:')

        self.curs = self.conn.cursor()
        self.conn.row_factory = sqlite3.Row

        self.conn.execute(f'''CREATE TABLE IF NOT EXISTS {Store.TABLE_NAME} (
         str_id    TEXT NOT NULL PRIMARY KEY,
         lines TEXT NOT NULL,
         timestamp TEXT NOT NULL);''')

    def save(self, str_id, lines):
        now_timestamp = str(datetime.now())
        if self.str_id_already_exists(str_id):
            self.conn.execute(f"UPDATE {self.TABLE_NAME} SET lines=?, timestamp=? WHERE str_id = ?",
                              (lines, now_timestamp, str_id))
        else:
            self.conn.execute(f"INSERT INTO {self.TABLE_NAME} (str_id, lines, timestamp) VALUES (?, ?, ?)",
                              (str_id, lines, now_timestamp))
        self.conn.commit()

    def get(self, str_id):
        self.curs.execute(f"SELECT lines, timestamp FROM {self.TABLE_NAME} WHERE str_id = ?", (str_id,))
        rows = self.curs.fetchall()
        if len(rows) == 1:
            return rows[0]
        else:
            print(f"ERROR: not data found for str_id:{str_id}")
            return None, None

    def str_id_already_exists(self, str_id):
        self.curs.execute(f"SELECT str_id FROM {self.TABLE_NAME} WHERE str_id = ?", (str_id,))
        rows = self.curs.fetchall()

        return len(rows) == 1


def commit(self) -> None:
    self.conn.commit()


if __name__ == "__main__":
    store = Store(get_store_path())
    str_to_encode = sys.argv[1] if len(sys.argv) > 1 else 'A quick brown fox\njumps over the\nlazy dog'
    str_id_ = get_short_str_id(str_to_encode, length=8)
    store.save(str_id_, str_to_encode)
    lines_, timestamp = store.get(str_id_)
    print(f"str_id:{str_id_} lines:{lines_} timestamp:{timestamp}")
