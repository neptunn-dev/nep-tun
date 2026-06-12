import asyncio
import os
import re
import subprocess
import streamlit as st
from groq import Groq
from tavily import TavilyClient
from gtts import gTTS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from playwright.async_api import async_playwright

# --- 1. API ANAHTARLARI VE BAŞLATMA ---
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]

groq_istenci = Groq(api_key=GROQ_API_KEY)
tavily_istenci = TavilyClient(api_key=TAVILY_API_KEY)

st.set_page_config(page_title="Mega Yapay Zeka İstasyonu", page_icon="🚀", layout="wide")

if "mesaj_gecmisi" not in st.session_state:
    st.session_state.mesaj_gecmisi = []

# --- 2. MULTI-BOT SÜRÜCÜ AYARLARI (SELENIUM & PLAYWRIGHT) ---

# Playwright Sürücü Yükleyici
@st.cache_resource
def install_playwright_browsers():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        pass

install_playwright_browsers()

# Selenium Driver Başlatıcı
@st.cache_resource
def get_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/chromium"
    try:
        servis = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=servis, options=chrome_options)
    except Exception as e:
        st.error(f"Selenium Driver başlatılamadı: {e}")
        return None

# Örnek Playwright Fonksiyonu (İhtiyaç anında çağırmak için hazır)
async def internetten_veri_cek_playwright(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        icerik = await page.title()
        await browser.close()
        return icerik

# --- 3. AKILLI İNTERNET ARAMA (TAVILY) ---
def internette_ara_akilli(soru, kisilik_modu):
    try:
        temiz_soru = soru.lower()
        temiz_soru = re.sub(r'https?://[^\s]+', '', temiz_soru)
        temiz_soru = temiz_soru.replace("yargitay", "").replace("yargıtay", "").replace("gov.tr", "").strip()
        
        detayli_kriterler = ["daire", "hukuk", "ceza", "tazminat", "esas no", "karar no", "hırsızlık", "boşanma", "velayet"]
        
        if any(kelime in temiz_soru for kelime in detayli_kriterler) or kisilik_modu == "İnternet Araştırmacısı (Ajan)":
            arama_sorgusu = f"Yargıtay {temiz_soru[:100]} kesin karar metni emsal ilam"
            derinlik = "advanced"
            sonuc_sayisi = 3
        else:
            arama_sorgusu = f"{temiz_soru[:100]} nedir bilgi"
            derinlik = "basic"
            sonuc_sayisi = 2
            
        arama_sonucu = tavily_istenci.search(query=arama_sorgusu, max_results=sonuc_sayisi, search_depth=derinlik)

        metinler = []
        for sonuc in arama_sonucu["results"]:
            icerik = sonuc.get('content') or "İçerik yok"
            icerik_temiz = re.sub(r'\s+', ' ', icerik).strip()
            metinler.append(f"- {sonuc['title']} ({sonuc['url']}): {icerik_temiz[:600]}")
                
        return "\n".join(metinler)
    except Exception:
        return None

# --- 4. SOL MENÜ (SIDEBAR) ---
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
    
    st.subheader("💾 Raporu İndir")
    if st.session_state.mesaj_gecmisi:
        sohbet_metni = ""
        for mesaj in st.session_state.mesaj_gecmisi:
            rol = "Kullanıcı" if mesaj["role"] == "user" else "Yapay Zeka"
            sohbet_metni += f"{rol}: {mesaj['content']}\n\n"
        st.download_button(label="📄 Sohbeti Not Olarak İndir", data=sohbet_metni, file_name="sohbet_ozeti.txt", mime="text/plain", use_container_width=True)

# --- 5. ANA SAYFA VE METİN ALANI ---
st.title("🚀 Mega Yapay Zeka İstasyonu")
st.write(f"Şu anki mod: **{kisilik}** | İnternette arar, yapıştırılan metinleri doğrudan inceler!")

yapistirilan_metin = ""

if kisilik == "İnternet Araştırmacısı (Ajan)":
    st.info("⚖️ Yargıtay ve Hukuki Karar Analiz Paneli Aktif!")
    hukuk_metni = st.text_area("Kopyaladığınız hukuki kararları buraya ekleyin:", height=200, placeholder="Yargıtay ilam metinlerini buraya yapıştırın...", key="ana_yargitay_kutusu")
    
    if hukuk_metni:
        karar_parcalari = [p.strip() for p in re.split(r'(?i)(?=T\.C\.|YARGITAY)', hukuk_metni) if len(p.strip()) > 30]
        if len(karar_parcalari) <= 1 and hukuk_metni.count("Esas No") > 1:
            karar_parcalari = [p.strip() for p in re.split(r'(?i)(?=Esas No)', hukuk_metni) if len(p.strip()) > 30]

        if len(karar_parcalari) > 1:
            st.warning(f"📋 Kutuda {len(karar_parcalari)} farklı karar tespit ettim!")
            secenekler = {}
            for i, parca in enumerate(karar_parcalari):
                temiz_baslik = re.sub(r'\s+', ' ', parca).strip()
                secenekler[f"⚖️ {i+1}. Karar: {temiz_baslik[:70]}..."] = parca
            secilen_baslik = st.radio("Baba, hangisini analiz edeyim? Seçebilirsin:", list(secenekler.keys()))
            yapistirilan_metin = secenekler[secilen_baslik]
        else:
            yapistirilan_metin = hukuk_metni
else:
    with st.sidebar:
        st.subheader("📝 İnceleme Metni Yapıştır")
        yapistirilan_metin = st.text_area("Metin İçeriği:", height=200, placeholder="Uzun metni buraya yapıştırın...", key="standart_kutu")

st.write("---")

for mesaj in st.session_state.mesaj_gecmisi:
    with st.chat_message(mesaj["role"]):
        st.write(mesaj["content"])

# --- 6. İŞLETME DÖNGÜSÜ (GROQ & gTTS) ---
if soru_girdisi := st.chat_input("Mesajınızı buraya yazın..."):
    with st.chat_message("user"):
        st.write(soru_girdisi)
    st.session_state.mesaj_gecmisi.append({"role": "user", "content": soru_girdisi})

    with st.chat_message("assistant"):
        if yapistirilan_metin:
            internet_bilgisi = None
            st.caption("⚡ Seçilen karar metni yapay zeka tarafından inceleniyor...")
        else:
            arama_kelimeleri = ["nedir", "kimdir", "araştır", "fiyatı", "haber", "açıkla", "anlat", "bilgi ver", ".com", ".gov", "esas", "karar", "daire"]
            if any(kelime in soru_girdisi.lower() for kelime in arama_kelimeleri):
                with st.spinner("🌐 İnternet verileri akıllıca taranıyor..."):
                    internet_bilgisi = internette_ara_akilli(soru_girdisi, kisilik)
            else:
                internet_bilgisi = None

        if kisilik == "İnternet Araştırmacısı (Ajan)":
            karakter_talimati = "Sen uzman bir hukuk dedektifi ve internet araştırmacısısın. Kararları hukuki terimlerle analiz et."
        elif kisilik == "Bilim İnsanı":
            karakter_talimati = "Sen analitik düşünen, verilere dayalı konuşan bir bilim insanısın."
        elif kisilik == "Mahalle Arkadaşı (Kanka)":
            karakter_talimati = "Sen samimi, cana yakın ve çok içten bir mahalle arkadaşısın. Argoya kaçmadan sıcak bir dille konuş."
        elif kisilik == "Yazılımcı Mentoru":
            karakter_talimati = "Sen junior yazılımcılara rehberlik eden kıdemli bir yazılımcı mentorusun."
        else:
            karakter_talimati = "Sen kibar, zeki ve yardımcı bir yapay zeka asistanısın."

        sistem_talimati = f"{karakter_talimati} Sağlanan güncel dökümanları ve geçmişi dikkate alarak cevap üret."
        gonderilecek_mesajlar = [{"role": "system", "content": sistem_talimati}]
        
        if yapistirilan_metin:
            gonderilecek_mesajlar.append({"role": "system", "content": f"Kullanıcının Doğrudan Yapıştırdığı ve Seçtiği Karar Metni:\n{yapistirilan_metin}"})
            
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

