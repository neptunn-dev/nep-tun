import asyncio
from playwright.async_api import async_playwright
import streamlit as st
from groq import Groq
from tavily import TavilyClient
from gtts import gTTS
import os
import re

# API Anahtarlarını Streamlit Secrets üzerinden alıyoruz
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]

groq_istenci = Groq(api_key=GROQ_API_KEY)
tavily_istenci = TavilyClient(api_key=TAVILY_API_KEY)

st.set_page_config(page_title="Mega Yapay Zeka İstasyonu", page_icon="🚀", layout="wide")

# Hafıza Kurulumu
if "mesaj_gecmisi" not in st.session_state:
    st.session_state.mesaj_gecmisi = []

# --- SOL MENÜ (SIDEBAR) AYARLARI ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    
    if st.button("🗑️ Sohbeti Temizle", use_container_width=True):
        st.session_state.mesaj_gecmisi = []
        st.rerun()
        
    st.write("---")
    
    kisilik = st.selectbox(
        "🤖 Asistan Kişiliği Seçin:",
        ["Standart Asistan", "İnternet Araştırmacısı (Ajan)", "Bilim İnsanı", "Mahalle Arkadaşı (Kanka)", "Yazılımcı Mentoru"]
    )
    
    st.write("---")
    
    # METİN YAPIŞTIRMA ALANI (DÜMDÜZ METİN YAPTIK)
    st.subheader("📝 İnceleme Metni Yapıştır")
    st.caption("İnternette bulunamayan uzun metinleri buraya yapıştırıp aşağıdan soru sorabilirsiniz:")
    yapistirilan_metin = st.text_area("Metin İçeriği:", height=250, placeholder="Uzun metni buraya yapıştırın...")
    
    st.write("---")
    
    st.subheader("💾 Raporu İndir")
    if st.session_state.mesaj_gecmisi:
        sohbet_metni = ""
        for mesaj in st.session_state.mesaj_gecmisi:
            rol = "Kullanıcı" if mesaj["role"] == "user" else "Yapay Zeka"
            sohbet_metni += f"{rol}: {mesaj['content']}\n\n"
            
        st.download_button(
            label="📄 Sohbeti Not Olarak İndir",
            data=sohbet_metni,
            file_name="sohbet_ozeti.txt",
            mime="text/plain",
            use_container_width=True
        )
        
    # Dosya Yükleme Alanı
    yuklenen_dosya = st.file_uploader("Veya metin dosyası yükleyin:", type=["txt"])
    dosya_icerigi = ""
    if yuklenen_dosya is not None:
        try:
            dosya_icerigi = yuklenen_dosya.read().decode("utf-8")
            st.success("Dosya başarıyla okundu!")
        except Exception:
            st.error("Dosya okunurken bir hata oluştu.")

# Ana Sayfa Başlıkları
st.title("🚀 Mega Yapay Zeka İstasyonu")
st.write(f"Şu anki mod: **{kisilik}** | İnternette arar, yapıştırılan metinleri doğrudan inceler!")

# --- PLAYWRIGHT ASENKRON FONKSİYONU (DOĞRU YERE ALINDI) ---
async def yargitay_karar_cek(daire_adi, esas_no, karar_no):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = await browser.new_page()
            await page.goto("https://karararama.yargitay.gov.tr/", timeout=60000)
            await page.wait_for_load_state("networkidle")
            title = await page.title()
            await browser.close()
            return f"Yargıtay Canlı Bağlantı Testi Başarılı! Sayfa Başlığı: {title}"
    except Exception as e:
        return f"Yargıtay bağlantı hatası oluştu: {str(e)}"

# KOTA DOSTU ARAMA FONKSİYONU
def internette_ara(soru, gelismis_mod=False):
    try:
        temiz_soru = soru.lower()
        temiz_soru = re.sub(r'https?://[^\s]+', '', temiz_soru)
        temiz_soru = temiz_soru.replace("yargitay", "").replace("yargıtay", "").replace("gov.tr", "").strip()
        
        optimize_soru = temiz_soru[:100].strip()
        if not optimize_soru:
            return None
            
        arama_parametreleri = {
            "query": f"{optimize_soru} detaylı bilgi",
            "max_results": 2, 
            "search_depth": "advanced"
        }
        arama_sonucu = tavily_istenci.search(**arama_parametreleri)

        metinler = []
        for sonuc in arama_sonucu["results"]:
            icerik = sonuc.get('content') or "İçerik yok"
            icerik_temiz = re.sub(r'\s+', ' ', icerik).strip()
            metinler.append(f"- {sonuc['title']} ({sonuc['url']}): {icerik_temiz[:600]}")
                
        return "\n".join(metinler)
    except Exception:
        return None

# --- ÖZEL MOD: İNTERNET ARAŞTIRMACISI İÇİN YARGITAY PANELİ ---
if kisilik == "İnternet Araştırmacısı (Ajan)":
    st.info("⚖️ Yargıtay Canlı Karar Sorgulama Paneli Aktif!")
    col1, col2, col3 = st.columns(3)
    with col1:
        daire = st.text_input("Daire Adı", value="11. Hukuk Dairesi")
    with col2:
        esas = st.text_input("Esas No (Yıl/Sıra)", value="2019/4530")
    with col3:
        karar = st.text_input("Karar No (Yıl/Sıra)", value="2021/4133")
        
    if st.button("🔍 Playwright ile Yargıtay'ı Canlı Sorgula", type="primary"):
        with st.spinner("Playwright arka planda Yargıtay sitesine bağlanıyor..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            sorgu_sonucu = loop.run_until_complete(yargitay_karar_cek(daire, esas, karar))
            st.success(sorgu_sonucu)

st.write("---")

# Eski Mesajları Ekrana Basma
for mesaj in st.session_state.mesaj_gecmisi:
    with st.chat_message(mesaj["role"]):
        st.write(mesaj["content"])

# Kullanıcıdan girdi alma
if soru_girdisi := st.chat_input("Mesajınızı buraya yazın..."):
    
    with st.chat_message("user"):
        st.write(soru_girdisi)
    st.session_state.mesaj_gecmisi.append({"role": "user", "content": soru_girdisi})

    with st.chat_message("assistant"):
        if yapistirilan_metin:
            internet_bilgisi = None
            st.caption("⚡ Sol menüye yapıştırılan metin inceleniyor...")
        else:
            arama_kelimeleri = ["nedir", "kimdir", "araştır", "fiyatı", "haber", "açıkla", "anlat", "bilgi ver", ".com", ".gov"]
            internet_gerekli = any(kelime in soru_girdisi.lower() for kelime in arama_kelimeleri)
            if internet_gerekli:
                with st.spinner("🌐 İnternet verileri taranıyor..."):
                    internet_bilgisi = internette_ara(soru_girdisi)
            else:
                internet_bilgisi = None

        # Karakter Talimatı
        if kisilik == "
