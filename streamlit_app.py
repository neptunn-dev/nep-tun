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

def hukuk_karar_analizi(karar_metni):
    if not karar_metni:
        return "Lütfen analiz edilmek üzere bir karar metni yapıştırın."
    return None 

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
       # --- ÖZEL MOD: İNTERNET ARAŞTIRMACISI İÇİN YARGITAY ANALİZ PANELİ ---
if kisilik == "İnternet Araştırmacısı (Ajan)":
    st.info("⚖️ Yargıtay ve Hukuki Karar Analiz Paneli Aktif!")
    
    st.markdown("""
    **Karar Analiz Adımları:**
    1. [Yargıtay Karar Arama Sitesi'ne Gidin](https://karararama.yargitay.gov.tr/)
    2. İncelemek istediğiniz kararın içeriğini kopyalayın.
    3. Aşağıdaki kutuya yapıştırın ve ardından en alttaki sohbet kutusundan yapay zekaya dilediğiniz soruyu sorun!
    """)
    
    st.subheader("⚖️ Karar Metnini Yapıştır")
    hukuk_metni = st.text_area(
        "Kopyaladığınız hukuki kararı buraya ekleyin:", 
        height=200, 
        placeholder="Yargıtay ilam metnini buraya yapıştırın...",
        key="yargitay_karar_kutusu"
    )
    
    # Kullanıcı metin yapıştırırsa arka plan hafızasına aktarır
    if hukuk_metni:
        yapistirilan_metin = hukuk_metni
            )
        else:
            karakter_talimati = "Sen kibar, zeki ve yardımcı bir yapay zeka asistanısın."

        sistem_talimati = f"{karakter_talimati} Sağlanan güncel dökümanları ve geçmişi dikkate alarak cevap üret."
        gonderilecek_mesajlar = [{"role": "system", "content": sistem_talimati}]
        
        if yapistirilan_metin:
            gonderilecek_mesajlar.append({"role": "system", "content": f"Kullanıcının Doğrudan Yapıştırdığı Metin İçeriği:\n{yapistirilan_metin}"})
        elif dosya_icerigi:
            gonderilecek_mesajlar.append({"role": "system", "content": f"Dosya içeriği:\n{dosya_icerigi}"})
            
        gonderilecek_mesajlar.extend(st.session_state.mesaj_gecmisi[-2:])
        
        if internet_bilgisi:
            gonderilecek_mesajlar[-1]["content"] += f"\n\n(İnternet Bilgisi:\n{internet_bilgisi})"
            
        try:
            cevap = groq_istenci.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=gonderilecek_mesajlar,
                temperature=0.2
            )
            yanit = cevap.choices[0].message.content
            
            st.write(yanit)
            st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": yanit})
            
            ses_metni = re.sub(r'[^\w\s,.!?:\(\)\-\"\']', '', yanit)
            with st.spinner("🔊 Ses dosyası hazırlanıyor..."):
                tts = gTTS(text=ses_metni[:300], lang='tr', tld='com.tr')
                tts.save("cevap.mp3")
                st.audio("cevap.mp3", format="audio/mp3")
                
        except Exception as e:
            st.warning("⚠️ Küçük bir yoğunluk kısıtlaması oldu. Lütfen birkaç saniye sonra tekrar gönderin.")
