import os
import sys
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QMessageBox

if hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication
import database.database as database
# --- DİNAMİK YOL FONKSİYONU (Arayüz dosyaları için) ---
def get_resource_path(relative_path):
    """
    Program .exe iken geçici klasördeki (_MEIPASS) dosyayı,
    normal Python çalışırken ise proje klasöründeki dosyayı bulur.
    """
    if hasattr(sys, '_MEIPASS'):
        # Exe çalışırken geçici klasörün yolu
        return os.path.join(sys._MEIPASS, relative_path)
    
    # Normal Python çalışırken: main.py'nin bir üst klasörüne (proje köküne) gider
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, relative_path)

app = QApplication(sys.argv)
pencere = uic.loadUi(get_resource_path("UI/arayuz.ui"))

# 1. Rezervasyon penceresi nesnesi (rezervasyon.ui)
rezervasyon_dialog = uic.loadUi(get_resource_path("UI/rezervasyon.ui"))
secili_oda_no = None

def oda_butonuna_basildi(oda_no):
    global secili_oda_no
    secili_oda_no = oda_no
    rezervasyon_dialog.setWindowTitle(f"Oda {oda_no} - Rezervasyon İşlemi")
    rezervasyon_dialog.show()

def rezervasyonu_kaydet():
    ad = rezervasyon_dialog.txt_ad.text().strip()
    soyad = rezervasyon_dialog.txt_soyad.text().strip()
    tc = rezervasyon_dialog.txt_tc.text().strip()
    tel = rezervasyon_dialog.txt_tel.text().strip()

    giris = rezervasyon_dialog.date_giris.date().toString("yyyy-MM-dd")
    cikis = rezervasyon_dialog.date_cikis.date().toString("yyyy-MM-dd")

    # Boş alan kontrolü
    if not ad or not soyad or not tc or not tel:
        QMessageBox.warning(
            rezervasyon_dialog,
            "Eksik Bilgi",
            "Lütfen müşteri bilgilerini eksiksiz doldurun."
        )
        return

    # Tarih kontrolü
    if rezervasyon_dialog.date_giris.date() >= rezervasyon_dialog.date_cikis.date():
        QMessageBox.warning(
            rezervasyon_dialog,
            "Hatalı Tarih",
            "Çıkış tarihi giriş tarihinden sonra olmalıdır."
        )
        return

    try:
        with database.baglanti_sagla() as conn:
            cursor = conn.cursor()

            # Seçilen oda gerçekten müsait mi?
            cursor.execute("""
                SELECT oda_id, gunluk_ucret
                FROM odalar
                WHERE oda_no = ? AND oda_durum = 'Müsait'
            """, (secili_oda_no,))

            oda = cursor.fetchone()

            if not oda:
                QMessageBox.warning(
                    rezervasyon_dialog,
                    "Oda Dolu",
                    "Bu oda artık müsait değil."
                )
                return

            oda_id = oda[0]
            gunluk_ucret = oda[1]

            # Müşteri daha önce kayıtlı mı?
            cursor.execute("""
                SELECT musteri_id
                FROM musteri
                WHERE tc_kimlik = ?
            """, (tc,))

            musteri = cursor.fetchone()

            if musteri:
                musteri_id = musteri[0]

            else:
                # Şu an UI'da yaş alanı olmadığı için 0 veriyoruz.
                cursor.execute("""
                    INSERT INTO musteri
                    (ad, soyad, tc_kimlik, telefon, age, email)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    ad,
                    soyad,
                    tc,
                    tel,
                    0,
                    None
                ))

                musteri_id = cursor.lastrowid

            # Konaklama gün sayısı
            gun_sayisi = (
                rezervasyon_dialog.date_cikis.date()
                .toPyDate()
                -
                rezervasyon_dialog.date_giris.date()
                .toPyDate()
            ).days

            toplam_ucret = gunluk_ucret * gun_sayisi

            # Rezervasyonu oluştur
            cursor.execute("""
                INSERT INTO rezervasyon
                (musteri_id, oda_id, giris_tarihi, cikis_tarihi,
                 toplam_ucret, durum)
                VALUES (?, ?, ?, ?, ?, 'Onaylandi')
            """, (
                musteri_id,
                oda_id,
                giris,
                cikis,
                toplam_ucret
            ))

            # Odayı dolu yap
            cursor.execute("""
                UPDATE odalar
                SET oda_durum = 'Dolu'
                WHERE oda_id = ?
            """, (oda_id,))

        QMessageBox.information(
            rezervasyon_dialog,
            "Başarılı",
            f"Rezervasyon başarıyla oluşturuldu!\n\n"
            f"Oda: {secili_oda_no}\n"
            f"Giriş: {giris}\n"
            f"Çıkış: {cikis}\n"
            f"Toplam Ücret: {toplam_ucret} TL"
        )

        rezervasyon_dialog.close()
        arayuzu_db_ile_guncelle()

    except Exception as e:
        QMessageBox.critical(
            rezervasyon_dialog,
            "Hata",
            f"Rezervasyon oluşturulurken hata oluştu:\n\n{e}"
        )

def arayuzu_db_ile_guncelle():
    # 1. Gerçek veriyi SQLite'tan çek
    odalar_verisi = database.arayuz_icin_odalari_getir()
    print("ODALAR:", odalar_verisi)
    # 2. Qt Designer'daki etiketlere yazdır
    for index, veri in enumerate(odalar_verisi):
        
        suffix = "" if index == 0 else f"_{index + 1}"
        
        lbl_ad = getattr(pencere, f"ad_soyad{suffix}", None)
        lbl_no = getattr(pencere, f"oda_no{suffix}", None)
        lbl_durum = getattr(pencere, f"durum{suffix}", None)
        lbl_ucret = getattr(pencere, f"gunluk_ucret{suffix}", None)
        lbl_giris = getattr(pencere, f"giris{suffix}", None)
        lbl_cikis = getattr(pencere, f"cikis{suffix}", None)

        if lbl_no: lbl_no.setText(f"Oda: {veri['oda_no']}")
        if lbl_ad: lbl_ad.setText(f"Müşteri: {veri['ad_soyad']}")
        if lbl_ucret: lbl_ucret.setText(f"Ücret: {veri['gunluk_ucret']}")
        if lbl_giris: lbl_giris.setText(f"Giriş: {veri['giris']}")
        if lbl_cikis: lbl_cikis.setText(f"Çıkış: {veri['cikis']}")

        if lbl_durum:
            durum_metni = veri['durum'].upper()
            lbl_durum.setText(durum_metni)
            
            # Durumuna göre etiket rengini ayarla
            if durum_metni == "MÜSAIT" or durum_metni == "BOŞ":
                lbl_durum.setStyleSheet("color: #2ecc71; font-weight: bold;")
            else:
                lbl_durum.setStyleSheet("color: #e74c3c; font-weight: bold;")

# İlk açılışta veritabanından çekip arayüze bas
arayuzu_db_ile_guncelle()

for i in range(1, 7):
    btn = getattr(pencere, f"btn_islem_{i}", None)
    if btn:
        btn.clicked.connect(lambda checked, no=str(i): oda_butonuna_basildi(no))

rezervasyon_dialog.btn_kaydet.clicked.connect(rezervasyonu_kaydet)
rezervasyon_dialog.btn_iptal.clicked.connect(rezervasyon_dialog.close)

pencere.show()
sys.exit(app.exec())