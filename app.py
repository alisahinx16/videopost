import streamlit as st
import yt_dlp
import os
import subprocess
from PIL import Image

st.set_page_config(page_title="Gelişmiş Video Filigran Aracı", layout="centered")

st.title("Gelişmiş Video Filigran Aracı")
st.write("Instagram ve X uyumlu, kırpılamaz çoklu logo ve güvenli alan metin yerleşimi.")

# Kullanıcı Girdileri
video_url = st.text_input("Sosyal Medya Video Linki")
uploaded_logo = st.file_uploader("Logo Seçin (PNG/JPG)", type=["png", "jpg", "jpeg"])
description = st.text_input("Görünür Açıklama Metni", max_chars=80)
logo_opacity = st.slider("Logo Görünürlük Oranı (Saydamlık)", 0.1, 1.0, 0.3, step=0.05)

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

def adjust_logo_opacity(image_path, opacity):
    """Logonun saydamlığını ayarlayarak videonun görünmesini kolaylaştırır."""
    img = Image.open(image_path).convert("RGBA")
    alpha = img.split()[3]
    alpha = alpha.point(lambda p: int(p * opacity))
    img.putalpha(alpha)
    img.save(image_path)

def process_video(video_path, logo_path, text, output_path):
    """
    FFmpeg ile logoları 9 noktaya yerleştirir ve metni Instagram 
    güvenli bölgesine (Safe Zone) hizalar.
    """
    filter_parts = []
    
    # 1. Logoyu video genişliğinin %12'sine ölçekle (farklı çözünürlükler için dinamik)
    filter_parts.append("[1:v][0:v]scale2ref=w=main_w*0.12:h=keep[logo][main]")
    
    # 2. 9 Noktalı Grid Koordinatları (Kırpmayı önlemek için her bölgeye yerleşim)
    # X: Sol (%15), Orta, Sağ (%85)
    # Y: Üst (%15), Orta, Alt (Instagram güvenli bölge sınırı olan %70 seviyesi)
    positions = [
        ("W*0.15", "H*0.15"), ("(W-w)/2", "H*0.15"), ("W*0.85-w", "H*0.15"),
        ("W*0.15", "(H-h)/2"), ("(W-w)/2", "(H-h)/2"), ("W*0.85-w", "(H-h)/2"),
        ("W*0.15", "H*0.70-h"), ("(W-w)/2", "H*0.70-h"), ("W*0.85-w", "H*0.70-h")
    ]
    
    last_output = "[main]"
    for i, (x, y) in enumerate(positions):
        out_label = f"[v_overlay_{i}]"
        filter_parts.append(f"{last_output}[logo]overlay=x={x}:y={y}{out_label}")
        last_output = out_label
        
    # 3. Instagram Güvenli Bölge Metin Yerleşimi
    # Metin, Reels arayüz elemanlarının üstünde kalacak şekilde y=H*0.75 noktasına yerleştirilir.
    # Yazı boyutu video yüksekliğinin %3.5'i olarak dinamik hesaplanır.
    font_size_expr = "H*0.035"
    text_filter = (
        f"{last_output}drawtext=text='{text}':"
        f"x=(w-text_w)/2:y=H*0.75:"
        f"fontsize={font_size_expr}:fontcolor=white:"
        f"box=1:boxcolor=black@0.65:boxborderw=15"
    )
    filter_parts.append(text_filter)
    
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

if st.button("Videoyu İşle ve Hazırla") and video_url and uploaded_logo:
    with st.spinner("Video indiriliyor ve güvenli alan hesaplamaları yapılıyor..."):
        input_video = "temp_input.mp4"
        input_logo = "temp_logo.png"
        output_video = "processed_output.mp4"
        
        # Temizlik
        for f in [input_video, input_logo, output_video]:
            if os.path.exists(f):
                os.remove(f)

        try:
            # Logo saydamlık ayarı
            image = Image.open(uploaded_logo)
            image.save(input_logo)
            adjust_logo_opacity(input_logo, logo_opacity)
            
            # Video indirme
            st.info("Sosyal medya bağlantısı çözümleniyor...")
            download_video(video_url, input_video)
            
            # Video işleme
            st.info("9 noktalı filigran ve güvenli bölge metni işleniyor...")
            process_video(input_video, input_logo, description, output_video)
            
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
            # Geçici dosyaları temizle
            for f in [input_video, input_logo]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
