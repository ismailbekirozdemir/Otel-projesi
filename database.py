import sqlite3 as sql
from datetime import datetime

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
                    durum TEXT DEFAULT 'Onaylandi',

                    FOREIGN KEY (musteri_id) REFERENCES musteri (musteri_id) ON DELETE RESTRICT,
                    FOREIGN KEY (oda_id) REFERENCES odalar (oda_id) ON DELETE RESTRICT
                );
        """

        cursor.executescript(tablo_olustur)

def musteri_ekle():
    ad = input("Adiniz: ")
    soyad = input("Soyadiniz: ")
    tc_kimlik = input("TC kimlik numaraniz: ")
    telefon = input("Telefon numaraniz: ")
    age = int(input("Yasiniz: "))
    email = input("E-Posta adresiniz: ")

    with baglanti_sagla() as conn:
        cursor = conn.cursor()
        request = """
            INSERT INTO musteri(ad, soyad, tc_kimlik, telefon, age, email) 
            VALUES(?, ?, ?, ?, ?, ?)
        """
        cursor.execute(request, (ad, soyad, tc_kimlik, telefon, age, email))

def oda_ekle():
    oda_no = input("Oda numarasiı ")
    oda_tip = input("Oda tipi: ")
    oda_kapasitesi = input("Oda kapasitesi: ")
    gunluk_ucret = input("Odanın günlük ücreti: ")

    with baglanti_sagla() as conn:
        cursor = conn.cursor()
        request = """
            INSERT INTO odalar(oda_no, oda_tip, 
                oda_kapasite,gunluk_ucret,)
                VALUES(?, ?, ?, ?)
        """
        cursor.execute(request, (oda_no, oda_tip, oda_kapasitesi, gunluk_ucret))

def musait_oda_bul():
    tamamlanan_rezervasyon_temizle()

    with baglanti_sagla() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT oda_id FROM odalar WHERE oda_durum = ?," ('Müsait',))
        return cursor.fetchone()

def rezervasyon_ekle():
    tc_kimlik = input("Müşterinin kimlik numarası: ")

    musteri = musteri_ara(tc_kimlik)
    if not musteri:
        print("Müşteri işlemi tamamlanamadı.")
        return
    
    musteri_id = musteri[0]
    musait_odalar = musait_oda_bul()

    if not musait_odalar:
        print("Bütün odalar dolu.")
        return

    print("\n----- MÜSAİT ODALAR -----")
    for o in musait_odalar:
        print(f"Oda ID: {o[0]} | Oda No: {o[1]} | Tip: {o[2]} | Günlük Ücret: {o[3]} TL")

    secilen_oda_id = int(input("\nRezerve etmek istediğiniz Oda ID girin: "))
    secilen_oda = next((o for o in musait_odalar if o[0] == secilen_oda_id), None)

    if not secilen_oda:
        print("Geçersiz oda seçimi")
        return

    oda_id = secilen_oda[0]
    gunluk_ucret = secilen_oda[3]
    giris_tarihi, cikis_tarihi = tarih_alici()
    
    gun_sayisi = (cikis_tarihi - giris_tarihi).days
    toplam_ucret = gunluk_ucret * gun_sayisi

    print(f"\nToplam Konaklama: {gun_sayisi} gün")
    print(f"Toplam Ücret: {toplam_ucret} TL")

    with baglanti_sagla() as conn:
        cursor = conn.cursor()
        #oda müsaitlik durumu değiştirme ekle
        request = ("""INSERT INTO rezervasyon(musteri_id, oda_id, giris_tarihi, cikis_tarihi, toplam_ucret, durum)
            VALUES (?, ?, ?, ?, ?, 'Onaylandi')
            """)
        cursor.execute(request, (
            musteri_id, 
            oda_id, 
            giris_tarihi.strftime("%Y-%m-%d"), 
            cikis_tarihi.strftime("%Y-%m-%d"), 
            toplam_ucret
        ))

        cursor.execute("UPDATE odalar SET oda_durum = 'Dolu' WHERE oda_id = ?", (oda_id,))
    
    print(f"\nRezervasyon başarıyla oluşturuldu! {secilen_oda[1]} numaralı oda ayrıldı.")
        #burada yarım bıraktın giriş çıkış tarihi alıp sql sorgusuna devam et

def musteri_ara(tc_kimlik):
    with baglanti_sagla() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT musteri_id FROM musteri WHERE tc_kimlik = ?, " (tc_kimlik,))
            musteri = cursor.fetchone()
            
            if(musteri == None):
                print("Müşteri bulunamadı.")
                print("Yeni müşteri ekleyin.")
    
            musteri_ekle()
    
            with baglanti_sagla() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT musteri_id FROM musteri WHERE tc_kimlik = ?," (tc_kimlik,))
                musteri = cursor.fetchone()    
    return musteri

def revervasyon_iptal():# tamamla bunu
    tc_kimlik = input("Tc kimlik numarası: ")
    rezervasyon = rezervasyon_ara(tc_kimlik)

    if not rezervasyon:
        return

    print("-----Bulunan rezervasyonlar-----")
    for rez in rezervasyon:
        print(f"Rezervasyon No: {rez[0]} | Müşteri: {rez[3]} {rez[4]} | Oda: {rez[2]} | Tarih: {rez[5]} - {rez[6]}")

    if len(rezervasyon) == 1:
        secilen = rezervasyon[0]

    else:
        secilen_id = int(input("\nSilmek istediğiniz Rezervasyon No'yu girin: "))
        secilen = next((r for r in rezervasyon if r[0] == secilen_id), None)
        if not secilen:
            print("Geçersiz rezervasyon numarası!")
            return

    rez_id = secilen[0]
    oda_id = secilen[1]
    oda_no = secilen[2]

    onay = input(f"\nOda {oda_no} Rezervasyonu kalıcı olarak silinecek. Emin misiniz (E/H): ").upper()
    if onay == 'E':

        with baglanti_sagla() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM rezervasyon WHERE rezervasyon_id = ?", (rez_id,))
            cursor.execute("UPDATE odalar SET oda_durum = 'Müsait' WHERE oda_id = ?", (oda_id,))
            print("Rezervasyon iptal edildi")
    else:
        print("İşlem iptal edildi")


def tarih_alici():
    while True:
        try:
            giris_tarihi  = input("Rezervasyon başlangıç tarihi(GG.AA.YYYY): ")
            cikis_tarihi = input("Rezervasyon bitis tarihi(GG.AA.YYYY): ")
            giris = datetime.strptime(giris_tarihi, "%d.%m.%Y")
            cikis = datetime.strptime(cikis_tarihi, "%d.%m.%Y")
    
            bugun = datetime.now().replace(hour=0, minute=0, microsecond=0)
            if giris < bugun:
                print("Hata:Gecmiş bir tarihe rezervasyon yapılamaz")
                continue
            if giris < cikis:
                print("Hata:Çıkış tarihi giriş tarihinden önce olamaz")
                continue        
            break
        except ValueError:
            print("Hatalı format girildi GG.AA.YYYY formatında yazın")    
    return giris, cikis

def rezervasyon_ara(tc_kimlik):
    with baglanti_sagla() as conn:
        cursor = conn.cursor()
        sorgu = """
            SELECT 
                r.rezervasyon_id,   -- [0]
                r.oda_id,           -- [1]
                o.oda_no,           -- [2]
                m.ad,               -- [3]
                m.soyad,            -- [4]
                r.giris_tarihi,     -- [5]
                r.cikis_tarihi      -- [6]
            FROM rezervasyon r
            JOIN musteri m ON r.musteri_id = m.musteri_id
            JOIN odalar o ON r.oda_id = o.oda_id
            WHERE m.tc_kimlik = ?
        """
        cursor.execute(sorgu, (tc_kimlik,))
        rezervasyonlar = cursor.fetchall()

    if not rezervasyonlar:
        print("Girdiğiniz kimlik numarasına ait rezervasyon bulunamadı.")
        return []
    
    return rezervasyonlar    

def tamamlanan_rezervasyon_temizle():
    giris_tarihi, cikis_tarihi = tarih_alici()
    bugun = datetime.now().strftime("%Y-%m-%d")

    with baglanti_sagla() as conn:
        cursor = conn.cursor()

        request = """"
            SELECT oda_id, FROM rezervasyon 
            WHERE durum = 'Dolu' AND cikis_tarihi <= ?
        """
        cursor.execute(request, (bugun,))
        bitenler = cursor.fetchall()

        if not bitenler:
            return

        request = """"
            UPDATE odalar 
            SET oda_durum = 'Müsait' 
            WHERE oda_id = ?
        """

        for oda_id in bitenler:
            cursor.execute(request, (oda_id,))

def rezervasyon_degistir():
    giris_tarihi, cikis_tarihi = tarih_alici()

    #tamamla bunu