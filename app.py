import streamlit as st
import yt_dlp
import os
import subprocess

st.set_page_config(page_title="Video Filigran Aracı", layout="centered")

st.title("Mobil Video Filigran Aracı")
st.write("Instagram/X linkini girerek çoklu logo ve güvenli alan metni ekleyebilirsiniz.")

# Kullanıcı Girdileri
video_url = st.text_input("Sosyal Medya Video Linki")
uploaded_logo = st.file_uploader("Logo Seçin (PNG/JPG)", type=["png", "jpg", "jpeg"])
description = st.text_input("Kısa Açıklama", max_chars=80)

def download_video(url, output_path):
    """yt-dlp kullanarak videoyu indirir."""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def process_video(video_path, logo_path, text, output_path):
    """
    FFmpeg ile logoyu 120px genişliğinde, %35 opaklıkla 5 noktaya yerleştirir.
    Metni ise Instagram güvenli alanına dinamik boyutta ekler.
    """
    # Tek tırnak işaretlerini FFmpeg drawtext filtresi için güvenli hale getirme
    safe_text = text.replace("'", "'\\''")
    
    filter_parts = [
        # Logonun boyutunu 120px yapar ve %35 opaklık (colorchannelmixer) uygular
        '[1:v]scale=120:-1,format=rgba,colorchannelmixer=aa=0.35[logo]',
        
        # 5 Noktaya yerleşim zinciri (Sol Üst, Sağ Üst, Merkez, Sol Alt, Sağ Alt)
        '[0:v][logo]overlay=x=W*0.1:y=H*0.1[v1]',
        '[v1][logo]overlay=x=W*0.9-w:y=H*0.1[v2]',
        '[v2][logo]overlay=x=(W-w)/2:y=(H-h)/2[v3]',
        '[v3][logo]overlay=x=W*0.1:y=H*0.7-h[v4]',
        '[v4][logo]overlay=x=W*0.9-w:y=H*0.7-h[v5]',
        
        # Metni Instagram güvenli alanına (Yüksekliğin %75'i) büyük ve okunaklı yerleştirme
        f"[v5]drawtext=text='{safe_text}':x=(w-text_w)/2:y=h*0.75:fontsize=h*0.035:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=15"
    ]
    
    filter_complex_str = ";".join(filter_parts)

    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', logo_path,
        '-filter_complex', filter_complex_str,
        '-c:a', 'copy',
        output_path
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg Hatası: {result.stderr}")

if st.button("Videoyu İşle") and video_url and uploaded_logo:
    with st.spinner("İşlem yapılıyor, lütfen bekleyin..."):
        input_video = "temp_input.mp4"
        input_logo = "temp_logo.png"
        output_video = "processed_output.mp4"
        
        # Eski geçici dosyaların temizliği
        for f in [input_video, input_logo, output_video]:
            if os.path.exists(f):
                os.remove(f)

        try:
            # Gelen logoyu geçici olarak diske yaz
            with open(input_logo, "wb") as f:
                f.write(uploaded_logo.getbuffer())
            
            # Videoyu indir
            st.info("Video indiriliyor...")
            download_video(video_url, input_video)
            
            # Videoyu işle
            st.info("Logolar ve metin videoya işleniyor...")
            process_video(input_video, input_logo, description, output_video)
            
            # İndirme butonunu göster
            if os.path.exists(output_video):
                with open(output_video, "rb") as file:
                    st.success("Video başarıyla hazırlandı!")
                    st.download_button(
                        label="Düzenlenmiş Videoyu İndir",
                        data=file,
                        file_name="korumali_video.mp4",
                        mime="video/mp4"
                    )
            
        except Exception as e:
            st.error(f"İşlem sırasında bir hata oluştu: {str(e)}")
            
        finally:
            # Geçici dosyaları temizleme
            for f in [input_video, input_logo]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
