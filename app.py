import streamlit as st
import yt_dlp
import os
import subprocess
from PIL import Image

st.set_page_config(page_title="Video Filigran Aracı", layout="centered")

st.title("Mobil Video Filigran Aracı")
st.write("Instagram veya X (Twitter) video linkini girerek filigran ekleyebilirsiniz.")

# Kullanıcı Girdileri
video_url = st.text_input("Sosyal Medya Video Linki")
uploaded_logo = st.file_uploader("Logo Seçin (PNG/JPG)", type=["png", "jpg", "jpeg"])
description = st.text_input("Video Altı Açıklama Metni", max_chars=100)

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
    """FFmpeg kullanarak logo ve metni videoya ekler."""
    # Kırpılmayı önlemek için logo merkeze yerleştirilir.
    # Metin ise alt kısma siyah arka plan kutusuyla eklenir.
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', logo_path,
        '-filter_complex',
        '[1:v]scale=iw*0.15:-1[logo];'  # Logo genişliğini videonun %15'i yapar
        '[0:v][logo]overlay=(W-w)/2:(H-h)/2[temp];'  # Logoyu merkeze yerleştirir
        f"[temp]drawtext=text='{text}':x=(w-text_w)/2:y=h-80:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=10",
        '-c:a', 'copy',
        output_path
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg Hatası: {result.stderr}")

if st.button("Videoyu İşle") and video_url and uploaded_logo:
    with st.spinner("İşlem gerçekleştiriliyor, lütfen bekleyin..."):
        # Geçici dosya isimleri
        input_video = "temp_input.mp4"
        input_logo = "temp_logo.png"
        output_video = "processed_output.mp4"
        
        # Eski geçici dosyaları temizle
        for f in [input_video, input_logo, output_video]:
            if os.path.exists(f):
                os.remove(f)

        try:
            # 1. Logoyu kaydet
            image = Image.open(uploaded_logo)
            image.save(input_logo)
            
            # 2. Videoyu indir
            st.info("Video indiriliyor...")
            download_video(video_url, input_video)
            
            # 3. Videoyu işle
            st.info("Filigran ve metin ekleniyor...")
            process_video(input_video, input_logo, description, output_video)
            
            # 4. Kullanıcıya sun
            if os.path.exists(output_video):
                with open(output_video, "rb") as file:
                    st.success("İşlem tamamlandı!")
                    st.download_button(
                        label="İşlenmiş Videoyu İndir",
                        data=file,
                        file_name="filigranli_video.mp4",
                        mime="video/mp4"
                    )
            
        except Exception as e:
            st.error(f"Bir hata oluştu: {str(e)}")
            
        finally:
            # Geçici dosyaları temizleme işlemi
            for f in [input_video, input_logo]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass