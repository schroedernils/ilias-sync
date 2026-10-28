"""Isolated issue-2 prototype; deliberately not connected to the production archive."""
import json
from pathlib import Path
import sqlite3
import time


class ReviewState:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS objects(identity TEXT PRIMARY KEY, digest TEXT, entry TEXT);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, identity TEXT, kind TEXT, stamp REAL);
            CREATE TABLE IF NOT EXISTS checkpoint(singleton INTEGER PRIMARY KEY CHECK(singleton=1), boundary INTEGER);
            INSERT OR IGNORE INTO checkpoint VALUES(1,0);
            CREATE TABLE IF NOT EXISTS undo(id INTEGER PRIMARY KEY AUTOINCREMENT, boundary INTEGER);
        ''')

    def baseline(self, entries):
        if self.db.execute('SELECT count(*) FROM objects').fetchone()[0]:
            raise ValueError('A baseline can only be established once.')
        with self.db:
            for identity, entry in entries.items():
                self.db.execute('INSERT INTO objects VALUES(?,?,?)', (identity,entry['digest'],json.dumps(entry)))

    def observe(self, identity, entry, *, stamp=None):
        previous = self.db.execute('SELECT digest FROM objects WHERE identity=?',(identity,)).fetchone()
        changed = previous is None or previous[0] != entry['digest']
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO objects VALUES(?,?,?)',(identity,entry['digest'],json.dumps(entry)))
            if changed and not entry.get('generated'):
                self.db.execute('INSERT INTO events(identity,kind,stamp) VALUES(?,?,?)',
                                (identity,'added' if previous is None else 'updated',time.time() if stamp is None else stamp))

    def boundary(self):
        return self.db.execute('SELECT coalesce(max(id),0) FROM events').fetchone()[0]

    def reviewed(self):
        return self.db.execute('SELECT boundary FROM checkpoint WHERE singleton=1').fetchone()[0]

    def acknowledge(self, captured_boundary):
        previous = self.reviewed()
        if not previous <= captured_boundary <= self.boundary():
            raise ValueError('Use a captured event boundary; never a wall-clock checkpoint.')
        if previous == captured_boundary:
            return
        with self.db:
            self.db.execute('INSERT INTO undo(boundary) VALUES(?)',(previous,))
            self.db.execute('UPDATE checkpoint SET boundary=? WHERE singleton=1',(captured_boundary,))

    def undo(self):
        row = self.db.execute('SELECT id,boundary FROM undo ORDER BY id DESC LIMIT 1').fetchone()
        if row:
            with self.db:
                self.db.execute('UPDATE checkpoint SET boundary=? WHERE singleton=1',(row[1],))
                self.db.execute('DELETE FROM undo WHERE id=?',(row[0],))

    def items(self, *, since_review=False, since_time=None):
        result = []
        for identity, encoded in self.db.execute('SELECT identity,entry FROM objects ORDER BY identity'):
            entry = json.loads(encoded)
            event = self.db.execute('SELECT id,kind,stamp FROM events WHERE identity=? ORDER BY id DESC LIMIT 1',(identity,)).fetchone()
            if since_review and (event is None or event[0] <= self.reviewed()):
                continue
            if since_time is not None and (event is None or event[2] < since_time):
                continue
            result.append({**entry,'identity':identity,'event':event[0] if event else 0,
                           'change':event[1] if event else '', 'changed_at':event[2] if event else 0})
        return sorted(result,key=lambda row:row['event'],reverse=True)

    def close(self):
        self.db.close()


def local_read_check(path, *, local_root, cloud_roots=()):
    """Read only a caller-designated local fixture root. Never promise offline residency."""
    import os
    import stat
    checked = time.time()
    path, local_root = Path(os.path.abspath(path)), Path(os.path.abspath(local_root))
    def result(state):
        return {'path':str(path),'state':state,'checked_at':checked,'offline_certified':False}
    if path.suffix.lower() in {'.url','.webloc'}:
        return result('external_link')
    if any(path.is_relative_to(Path(root).absolute()) for root in cloud_roots) or 'CloudStorage' in path.parts:
        return result('residency_unverified')
    if not path.is_relative_to(local_root):
        return result('outside_local_fixture')
    # Reject symlinks before opening: a parent link could otherwise escape the
    # designated root or lead into a cloud/network provider and hydrate content.
    for parent in [path,*path.parents]:
        if parent.is_symlink() or getattr(parent, 'is_junction', lambda:False)():
            return result('residency_unverified')
    if not local_root.is_dir():
        return result('root_unavailable')
    try:
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            return result('not_regular')
        with path.open('rb') as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev,opened.st_ino) != (before.st_dev,before.st_ino):
                return result('changed_during_check')
            count = 0
            for block in iter(lambda:handle.read(1024*1024),b''):
                count += len(block)
            after = os.fstat(handle.fileno())
        if (before.st_ino,before.st_size,before.st_mtime_ns) != (after.st_ino,after.st_size,after.st_mtime_ns) or count != after.st_size:
            return result('changed_during_check')
        return result('local_read_passed')
    except FileNotFoundError:
        return result('missing')
    except OSError:
        return result('unreadable')
