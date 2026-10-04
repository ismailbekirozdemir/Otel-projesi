import sqlite3 as sql

def baglanti_al():
    conn = sql.connect('Otel.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def tablo_olustur():
    conn = baglanti_al()

    cursor = conn.cursor()

    tablolari_olustur = """
    CREATE TABLE IF NOT EXISTS odalar(
        oda_id INTEGER PRIMARY KEY AUTOINCREMENT,
        oda_numarasi TEXT NOT NULL UNIQUE,
        oda_tipi TEXT NOT NULL,
        kapasite INTEGER NOT NULL DEFAULT 2,
        gunluk_fiyat REAL NOT NULL,
        durum TEXT DEFAULT 'Müsait');

    CREATE TABLE IF NOT EXISTS MUSTERI(
        musteri_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tc_kimlik TEXT UNIQUE,
        ad TEXT NOT NULL,
        soyad TEXT NOT NULL,
        telefon TEXT NOT NULL,
        eposta TEXT,
        kayit_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS rezervasyonlar(
        rezervasyon_id INTEGER PRIMARY KEY AUTOINCREMENT,
        musteri_id INTEGER NOT NULL,
        oda_id INTEGER NOT NULL,
        giris_tarihi DATE NOT NULL,
        cikis_tarihi DATE NOT NULL,
        toplam_ucret REAL NOT NULL, 
        odendi_mi INTEGER DEFAULT 0,
        durum TEXT DEFAULT 'Bekliyor',
        FOREIGN KEY (musteri_id) REFERENCES MUSTERI (musteri_id) ON DELETE CASCADE,
        FOREIGN KEY (oda_id) REFERENCES odalar (oda_id) ON DELETE RESTRICT
    );
        """

    cursor.executescript(tablolari_olustur)
    conn.commit()
    conn.close()

def musteri_ekle(tc_kimlik, ad, soyad, telefon, eposta):
    with baglanti_al() as conn:
        cursor = conn.cursor()

        request = """
            INSERT INTO MUSTERI(tc_kimlik, ad, soyad, telefon, eposta)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(request, (tc_kimlik, ad, soyad, telefon, eposta))
    print(f"{ad} {soyad} başarıyla kaydedildi.")

def varsayilan_odalari_ekle():
    ornek_odalar = [
        ('101', 'Standart', 2, 1500.0),
        ('102', 'Standart', 2, 1500.0),
        ('201', 'Suit', 3, 2500.0),
        ('202', 'Aile Odası', 4, 3200.0)
    ]
    with baglanti_al() as conn:
        cursor = conn.cursor()

        cursor.executemany("""
            INSERT OR IGNORE INTO odalar (oda_numarasi, oda_tipi, kapasite, gunluk_fiyat)
            VALUES(?, ?, ?, ?)
        """, ornek_odalar)
    print("Varsayılan odalar eklendi")


from datetime import datetime
def rezervasyon_ayarla(musteri_id, oda_id, giris_tarihi, cikis_tarihi):

    try:
        giris = datetime.strptime(giris_tarihi, "%Y-%m-%d").date()
        cikis = datetime.strptime(cikis_tarihi, "%Y-%m-%d").date()
    except ValueError:
        print("Hata: Tarih formatı 'YYYY-MM-DD' olmalıdır (Örn: 2026-06-15).")
        return False

    gece_sayisi = (cikis - giris).days

    with baglanti_al() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT gunluk_fiyat, oda_numarasi FROM odalar WHERE oda_id = ?", (oda_id,))
        oda = cursor.fetchone()
        
        if not oda:
            print("Hata: Oda bulunamadı!")
            return False

        gunluk_fiyat, oda_no = oda[0], oda[1]
        toplam_ucret = gece_sayisi * gunluk_fiyat

        ekle_sorgu = """
            INSERT INTO rezervasyonlar (musteri_id, oda_id, giris_tarihi, cikis_tarihi, toplam_ucret, durum)
            VALUES (?, ?, ?, ?, ?, 'Onaylandı')
        """
        cursor.execute(ekle_sorgu, (musteri_id, oda_id, giris_tarihi, cikis_tarihi, toplam_ucret))

    print(f"\nRezervasyon Başarılı! | Oda: {oda_no} | Gece: {gece_sayisi} | Tutar: {toplam_ucret} TL")
    return True
   

def bos_odalari_bul(giris_tarihi, cikis_tarihi):
    with baglanti_al() as conn:
        cursor = conn.cursor()

        sorgu = """
            SELECT oda_id, oda_numarasi, oda_tipi, kapasite, gunluk_fiyat
            FROM odalar 
            WHERE durum = 'Müsait'
                AND oda_id NOT IN(
                    SELEC oda_id FROM rezervasyonlar
                    WHERE durum != 'İptal'
                        AND giris < ?
                        AND cikis > ?
                )
        """
        cursor.execute(sorgu, (cikis_tarihi, giris_tarihi))
        bos_odalar = cursor.fetchall()

        if not bos_odalar:
            print(f"{giris_tarihi} ile {cikis_tarihi} arasında hiç boş oda yok!")
            return []

        print(f"\n--- {giris_tarihi} / {cikis_tarihi} Arası Boş Odalar ---")
        for oda in bos_odalar:
            print(f"Oda ID: {oda[0]} | No: {oda[1]} | Tip: {oda[2]} | Kapasite: {oda[3]} Kişilik | Fiyat: {oda[4]} TL")
        
        return bos_odalar
