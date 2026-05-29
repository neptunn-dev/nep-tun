import streamlit as st
from groq import Groq
from tavily import TavilyClient

# Şifreler kodun içinde değil, st.secrets içinde kalmalı!
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]

groq_istenci = Groq(api_key=GROQ_API_KEY)
tavily_istenci = TavilyClient(api_key=TAVILY_API_KEY)

# Web sitesi başlığı ve tasarımı
st.set_page_config(page_title="Yapay Zeka Araştırma Ajanı", page_icon="🤖")
st.title("🤖 Yapay Zeka Araştırma Ajanı")
st.write("Sorunu yazın, internette araştırıp geçmişi hatırlayarak cevaplayayım!")

# --- HAFIZA (SESSION STATE) KURULUMU ---
# Eğer hafızada daha önce konuşma geçmişi yoksa, boş bir liste oluşturuyoruz
if "mesaj_gecmisi" not in st.session_state:
    st.session_state.mesaj_gecmisi = []

# Eski mesajları ekranda chat şeklinde göster
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
        return "İnternet araması yapılamadı."

# Kullanıcıdan girdi alma (Chat input arayüzü)
if soru_girdisi := st.chat_input("Araştırmak istediğiniz konuyu yazın..."):
    
    # 1. Kullanıcının yazdığı soruyu ekrana bas ve hafızaya kaydet
    with st.chat_message("user"):
        st.write(soru_girdisi)
    st.session_state.mesaj_gecmisi.append({"role": "user", "content": soru_girdisi})

    # 2. Yapay zekanın araştırma ve cevaplama süreci
    with st.chat_message("assistant"):
        with st.spinner("İnternetteki kaynaklar taranıyor ve geçmiş analiz ediliyor..."):
            
            # İnternette arama yapalım
            internet_bilgisi = internette_ara(soru_girdisi)
            
            # Yapay zekaya hem geçmişi hem de yeni internet bilgisini göndermek için sistem talimatı hazırlıyoruz
            sistem_talimati = (
                "Sen profesyonel bir araştırma uzmanısın. İnternet arama sonuçlarını ve "
                "kullanıcıyla olan önceki konuşma geçmişini dikkate alarak net bir özet çıkar."
            )
            
            # Groq modeline gönderilecek mesajlar listesini hazırlıyoruz
            gonderilecek_mesajlar = [{"role": "system", "content": sistem_talimati}]
            
            # HAFIZADAKİ ESKİ KONUŞMALARI MODELİN GÖRMESİ İÇİN EKLİYORUZ
            gonderilecek_mesajlar.extend(st.session_state.mesaj_gecmisi)
            
            # En son gelen internet bilgisini de son mesaja ek bilgi olarak iliştiriyoruz
            gonderilecek_mesajlar[-1]["content"] += f"\n\n(İnternet Kaynakları: {internet_bilgisi})"
            
            try:
                # Groq ile cevap üretme
                cevap = groq_istenci.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=gonderilecek_mesajlar
                )
                yanit = cevap.choices[0].message.content
                
                # Cevabı ekrana yazdır ve hafızaya kaydet
                st.write(yanit)
                st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": yanit})
                
            except Exception as e:
                st.error(f"Bir hata oluştu: {e}")
