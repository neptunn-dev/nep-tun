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
    
    # Sohbeti Temizle Butonu
    if st.button("🗑️ Sohbeti Temizle", use_container_width=True):
        st.session_state.mesaj_gecmisi = []
        st.rerun()
        
    st.write("---")
    
    # Kişilik Seçme Menüsü
    kisilik = st.selectbox(
        "🤖 Asistan Kişiliği Seçin:",
        ["Standart Asistan", "İnternet Araştırmacısı (Ajan)", "Bilim İnsanı", "Mahalle Arkadaşı (Kanka)", "Yazılımcı Mentoru"]
    )
    
    st.write("---")
    
    # Sohbet Geçmişini İndirme (Export)
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
    else:
        st.caption("İndirmek için önce bir şeyler yazın.")
        
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

# Geliştirilmiş İnternet arama fonksiyonu
def internette_ara(soru, gelismis_mod=False):
    try:
        if gelismis_mod:
            # Filtrelenmiş ve optimize edilmiş derin arama
            arama_sonucu = tavily_istenci.search(
                query=soru, 
                search_depth="advanced", 
                max_results=5, 
                include_raw_content=True
            )
            metinler = []
            for sonuc in arama_sonucu["results"]:
                icerik = sonuc.get('raw_content') or sonuc.get('content') or "İçerik çekilemedi"
                metinler.append(f"- {sonuc['title']}: {icerik[:600]}")
            return "\n".join(metinler)
        else:
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
        # Mod kontrolü ve internet tetikleme mekanizması
        if kisilik == "İnternet Araştırmacısı (Ajan)":
            internet_gerekli = True
        else:
            arama_kelimeleri = ["nedir", "kimdir", "araştır", "fiyatı", "haber", "hava durumu", "ne zaman", "son dakika", "açıkla", "anlat", "bilgi ver"]
            internet_gerekli = any(kelime in soru_girdisi.lower() for kelime in arama_kelimeleri)
        
        if internet_gerekli:
            with st.spinner("🌐 İnternet kaynakları derinlemesine taranıyor..."):
                is_advanced = (kisilik == "İnternet Araştırmacısı (Ajan)")
                internet_bilgisi = internette_ara(soru_girdisi, gelismis_mod=is_advanced)
        else:
            internet_bilgisi = None

        # Kişiliklere göre sistem talimatı belirleme (Yalan söylemeyi engelleyen sert kurallar)
        if kisilik == "İnternet Araştırmacısı (Ajan)":
            karakter_talimati = (
                "Sen son derece katı bir siber araştırma ve bilgi doğrulama uzmanısın. "
                "Adım adım düşün: Önce sana sağlanan internet bilgilerini oku ve kullanıcının aradığı spesifik bilgi/karar numarası orada var mı kontrol et. "
                "Eğer aranan karar numarası, yıl veya hukuki veri kaynaklarda AÇIKÇA geçmiyorsa, 'İnternet verilerinde bu kriterlere ait resmi bir karara ulaşılamadı' diyeceksiniz ve asla kafandan uydurmayacaksın. "
                "Verdiğin her somut bilginin, rakamın veya dökümanın sonuna hangi başlığı/kaynağı kullandığını parantez içinde yazacaksın (Örn: [Kaynak: Yargıtay Bilgi Bankası]). "
                "Yalnızca kullanıcı senden hayali bir senaryo, hukuki bir yorum veya beyin fırtınası isterse yaratıcı analizler yapabilirsin."
            )
        elif kisilik == "Bilim İnsanı":
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
                messages=gonderilecek_mesajlar,
                temperature=0.3  # Hem uydurmayı frenler hem de hayal gücünü tamamen öldürmez!
            )
            yanit = cevap.choices[0].message.content
            
            # Cevabı ekrana yazdır
            st.write(yanit)
            st.session_state.mesaj_gecmisi.append({"role": "assistant", "content": yanit})
            
            # Sadece ses motoru için metindeki emojileri temizliyoruz
            ses_metni = re.sub(r'[^\w\s,.!?:\(\)\-\"\']', '', yanit)
            
            # Sesli Okuma Ayarı
            with st.spinner("🔊 Ses dosyası hazırlanıyor..."):
                tts = gTTS(text=ses_metni[:300], lang='tr', tld='com.tr')
                tts.save("cevap.mp3")
                st.audio("cevap.mp3", format="audio/mp3")
                
        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
