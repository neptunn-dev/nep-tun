import streamlit as st
from groq import Groq
from tavily import TavilyClient

# API Anahtarlarını Streamlit Secrets üzerinden alıyoruz
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]

groq_istenci = Groq(api_key=GROQ_API_KEY)
tavily_istenci = TavilyClient(api_key=TAVILY_API_KEY)

st.set_page_config(page_title="Yapay Zeka Asistanı", page_icon="🤖")
st.title("🤖 Gelişmiş Yapay Zeka Asistanı")
st.write("Benimle hem sohbet edebilirsin hem de benden bir şeyleri araştırmamı veya açıklamamı isteyebilirsin!")

# Hafıza Kurulumu
if "mesaj_gecmisi" not in st.session_state:
    st.session_state.mesaj_gecmisi = []

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
if soru_girdisi := st.chat_input("Mesajınızı yazın..."):
    
    # Kullanıcı mesajını ekrana bas ve hafızaya kaydet
    with st.chat_message("user"):
        st.write(soru_girdisi)
    st.session_state.mesaj_gecmisi.append({"role": "user", "content": soru_girdisi})

    with st.chat_message("assistant"):
        # Gelişmiş Arama ve Açıklama Kelimeleri Listesi
        arama_kelimeleri = [
            "nedir", "kimdir", "araştır", "fiyatı", "haber", "hava durumu", 
            "ne zaman", "son dakika", "açıkla", "anlat", "bilgi ver", "nasıldır"
        ]
        
        # Kullanıcının yazdığı cümlede bu kelimelerden biri geçiyor mu kontrol et
        internet_gerekli = any(kelime in soru_girdisi.lower() for kelime in arama_kelimeleri)
        
        if internet_gerekli:
            with st.spinner("İnternette güncel kaynaklar araştırılıyor ve hazırlanıyor..."):
                internet_bilgisi = internette_ara(soru_girdisi)
        else:
            internet_bilgisi = None

        # Sistem Talimatı
        sistem_talimati = (
            "Sen arkadaş canlısı, zeki, esnek ve yardımcı bir yapay zeka asistanısın. "
            "Eğer kullanıcı sana bir şeyi açıklamanı, anlatmanı veya araştırmanı söylediyse "
            "ve sana internet bilgisi sağlandıysa, o internet bilgilerini kullanarak detaylı, "
            "anlaşılır ve açıklayıcı bir cevap ver. "
            "Eğer internet bilgisi yoksa ve kullanıcı sadece muhabbet ediyorsa, samimi bir şekilde sohbeti sürdür."
        )
        
        gonderilecek_mesajlar = [{"role": "system", "content": sistem_talimati}]
        gonderilecek_mesajlar.extend(st.session_state.mesaj_gecmisi)
        
        # Eğer internet araması yapıldıysa, son mesaja ekleyelim
        if internet_bilgisi:
            gonderilecek_mesajlar[-1]["content"] += f"\n\n(Güncel İnternet Bilgisi: {internet_bilgisi})"
            
        try:
            cevap = groq_istenci.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=gonderilecek_mesajlar
            )
            yanit = cevap.choices[0].message.content
            
            st.write(yanit)
            st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": yanit})
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
            
