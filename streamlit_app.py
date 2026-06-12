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
# --- SELENIUM İÇİN GELİŞMİŞ GİZLENMİŞ (ANTI-BOT) SÜRÜCÜ AYARI ---
@st.cache_resource
def get_selenium_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    # 🕵️ GÜVENLİK DUVARLARINI AŞMA VE GİZLENME AYARLARI:
    # Sitenin bizi otomasyon yazılımı (bot) olarak görmesini engeller
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Gerçek bir kullanıcı gibi davranması için sahte Tarayıcı Kimliği (User-Agent) tanımlıyoruz
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        servis = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=servis, options=chrome_options)
        
        # Tarayıcıya "ben bot değilim" imzasını yerleştiriyoruz
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver
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
# --- ADINI ANMADIĞIMIZ SİTEDEN VERİ ÇEKME MOTORU ---
def gizli_siteden_karar_ara(aranacak_kelime):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    # 🕵️ Gelişmiş Gizlilik ve Cloudflare Atlama Ayarları
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    # Güncel ve temiz bir kullanıcı kimliği tanımlıyoruz
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    chrome_options.add_argument("--lang=tr-TR")

    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        
        servis = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=servis, options=chrome_options)
        
        # Tarayıcının otomasyon imzasını tamamen sıfırlıyoruz
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        # Siteye giriş yap
        driver.get("https://yargitay.gov.tr")
        
        # Sayfa içeriğinin render edilmesi için ekstra 3 saniye kemiksiz bekleme süresi
        time.sleep(3)
        
        # 🎯 ELEMENT BULMA STRATEJİSİ: Tek bir Xpath yerine esnek alternatifler deniyoruz
        arama_kutusu = None
        alternatif_xpathler = [
            "//input[contains(@placeholder, 'Anahtar')]",
            "//input[@type='text']",
            "//input[contains(@class, 'form-control')]",
            "//input"
        ]
        
        for xpath in alternatif_xpathler:
            try:
                arama_kutusu = driver.find_element(By.XPATH, xpath)
                if arama_kutusu.is_displayed():
                    break
            except:
                continue
                
        if not arama_kutusu:
            driver.quit()
            return "Siteye bağlanıldı ancak arama girdi kutusu (input) sistem tarafından tespit edilemedi. Site yapısı değişmiş olabilir."
            
        # Temizle ve kelimeyi yaz
        arama_kutusu.clear()
        for harf in aranacak_kelime:
            arama_kutusu.send_keys(harf)
            time.sleep(0.05) # Yazma hızını hafifçe hızlandırdık
            
        # 🎯 BUTON BULMA STRATEJİSİ
        ara_butonu = None
        buton_xpathler = [
            "//button[contains(text(), 'Ara')]",
            "//button[contains(@class, 'btn')]",
            "//button[@type='button']",
            "//span[contains(text(), 'Ara')]"
        ]
        
        for b_xpath in buton_xpathler:
            try:
                ara_butonu = driver.find_element(By.XPATH, b_xpath)
                if ara_butonu.is_displayed():
                    break
            except:
                continue
                
        if not ara_butonu:
            driver.quit()
            return "Arama kutusuna veri yazıldı ancak tıklanacak 'Ara' butonu bulunamadı."
            
        # Butona tıkla
        driver.execute_script("arguments[0].click();", ara_butonu)
        
        # Sonuçların yüklenmesi için 6 saniye bekle
        time.sleep(6)
        
        # Sayfadaki ham metni veya sonuç tablolarını yakala
        # Spasifik class ismi yerine tüm sayfa gövdesindeki (body) değişimi okuyoruz
        sayfa_metni = driver.find_element(By.TAG_NAME, "body").text
        
        driver.quit()
        
        # Eğer sayfada sonuç bulunamadı uyarısı varsa veya metin çok kısaysa kontrol et
        if "Adet Karar Mevcuttur" in sayfa_metni or len(sayfa_metni) < 500:
            return "Arama tetiklendi fakat arama kriterlerine uygun resmi bir karar listelenmedi veya boş sonuç döndü."
            
        # Ham veriyi temizle ve ilk 1500 karakterini özetlemesi için yapay zekaya gönder
        temiz_ozet = re.sub(r'\s+', ' ', sayfa_metni).strip()
        return temiz_ozet[:1500]
            
    except Exception as e:
        if 'driver' in locals(): driver.quit()
        # Detaylı hata mesajı yerine temiz ve anlaşılır bir geri bildirim veriyoruz
        return f"Resmi kurum sitesinin güvenlik duvarı (Cloudflare/Bot Engelleyici) veya sunucu yoğunluğu nedeniyle bağlantı zaman aşımına uğradı."

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
st.write(f"Şu anki mod: **{kisilik}** | normal bir yapay zeka, çok bişi beklemeyin")

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
# --- 6. İŞLETME DÖNGÜSÜ (KESİN RESMİ VERİ ODAKLI) ---
if soru_girdisi := st.chat_input("Mesajınızı buraya yazın..."):
    with st.chat_message("user"):
        st.write(soru_girdisi)
    st.session_state.mesaj_gecmisi.append({"role": "user", "content": soru_girdisi})

    with st.chat_message("assistant"):
        # Durum kontrol bayrağı (Resmi siteye girildi mi?)
        resmi_site_aktif = False
        
        if yapistirilan_metin:
            internet_bilgisi = None
            st.caption("⚡ Seçilen karar metni yapay zeka tarafından inceleniyor...")
        else:
            # 🎯 RESMİ SİTEYİ TETİKLEYECEK KESİN ANAHTAR KELİMELER
            site_tetikleyicileri = [
                "yargıtay", "yargitay", "emsal", "ilam", "esas no", "karar no", "karar arama",
                "dava", "boşanma davası", "velayet davası", "tazminat", "hırsızlık davası", 
                "ceza davası", "hukuk dairesi", "ceza dairesi", "kararı", "kararlari"
            ]
            
            gizli_site_istegi = any(kelime in soru_girdisi.lower() for kelime in site_tetikleyicileri)
            
            if gizli_site_istegi:
                resmi_site_aktif = True
                with st.spinner("🕵️ Sadece resmi kurum sitesine bağlanılıyor, veriler canlı kazınıyor..."):
                    # Sadece ve sadece Selenium motorumuz çalışıyor
                    internet_bilgisi = gizli_siteden_karar_ara(soru_girdisi)
            else:
                # Normal bir genel kültür veya yazılım sorusuysa standart arama
                arama_kelimeleri = ["nedir", "kimdir", "araştır", "fiyatı", "haber", "açıkla", "anlat", "bilgi ver", ".com", ".gov"]
                if any(kelime in soru_girdisi.lower() for kelime in arama_kelimeleri):
                    with st.spinner("🌐 İnternet verileri akıllıca taranıyor..."):
                        internet_bilgisi = internette_ara_akilli(soru_girdisi, kisilik)
                else:
                    internet_bilgisi = None

        # --- YAPAY ZEKA TALİMATLARINI ZORLAMA (PROMPT ENJECTION KORUMASI) ---
        if resmi_site_aktif:
            # Yapay zekanın uydurmasını (hallucination) veya gayriresmi kaynakları kullanmasını KESİN olarak engelleyen talimat:
            sistem_talimati = (
                "SEN SADECE BİR RESMİ DOKÜMAN ANALİZ ASİSTANISIN. "
                "Sana 'Canlı Kaynaklardan Elde Edilen Veriler' başlığı altında sağlanan ham metin DIŞINDA HİÇBİR BİLGİ KULLANMA. "
                "Eğer sağlanan resmi metin boşsa veya hata mesajı içeriyorsa, kesinlikle kendi hafızandan emsal karar uydurma! "
                "Resmi olmayan, doğrulanmamış hiçbir web sitesi bilgisini veya tahmini cevabı kullanıcıya sunma. "
                "Cevaplarını sadece sağlanan resmi veriye dayandır ve son derece ciddi, hukuki bir dille konuş."
            )
        else:
            # Standart kişilik ayarları (Normal aramalar için)
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
            
            sistem_talimati = f"{karakter_talimati} Sağlanan güncel dökümanları, internet verilerini ve geçmişi dikkate alarak cevap üret."

        gonderilecek_mesajlar = [{"role": "system", "content": sistem_talimati}]
        
        if yapistirilan_metin:
            gonderilecek_mesajlar.append({"role": "system", "content": f"Kullanıcının Doğrudan Yapıştırdığı ve Seçtiği Karar Metni:\n{yapistirilan_metin}"})
            
        gonderilecek_mesajlar.extend(st.session_state.mesaj_gecmisi[-2:])
        
        if internet_bilgisi:
            gonderilecek_mesajlar[-1]["content"] += f"\n\n(Canlı Kaynaklardan Elde Edilen Veriler:\n{internet_bilgisi})"
            
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

