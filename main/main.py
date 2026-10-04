import os
import sys
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

def arayuzu_db_ile_guncelle():
    # 1. Gerçek veriyi SQLite'tan çek
    odalar_verisi = database.arayuz_icin_odalari_getir()

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

pencere.show()
sys.exit(app.exec())