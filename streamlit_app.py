import streamlit as st
from groq import Groq
from tavily import TavilyClient
from gtts import gTTS
import os

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
    
    # Sohbeti Temizle Butonu
    if st.button("🗑️ Sohbeti Temizle", use_container_width=True):
        st.session_state.mesaj_gecmisi = []
        st.rerun()
        
    st.write("---")
    
    # Kişilik Seçme Menüsü
    kisilik = st.selectbox(
        "🤖 Asistan Kişiliği Seçin:",
        ["Standart Asistan", "Bilim İnsanı", "Mahalle Arkadaşı (Kanka)", "Yazılımcı Mentoru"]
    )
    
    st.write("---")
    
    # PDF / Dosya Yükleme Alanı
    st.subheader("📁 Döküman Analizi")
    yuklenen_dosya = st.file_uploader("Bir metin dosyası yükleyin:", type=["txt"])
    dosya_icerigi = ""
    if yuklenen_dosya is not None:
        try:
            dosya_icerigi = yuklenen_dosya.read().decode("utf-8")
            st.success("Dosya başarıyla okundu!")
        except Exception:
            st.error("Dosya okunurken bir hata oluştu (Şimdilik sadece .txt destekleniyor).")

# Ana Sayfa Başlıkları
st.title("🚀 Mega Yapay Zeka İstasyonu")
st.write(f"Şu anki mod: **{kisilik}** | Geçmişi hatırlar, internette arar, dosya okur ve sesli konuşur!")

# Eski mesajları ekranda göster
for mesaj in st.session_state.mesaj_gecmisi:
    with st.chat_message(mesaj["role"]):
        st.write(mesaj["content"])

# İnternet arama fonksiyonu
def internette_ara(soru):
    try:
        arama_sonucu = tavily_istenci.search(query=soru, max_results=3)
        metinler = [sonuc["content"] for sonuc in arama_sonucu["results"]]
        return "\n".join(metinler)
    except Exception:
        return None

# Kullanıcıdan girdi alma
if soru_girdisi := st.chat_input("Mesajınızı buraya yazın..."):
    
    # Kullanıcı mesajını ekrana bas ve hafızaya kaydet
    with st.chat_message("user"):
        st.write(soru_girdisi)
    st.session_state.mesaj_gecmisi.append({"role": "user", "content": soru_girdisi})

    with st.chat_message("assistant"):
        # Akıllı internet arama tespiti
        arama_kelimeleri = ["nedir", "kimdir", "araştır", "fiyatı", "haber", "hava durumu", "ne zaman", "son dakika", "açıkla", "anlat", "bilgi ver"]
        internet_gerekli = any(kelime in soru_girdisi.lower() for kelime in arama_kelimeleri)
        
        if internet_gerekli:
            with st.spinner("🌐 İnternet taranıyor..."):
                internet_bilgisi = internette_ara(soru_girdisi)
        else:
            internet_bilgisi = None

        # Kişiliklere göre sistem talimatı belirleme
        if kisilik == "Bilim İnsanı":
            karakter_talimati = "Sen ciddi, akademik, tamamen bilimsel verilere dayanan ve detaylı açıklamalar yapan bir bilim insanısın. Cevaplarında bolca bilimsel emoji kullan."
        elif kisilik == "Mahalle Arkadaşı (Kanka)":
            karakter_talimati = "Sen kullanıcının çok yakın bir mahalle arkadaşısın. Samimi, esprili konuş, 'kanka', 'reis', 'brom' gibi kelimeler kullan, asla resmi olma. Bol bol gülen ve eğlenceli emojiler koy."
        elif kisilik == "Yazılımcı Mentoru":
            karakter_talimati = "Sen tecrübeli bir yazılım liderisin. Kullanıcıya kodlama konusunda rehberlik et, motive et ve teknik ama anlaşılır konuş. Kod blokları ve teknoloji emojileri kullan."
        else:
            karakter_talimati = "Sen kibar, zeki ve yardımcı bir yapay zeka asistanısın. Cevaplarında uygun emojiler kullanmayı unutma."

        sistem_talimati = (
            f"{karakter_talimati} Sana sağlanan internet bilgilerini ve konuşma geçmişini dikkate alarak cevap üret."
        )
        
        gonderilecek_mesajlar = [{"role": "system", "content": sistem_talimati}]
        
        # Eğer yüklenmiş bir dosya varsa ekliyoruz
        if dosya_icerigi:
            gonderilecek_mesajlar.append({"role": "system", "content": f"Kullanıcının yüklediği dosya içeriği şudur:\n{dosya_icerigi}"})
            
        gonderilecek_mesajlar.extend(st.session_state.mesaj_gecmisi)
        
        if internet_bilgisi:
            gonderilecek_mesajlar[-1]["content"] += f"\n\n(Güncel İnternet Bilgisi: {internet_bilgisi})"
            
        try:
            cevap = groq_istenci.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=gonderilecek_mesajlar
            )
            yanit = cevap.choices[0].message.content
            
            # Cevabı ekrana yazdır
            st.write(yanit)
            st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": yanit})
            
            # Sesli Okuma (Text-to-Speech)
            with st.spinner("🔊 Ses dosyası hazırlanıyor..."):
                tts = gTTS(text=yanit[:300], lang='tr')
                tts.save("cevap.mp3")
                st.audio("cevap.mp3", format="audio/mp3")
                
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
