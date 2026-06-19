import streamlit as st
import yt_dlp
import os
import subprocess
import json
from PIL import Image

st.set_page_config(page_title="Gelişmiş Video Filigran Aracı", layout="centered")

st.title("Gelişmiş Video Filigran Aracı")
st.write("Instagram ve X uyumlu, kırpılamaz çoklu logo ve güvenli alan metin yerleşimi.")

# Kullanıcı Girdileri
video_url = st.text_input("Sosyal Medya Video Linki")
uploaded_logo = st.file_uploader("Logo Seçin (PNG/JPG)", type=["png", "jpg", "jpeg"])
description = st.text_input("Görünür Açıklama Metni", max_chars=80)
logo_opacity = st.slider("Logo Görünürlük Oranı (Saydamlık)", 0.1, 1.0, 0.3, step=0.05)

def get_video_dimensions(video_path):
    """ffprobe kullanarak videonun gerçek genişlik ve yükseklik değerlerini döner."""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        data = json.loads(result.stdout)
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                width = int(stream.get('width'))
                height = int(stream.get('height'))
                return width, height
    except Exception as e:
        st.warning(f"Video boyutları okunurken hata oluştu, varsayılan değerler kullanılacak. Detay: {e}")
    return 1280, 720  # Hata durumunda varsayılan değerler

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
    Python ile hesaplanan boyutlara göre logoları 9 noktaya yerleştirir 
    ve metni Instagram güvenli bölgesine (Safe Zone) hizalar.
    """
    # Video boyutlarını dinamik olarak alıyoruz
    width, height = get_video_dimensions(video_path)
    
    # Logonun genişliğini video genişliğinin %12'si olacak şekilde hesaplıyoruz
    logo_w = int(width * 0.12)
    logo_w = max(logo_w, 40) # Çok küçük boyutları önlemek için sınır
    
    # Metin boyutunu video yüksekliğinin %3.5'i olacak şekilde hesaplıyoruz
    font_size = int(height * 0.035)
    font_size = max(font_size, 14)
    
    # Instagram Güvenli Bölge Y koordinatı (Yüksekliğin %75'i)
    text_y = int(height * 0.75)

    filter_parts = []
    
    # 1. Logoyu önceden hesaplanan genişliğe göre ölçeklendir (En boy oranı korunur)
    filter_parts.append(f"[1:v]scale={logo_w}:-1[logo]")
    
    # 2. 9 Noktalı Grid Koordinatları
    positions = [
        ("W*0.15", "H*0.15"), ("(W-w)/2", "H*0.15"), ("W*0.85-w", "H*0.15"),
        ("W*0.15", "(H-h)/2"), ("(W-w)/2", "(H-h)/2"), ("W*0.85-w", "(H-h)/2"),
        ("W*0.15", "H*0.70-h"), ("(W-w)/2", "H*0.70-h"), ("W*0.85-w", "H*0.70-h")
    ]
    
    last_output = "[0:v]"
    for i, (x, y) in enumerate(positions):
        out_label = f"[v_overlay_{i}]"
        filter_parts.append(f"{last_output}[logo]overlay=x={x}:y={y}{out_label}")
        last_output = out_label
        
    # 3. Metin Ekleme (Tek tırnakları FFmpeg için güvenli hale getiriyoruz)
    safe_text = text.replace("'", "'\\''")
    text_filter = (
        f"{last_output}drawtext=text='{safe_text}':"
        f"x=(w-text_w)/2:y={text_y}:"
        f"fontsize={font_size}:fontcolor=white:"
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
