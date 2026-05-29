
import streamlit as st
from groq import Groq
from tavily import TavilyClient

# Web sitesi başlığı ve tasarımı
st.set_page_config(page_title="Yapay Zeka Araştırmacı", page_icon="🤖")
st.title("🤖 Yapay Zeka Araştırma Ajanı")
st.write("Sorunu yazın, internette araştırıp sizin için özetleyeyim!")

# API Anahtarlarını Streamlit Secrets üzerinden güvenli bir şekilde alıyoruz
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]

groq_istenci = Groq(api_key=GROQ_API_KEY)
tavily_istenci = TavilyClient(api_key=TAVILY_API_KEY)

def ajan_ara_ve_cevapla(soru):
    # İnternet araması yapılıyor
    arama = tavily_istenci.search(query=soru, max_results=5)
    
    veri_tabani = ""
    for sayfa in arama['results']:
        veri_tabani += f"- {sayfa['title']}: {sayfa['content']}\n"
    
    sistem_talimati = (
        "Sen profesyonel bir döküman inceleme ve araştırma uzmanısın. İnternet arama sonuçlarından "
        "gelen farklı kaynakları oku, birbiriyle birleştir, tekrar eden bilgileri temizle ve net bir özet çıkar."
    )
    
    # Groq ile cevap üretme
    cevap = groq_istenci.chat.completions.create(
        model="llama3-8b-8192", # ya da kullandığın diğer model ismi
        messages=[
            {"role": "system", "content": sistem_talimati},
            {"role": "user", "content": f"Soru: {soru}\n\nİnternet Kaynakları:\n{veri_tabani}"}
        ]
    )
    return cevap.choices[0].message.content

# Kullanıcıdan girdi alma (Web Arayüzü)
soru_girdisi = st.text_input("Araştırmak istediğiniz konuyu yazın:")

if soru_girdisi:
    with st.spinner("İnternetteki kaynaklar taranıyor ve analiz ediliyor..."):
        try:
            yanit = ajan_ara_ve_cevapla(soru_girdisi)
            st.subheader("📝 Araştırma Sonucu:")
            st.write(yanit)
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}. Lütfen API anahtarlarınızı kontrol edin.")
