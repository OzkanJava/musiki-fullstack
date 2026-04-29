"""
Birebir port: seek-tune/server/db/sqlite.go
SQLite veritabanı — songs + fingerprints tabloları.
"""
import sqlite3


class SQLiteClient:
    def __init__(self, db_path='seekture.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, timeout=5)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        """
        Go karşılığı: sqlite.go → createTables()
        """
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title  TEXT NOT NULL,
                artist TEXT NOT NULL,
                key    TEXT NOT NULL UNIQUE
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS fingerprints (
                address       INTEGER NOT NULL,
                anchor_time_ms INTEGER NOT NULL,
                song_id       INTEGER NOT NULL,
                PRIMARY KEY (address, anchor_time_ms, song_id)
            )
        ''')
        self.conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_fp_address ON fingerprints(address)'
        )
        self.conn.commit()

    # ── Songs ─────────────────────────────────────────────────────────────

    def store_song(self, title, artist):
        """Şarkıyı kaydet, ID döndür. Zaten varsa mevcut ID'yi döndür."""
        key = f"{title}---{artist}"
        cursor = self.conn.execute(
            'INSERT OR IGNORE INTO songs (title, artist, key) VALUES (?, ?, ?)',
            (title, artist, key),
        )
        self.conn.commit()
        if cursor.lastrowid and cursor.rowcount > 0:
            return cursor.lastrowid
        row = self.conn.execute(
            'SELECT id FROM songs WHERE key = ?', (key,)
        ).fetchone()
        return row[0] if row else None

    def store_song_with_id(self, song_id, title, artist):
        """
        Django entegrasyonu için: belirli bir ID ile şarkı kaydet.
        Django Song.id'yi seekture song_id olarak kullanarak doğrudan eşleşme sağlar.
        Zaten varsa günceller.
        """
        key = f"{title}---{artist}"
        self.conn.execute(
            'INSERT OR REPLACE INTO songs (id, title, artist, key) VALUES (?, ?, ?, ?)',
            (song_id, title, artist, key),
        )
        self.conn.commit()
        return song_id

    def delete_song(self, song_id):
        """Şarkıyı ve tüm fingerprint'lerini sil."""
        self.conn.execute('DELETE FROM fingerprints WHERE song_id = ?', (song_id,))
        self.conn.execute('DELETE FROM songs WHERE id = ?', (song_id,))
        self.conn.commit()

    def get_song_by_id(self, song_id):
        """Go karşılığı: GetSongByID(id)"""
        row = self.conn.execute(
            'SELECT id, title, artist FROM songs WHERE id = ?', (song_id,)
        ).fetchone()
        if row:
            return {'id': row[0], 'title': row[1], 'artist': row[2]}
        return None

    def get_total_songs(self):
        row = self.conn.execute('SELECT COUNT(*) FROM songs').fetchone()
        return row[0]

    # ── Fingerprints ──────────────────────────────────────────────────────

    def store_fingerprints(self, fingerprints):
        """
        Go karşılığı: StoreFingerprints(fingerprints map[uint32]Couple)
        fingerprints: dict[address -> Couple] veya list[(address, Couple)]
        """
        if isinstance(fingerprints, dict):
            rows = [
                (addr, c.anchor_time_ms, c.song_id)
                for addr, c in fingerprints.items()
            ]
        else:
            # list of (address, Couple) — tum fingerprint'ler, kayip yok
            rows = [
                (addr, c.anchor_time_ms, c.song_id)
                for addr, c in fingerprints
            ]
        self.conn.executemany(
            'INSERT OR IGNORE INTO fingerprints '
            '(address, anchor_time_ms, song_id) VALUES (?, ?, ?)',
            rows,
        )
        self.conn.commit()

    def get_couples(self, addresses):
        """
        Go karşılığı: GetCouples(addresses []uint32) map[uint32][]Couple
        Returns: dict[address] -> list of {anchor_time_ms, song_id}
        """
        if not addresses:
            return {}

        result = {}
        unique_addresses = list(set(addresses))
        CHUNK_SIZE = 900
        
        for i in range(0, len(unique_addresses), CHUNK_SIZE):
            chunk = unique_addresses[i:i + CHUNK_SIZE]
            placeholders = ','.join('?' * len(chunk))
            rows = self.conn.execute(
                f'SELECT address, anchor_time_ms, song_id '
                f'FROM fingerprints WHERE address IN ({placeholders})',
                chunk,
            ).fetchall()

            for addr, anchor_ms, song_id in rows:
                if addr not in result:
                    result[addr] = []
                result[addr].append({
                    'anchor_time_ms': anchor_ms,
                    'song_id': song_id,
                })

        return result

    def get_total_fingerprints(self):
        row = self.conn.execute('SELECT COUNT(*) FROM fingerprints').fetchone()
        return row[0]

    def close(self):
        self.conn.close()
