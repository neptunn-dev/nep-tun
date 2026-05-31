import asyncio
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

# --- AKILLI BOT TRAFİK POLİSİ FONKSİYONU ---
def otomatik_arama_kutusu_secici(soru_metni):
    """
    Babanın yazdığı soruya göre sitenin hangi arama kutusuna 
    tıklanması gerektiğini çözen akıllı yönlendirici mantık.
    """
    soru = soru_metni.lower()
    
    # Detaylı arama gerektiren anahtar kelimeler
    detayli_kriterler = ["daire", "hukuk", "ceza", "tazminat", "esas no", "karar no", "hırsızlık", "boşanma", "velayet"]
    
    # Eğer soruda bu detaylı kelimelerden biri geçiyorsa
    if any(kelime in soru for kelime in detayli_kriterler):
        return {
            "kutu": "Detaylı Arama Kutusu (Gelişmiş Filtre)",
            "renk": "orange",
            "ikon": "🔍",
            "id": "detayli_arama_input"
        }
    else:
        return {
            "kutu": "Normal Arama Kutusu (Hızlı Sorgu)",
            "renk": "blue",
            "ikon": "⚡",
            "id": "normal_arama_input"
        }

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

# Ana Sayfa Başlıkları
st.title("🚀 Mega Yapay Zeka İstasyonu")
st.write(f"Şu anki mod: **{kisilik}** | İnternette arar, yapıştırılan metinleri doğrudan inceler!")

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

# --- ORTAK METİN ALANI (KİŞİLİĞE GÖRE DEĞİŞİR) ---
yapistirilan_metin = ""

if kisilik == "İnternet Araştırmacısı (Ajan)":
    st.info("⚖️ Yargıtay ve Hukuki Karar Analiz Paneli Aktif!")
    
    st.markdown("""
    **Karar Analiz Adımları:**
    1. İncelemek istediğiniz kararları kopyalayın.
    2. Aşağıdaki büyük kutuya yapıştırın. Birden fazla karar varsa sistem size seçtirecektir!
    """)
    
    hukuk_metni = st.text_area(
        "Kopyaladığınız hukuki kararları buraya ekleyin:", 
        height=200, 
        placeholder="Yargıtay ilam metinlerini buraya yapıştırın...",
        key="ana_yargitay_kutusu"
    )
    
    if hukuk_metni:
        karar_parcalari = [p.strip() for p in re.split(r'(?i)(?=T\.C\.|YARGITAY)', hukuk_metni) if len(p.strip()) > 30]
        
        if len(karar_parcalari) <= 1 and hukuk_metni.count("Esas No") > 1:
            karar_parcalari = [p.strip() for p in re.split(r'(?i)(?=Esas No)', hukuk_metni) if len(p.strip()) > 30]

        if len(karar_parcalari) > 1:
            st.warning(f"📋 Kutuda {len(karar_parcalari)} farklı karar tespit ettim!")
            
            secenekler = {}
            for i, parca in enumerate(karar_parcalari):
                temiz_baslik = re.sub(r'\s+', ' ', parca).strip()
                baslik = f"⚖️ {i+1}. Karar: {temiz_baslik[:70]}..."
                secenekler[baslik] = parca
                
            secilen_baslik = st.radio("Baba, hangisini analiz edeyim? Seçebilirsin:", list(secenekler.keys()))
            yapistirilan_metin = secenekler[secilen_baslik]
        else:
            yapistirilan_metin = hukuk_metni
else:
    with st.sidebar:
        st.subheader("📝 İnceleme Metni Yapıştır")
        yapistirilan_metin = st.text_area("Metin İçeriği:", height=200, placeholder="Uzun metni buraya yapıştırın...", key="standart_kutu")

st.write("---")

# Eski Mesajları Ekrana Basma
for mesaj in st.session_state.mesaj_gecmisi:
    with st.chat_message(mesaj["role"]):
        st.write(mesaj["content"])

# Kullanıcıdan girdi alma ve işletme döngüsü
if soru_girdisi := st.chat_input("Mesajınızı buraya yazın..."):
    
    with st.chat_message("user"):
        st.write(soru_girdisi)
    st.session_state.mesaj_gecmisi.append({"role": "user", "content": soru_girdisi})

    # --- ARKA PLAN SEÇİM MANTIĞI SESSİZCE ÇALIŞIR ---
    # İleride Selenium bota bağlandığında bu değişken kullanılacak, ekrana bir şey basılmayacak.
    karar_durumu = otomatik_arama_kutusu_secici(soru_girdisi)

    with st.chat_message("assistant"):
        if yapistirilan_metin:
            internet_bilgisi = None
            st.caption("⚡ Seçilen karar metni yapay zeka tarafından inceleniyor...")
        else:
            arama_kelimeleri = ["nedir", "kimdir", "araştır", "fiyatı", "haber", "açıkla", "anlat", "bilgi ver", ".com", ".gov"]
            internet_gerekli = any(kelime in soru_girdisi.lower() for kelime in arama_kelimeleri)
            if internet_gerekli:
                with st.spinner("🌐 İnternet verileri taranıyor..."):
                    internet_bilgisi = internette_ara(soru_girdisi)
            else:
                internet_bilgisi = None

        # Karakter Kişilik Ayarları
        if kisilik == "İnternet Araştırmacısı (Ajan)":
            karakter_talimati = "Sen uzman bir hukuk dedektifi and internet araştırmacısısın. Kararları hukuki terimlerle analiz et."
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
