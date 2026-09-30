import sqlite3 as sql

def baglanti_sagla():
    conn = sql.connect('Otel.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def veritabani_olustur():
    with baglanti_sagla() as conn:
        cursor = conn.cursor()

        tablo_olustur = """
                CREATE TABLE IF NOT EXISTS odalar(
                    oda_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    oda_no TEXT NOT NULL,
                    oda_tip TEXT NOT NULL,
                    oda_kapasite INTEGER NOT NULL,
                    gunluk_ucret REAL NOT NULL,
                    oda_durum TEXT DEFAULT 'Müsait'
                );
                CREATE TABLE IF NOT EXISTS musteri(
                    musteri_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad TEXT NOT NULL,
                    soyad TEXT NOT NULL,
                    tc_kimlik TEXT NOT NULL,
                    telefon TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    email TEXT
                );
                CREATE TABLE IF NOT EXISTS rezervasyon(
                    rezervasyon_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    musteri_id INTEGER NOT NULL,
                    oda_id INTEGER NOT NULL,

                    islem_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,

                    giris_tarihi DATE NOT NULL,
                    cikis_tarihi DATE NOT NULL,

                    toplam_ucret REAL NOT NULL,
                    odendi_mi INTEGER DEFAULT 0,
                    durum TEXT DEFAULT 'Onaylandı',

                    FOREIGN KEY (musteri_id) REFERENCES musteri (musteri_id) ON DELETE RESTRICT,
                    FOREIGN KEY (oda_id) REFERENCES odalar (oda_id) ON DELETE RESTRICT
                );
        """

        cursor.executescript(tablo_olustur)

def musteri_ekle():
    ad = input("Adınız: ")
    soyad = input("Soyadınız: ")
    tc_kimlik = input("TC kimlik numaranız: ")
    telefon = input("Telefon numaranız: ")
    age = int(input("Yaşınız: "))
    email = input("E-Posta adresiniz: ")

    with baglanti_sagla() as conn:
        cursor = conn.cursor()
        request = """
            INSERT INTO musteri(ad, soyad, tc_kimlik, telefon, age, email) 
            VALUES(?, ?, ?, ?, ?, ?)
        """
        cursor.execute(request, (ad, soyad, tc_kimlik, telefon, age, email))