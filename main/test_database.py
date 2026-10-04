"""
=============================================================================
Otel Otomasyon Sistemi - Veritabanı Bütünlük ve İş Mantığı Test Paketi
=============================================================================
Kıdemli QA & Test Otomasyon Mühendisliği Standartlarında Hazırlanmıştır.

Özellikler:
- İzole SQLite in-memory (:memory:) ortamı
- PRAGMA foreign_keys = ON ile foreign key ve restrict kısıt doğrulamaları
- Overlap (çakışma) ve self-exclusion (kendi rezervasyonunu hariç tutma) testleri
- Sınır değer analizleri (Edge Case: Check-out == Check-in)
- Müsait oda sorgusu tekilleştirme (DISTINCT) testleri
=============================================================================
"""

import unittest
import sqlite3
from datetime import datetime, date


# Proje SQLite Şeması (database.py dosyasındaki orijinal şema tanımı)
DB_SCHEMA = """
PRAGMA foreign_keys = ON;

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


class BaseDatabaseTestCase(unittest.TestCase):
    """
    Tüm test sınıfları için izole in-memory SQLite veritabanı oluşturan temel sınıf.
    Her test metodundan önce sıfır bir veritabanı ayağa kaldırılır.
    """

    def setUp(self):
        # İzole in-memory veritabanı bağlantısı
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.cursor = self.conn.cursor()
        self.cursor.executescript(DB_SCHEMA)

    def tearDown(self):
        self.conn.close()

    # --- Yardımcı Fixture Metotları ---
    def helper_create_room(self, oda_no="101", oda_tip="Standart", kapasite=2, ucret=1000.0, durum="Müsait"):
        self.cursor.execute(
            """
            INSERT INTO odalar(oda_no, oda_tip, oda_kapasite, gunluk_ucret, oda_durum)
            VALUES(?, ?, ?, ?, ?)
            """,
            (oda_no, oda_tip, kapasite, ucret, durum),
        )
        return self.cursor.lastrowid

    def helper_create_customer(self, ad="Ahmet", soyad="Yılmaz", tc="12345678901", tel="5551112233", yas=30, email="ahmet@example.com"):
        self.cursor.execute(
            """
            INSERT INTO musteri(ad, soyad, tc_kimlik, telefon, age, email)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (ad, soyad, tc, tel, yas, email),
        )
        return self.cursor.lastrowid

    def helper_create_reservation(self, musteri_id, oda_id, giris, cikis, ucret=2000.0, durum="Onaylandi"):
        self.cursor.execute(
            """
            INSERT INTO rezervasyon(musteri_id, oda_id, giris_tarihi, cikis_tarihi, toplam_ucret, durum)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (musteri_id, oda_id, giris, cikis, ucret, durum),
        )
        return self.cursor.lastrowid


# =============================================================================
# 1. ŞEMA VE VERİ BÜTÜNLÜĞÜ TESTLERİ (CONSTRAINTS & INTEGRITY)
# =============================================================================
class TestSchemaAndIntegrityConstraints(BaseDatabaseTestCase):
    """Foreign Key, ON DELETE RESTRICT ve NOT NULL kısıtlarını doğrular."""

    def test_foreign_key_invalid_musteri_id_raises_integrity_error(self):
        """Mevcut olmayan bir musteri_id ile rezervasyon açılması engellenmelidir."""
        oda_id = self.helper_create_room()
        gecersiz_musteri_id = 9999

        with self.assertRaises(sqlite3.IntegrityError, msg="Geçersiz musteri_id ile kayıt engellenmeli!"):
            self.cursor.execute(
                """
                INSERT INTO rezervasyon(musteri_id, oda_id, giris_tarihi, cikis_tarihi, toplam_ucret)
                VALUES(?, ?, '2026-06-01', '2026-06-05', 5000.0)
                """,
                (gecersiz_musteri_id, oda_id),
            )

    def test_foreign_key_invalid_oda_id_raises_integrity_error(self):
        """Mevcut olmayan bir oda_id ile rezervasyon açılması engellenmelidir."""
        musteri_id = self.helper_create_customer()
        gecersiz_oda_id = 8888

        with self.assertRaises(sqlite3.IntegrityError, msg="Geçersiz oda_id ile kayıt engellenmeli!"):
            self.cursor.execute(
                """
                INSERT INTO rezervasyon(musteri_id, oda_id, giris_tarihi, cikis_tarihi, toplam_ucret)
                VALUES(?, ?, '2026-06-01', '2026-06-05', 5000.0)
                """,
                (musteri_id, gecersiz_oda_id),
            )

    def test_on_delete_restrict_prevents_deleting_customer_with_active_reservation(self):
        """Aktif rezervasyonu bulunan müşteri ON DELETE RESTRICT sebebiyle silinemez."""
        musteri_id = self.helper_create_customer()
        oda_id = self.helper_create_room()
        self.helper_create_reservation(musteri_id, oda_id, "2026-07-01", "2026-07-05")

        with self.assertRaises(sqlite3.IntegrityError, msg="Rezervasyonu olan müşteri silinememelidir!"):
            self.cursor.execute("DELETE FROM musteri WHERE musteri_id = ?", (musteri_id,))

    def test_on_delete_restrict_prevents_deleting_room_with_active_reservation(self):
        """Rezervasyonu bulunan bir oda ON DELETE RESTRICT sebebiyle silinemez."""
        musteri_id = self.helper_create_customer()
        oda_id = self.helper_create_room()
        self.helper_create_reservation(musteri_id, oda_id, "2026-07-01", "2026-07-05")

        with self.assertRaises(sqlite3.IntegrityError, msg="Rezervasyonu olan oda silinememelidir!"):
            self.cursor.execute("DELETE FROM odalar WHERE oda_id = ?", (oda_id,))

    def test_not_null_constraints_on_required_fields(self):
        """NOT NULL tanımlı kritik alanlar boş bırakıldığında IntegrityError fırlatılmalıdır."""
        # Odalar tablosunda oda_no NOT NULL
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("INSERT INTO odalar(oda_no, oda_tip, oda_kapasite, gunluk_ucret) VALUES(NULL, 'Tek', 1, 500)")

        # Müşteri tablosunda tc_kimlik NOT NULL
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("INSERT INTO musteri(ad, soyad, tc_kimlik, telefon, age) VALUES('Ali', 'Kaya', NULL, '555', 25)")

        # Rezervasyon tablosunda giris_tarihi ve cikis_tarihi NOT NULL
        musteri_id = self.helper_create_customer()
        oda_id = self.helper_create_room()
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute(
                "INSERT INTO rezervasyon(musteri_id, oda_id, giris_tarihi, cikis_tarihi, toplam_ucret) VALUES(?, ?, NULL, '2026-08-05', 1000)",
                (musteri_id, oda_id),
            )


# =============================================================================
# 2. TARİH ÇAKIŞMA (OVERLAP) MANTIĞI TESTLERİ
# =============================================================================
class TestReservationOverlapLogic(BaseDatabaseTestCase):
    """
    Rezervasyon tarihlerinin çakışma (conflict) mantığını test eder.
    Standart Otel Çakışma Kuralı:
        (Yeni Giriş < Mevcut Çıkış) AND (Yeni Çıkış > Mevcut Giriş)
    """

    def setUp(self):
        super().setUp()
        self.musteri_id = self.helper_create_customer()
        self.oda_id = self.helper_create_room(oda_no="201")
        # Referans Rezervasyon: 2026-06-10 ile 2026-06-20 arası (10 gece)
        self.ref_rez_id = self.helper_create_reservation(
            self.musteri_id, self.oda_id, giris="2026-06-10", cikis="2026-06-20"
        )

    def is_room_available(self, oda_id, yeni_giris, yeni_cikis, exclude_rez_id=None):
        """
        Belirtilen tarihlerde odanın müsait olup olmadığını kontrol eden sorgu fonksiyonu.
        """
        sorgu = """
            SELECT COUNT(*) FROM rezervasyon
            WHERE oda_id = ?
              AND durum = 'Onaylandi'
              AND giris_tarihi < ?
              AND cikis_tarihi > ?
        """
        params = [oda_id, yeni_cikis, yeni_giris]

        if exclude_rez_id is not None:
            sorgu += " AND rezervasyon_id != ?"
            params.append(exclude_rez_id)

        self.cursor.execute(sorgu, params)
        cakisma_sayisi = self.cursor.fetchone()[0]
        return cakisma_sayisi == 0

    def test_overlap_nested_exact_subrange(self):
        """Mevcut rezervasyonun tam ortasına denk gelen tarihler çakışma olarak algılanmalıdır."""
        # 12 Haziran - 15 Haziran (Mevcut rezervasyonun içinde)
        available = self.is_room_available(self.oda_id, "2026-06-12", "2026-06-15")
        self.assertFalse(available, "Mevcut rezervasyonun ortasındaki tarih aralığı dolu olmalıdır!")

    def test_overlap_exact_matching_dates(self):
        """Mevcut rezervasyonla birebir aynı tarihler çakışma olmalıdır."""
        available = self.is_room_available(self.oda_id, "2026-06-10", "2026-06-20")
        self.assertFalse(available, "Birebir aynı tarih aralığı dolu olmalıdır!")

    def test_overlap_enclosing_range(self):
        """Mevcut rezervasyonun öncesinde başlayıp sonrasında biten kapsayıcı tarihler çakışmalıdır."""
        # 05 Haziran - 25 Haziran
        available = self.is_room_available(self.oda_id, "2026-06-05", "2026-06-25")
        self.assertFalse(available, "Mevcut rezervasyonu kapsayan geniş tarih aralığı çakışmalıdır!")

    def test_overlap_partial_left_and_right(self):
        """Kısmi kesişimler (önceden başlayıp içinde biten veya içinde başlayıp sonra biten) çakışmalıdır."""
        # Sol kesişim: 05 Haziran - 15 Haziran
        self.assertFalse(self.is_room_available(self.oda_id, "2026-06-05", "2026-06-15"))
        # Sağ kesişim: 15 Haziran - 25 Haziran
        self.assertFalse(self.is_room_available(self.oda_id, "2026-06-15", "2026-06-25"))

    def test_edge_case_same_day_checkout_checkin_is_available(self):
        """
        KRİTİK SINIR DURUMU (Edge Case):
        Otelcilik standardında bir müşterinin çıkış yaptığı gün (check-out)
        başka bir müşteri aynı odaya giriş yapabilir (check-in).
        """
        # Durum 1: Mevcut rezervasyonun başladığı gün (10 Haziran) çıkış yapacak müşteri -> Müsait olmalı
        available_before = self.is_room_available(self.oda_id, "2026-06-01", "2026-06-10")
        self.assertTrue(available_before, "Check-out günü mevcut rezervasyonun check-in günü ile aynı ise çakışma OLMAMALIDIR!")

        # Durum 2: Mevcut rezervasyonun bittiği gün (20 Haziran) giriş yapacak müşteri -> Müsait olmalı
        available_after = self.is_room_available(self.oda_id, "2026-06-20", "2026-06-25")
        self.assertTrue(available_after, "Check-in günü mevcut rezervasyonun check-out günü ile aynı ise çakışma OLMAMALIDIR!")


# =============================================================================
# 3. REZERVASYON GÜNCELLEME (SELF-EXCLUSION) TESTLERİ
# =============================================================================
class TestReservationUpdateSelfExclusion(BaseDatabaseTestCase):
    """
    Tarih güncellerken kullanıcının KENDİ rezervasyonunun çakışma yaratmamasını,
    ancak BAŞKA rezervasyonla çakıştığında engellenmesini doğrular.
    """

    def setUp(self):
        super().setUp()
        self.musteri_1 = self.helper_create_customer(ad="Can", tc="11111111111")
        self.musteri_2 = self.helper_create_customer(ad="Deniz", tc="22222222222")
        self.oda_id = self.helper_create_room(oda_no="301")

        # Can'ın Rezervasyonu (Rez 1): 2026-08-01 - 2026-08-10
        self.rez1_id = self.helper_create_reservation(self.musteri_1, self.oda_id, "2026-08-01", "2026-08-10")

        # Deniz'in Rezervasyonu (Rez 2): 2026-08-15 - 2026-08-20
        self.rez2_id = self.helper_create_reservation(self.musteri_2, self.oda_id, "2026-08-15", "2026-08-20")

    def check_conflict(self, oda_id, yeni_giris, yeni_cikis, exclude_rez_id):
        self.cursor.execute(
            """
            SELECT COUNT(*) FROM rezervasyon
            WHERE oda_id = ?
              AND rezervasyon_id != ?
              AND durum = 'Onaylandi'
              AND giris_tarihi < ?
              AND cikis_tarihi > ?
            """,
            (oda_id, exclude_rez_id, yeni_cikis, yeni_giris),
        )
        return self.cursor.fetchone()[0] > 0

    def test_self_exclusion_allows_updating_own_dates(self):
        """
        Can, rezervasyonunu 2 gün kaydırıp 2026-08-03 - 2026-08-12 yapmak istiyor.
        Eski tarihleriyle kesişmesine rağmen KENDİ rezervasyonu hariç tutulduğu için izin verilmelidir.
        """
        has_conflict = self.check_conflict(
            self.oda_id,
            yeni_giris="2026-08-03",
            yeni_cikis="2026-08-12",
            exclude_rez_id=self.rez1_id,
        )
        self.assertFalse(has_conflict, "Kendi rezervasyonu ile kesişim çakışma sayılmamalıdır!")

    def test_self_exclusion_detects_conflict_with_another_customer(self):
        """
        Can, rezervasyonunu uzatıp Deniz'in rezervasyon tarihine (15-20 Ağustos) sarkıtırsa
        (örn: 2026-08-03 - 2026-08-17), sistem bunu çakışma olarak tespit etmelidir!
        """
        has_conflict = self.check_conflict(
            self.oda_id,
            yeni_giris="2026-08-03",
            yeni_cikis="2026-08-17",
            exclude_rez_id=self.rez1_id,
        )
        self.assertTrue(has_conflict, "Başka bir müşterinin rezervasyonuna taşan tarih çakışma olarak yakalanmalıdır!")


# =============================================================================
# 4. VERİ TUTARLILIĞI VE TEKİLLEŞTİRME (DISTINCT) TESTLERİ
# =============================================================================
class TestAvailableRoomSearchDeduplication(BaseDatabaseTestCase):
    """Müsait oda aramalarında aynı odanın mükerrer listelenmediğini doğrular."""

    def test_available_rooms_query_returns_distinct_room_ids(self):
        """Bir odanın geçmişte/gelecekte birden çok rezervasyonu olsa dahi sorgu DISTINCT oda listesi dönmelidir."""
        # 2 Oda oluştur
        oda_1 = self.helper_create_room(oda_no="401")
        oda_2 = self.helper_create_room(oda_no="402")
        musteri = self.helper_create_customer()

        # Oda 401 için 3 farklı dönemde rezervasyon ekle
        self.helper_create_reservation(musteri, oda_1, "2026-01-01", "2026-01-05")
        self.helper_create_reservation(musteri, oda_1, "2026-02-01", "2026-02-05")
        self.helper_create_reservation(musteri, oda_1, "2026-03-01", "2026-03-05")

        # 2026-04-01 - 2026-04-10 tarihleri için müsait odaları sorgula
        arama_giris = "2026-04-01"
        arama_cikis = "2026-04-10"

        sorgu = """
            SELECT DISTINCT o.oda_id, o.oda_no
            FROM odalar o
            WHERE o.oda_id NOT IN (
                SELECT oda_id FROM rezervasyon
                WHERE durum = 'Onaylandi'
                  AND giris_tarihi < ?
                  AND cikis_tarihi > ?
            )
            ORDER BY o.oda_id ASC
        """
        self.cursor.execute(sorgu, (arama_cikis, arama_giris))
        musait_odalar = self.cursor.fetchall()

        # Doğrulamalar:
        oda_id_listesi = [oda[0] for oda in musait_odalar]
        self.assertEqual(len(oda_id_listesi), 2, "Her iki oda da müsait olmalı ve toplam 2 kayıt dönmelidir.")
        self.assertEqual(
            len(oda_id_listesi),
            len(set(oda_id_listesi)),
            "Müsait oda listesinde aynı oda asla birden fazla kez tekrarlanmamalıdır (DISTINCT garantisi).",
        )
        self.assertIn(oda_1, oda_id_listesi)
        self.assertIn(oda_2, oda_id_listesi)


if __name__ == "__main__":
    # Testleri detaylı (verbose) formatta çalıştır
    unittest.main(verbosity=2)
