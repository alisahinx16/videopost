import streamlit as st
import yt_dlp
import os
import subprocess
import json
import textwrap
from PIL import Image

st.set_page_config(page_title="Video Filigran Aracı", layout="centered")

st.title("Mobil Video Filigran Aracı")
st.write("Sosyal medya videolarınıza dinamik metin ve çoklu logo filigranı ekleyin.")

# Kullanıcı Girdileri
video_url = st.text_input("Sosyal Medya Video Linki")
uploaded_logo = st.file_uploader("Logo Seçin (PNG/JPG)", type=["png", "jpg", "jpeg"])
description = st.text_input("Açıklama Metni (Uzun metinler otomatik alt satıra bölünür)")

def get_video_dimensions(video_path):
    """ffprobe kullanarak videonun genişlik ve yükseklik değerlerini döner."""
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
                return int(stream.get('width')), int(stream.get('height'))
    except:
        pass
    return 720, 1280  # Hata durumunda varsayılan dikey çözünürlük

def prepare_logo(logo_path, output_logo_path, video_width, opacity=0.35):
    """
    Logoyu video genişliğinin %12'si olacak şekilde yeniden boyutlandırır,
    saydamlık (opacity) ekler ve transparan PNG olarak kaydeder.
    """
    img = Image.open(logo_path).convert("RGBA")
    
    # Yeni genişlik hesaplama (%12)
    target_width = int(video_width * 0.12)
    target_width = max(target_width, 50) # Çok küçük olmasını engellemek için alt sınır
    
    # En boy oranını koruyarak yükseklik hesaplama
    aspect_ratio = img.height / img.width
    target_height = int(target_width * aspect_ratio)
    
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Saydamlık uygulama
    alpha = img.split()[3]
    alpha = alpha.point(lambda p: int(p * opacity))
    img.putalpha(alpha)
    
    img.save(output_logo_path, "PNG")

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
    """FFmpeg ile optimize edilmiş filigran ve dinamik metin işlemesi yapar."""
    width, height = get_video_dimensions(video_path)
    
    # 1. Logoyu Python (Pillow) ile hazırla
    ready_logo_path = "temp_ready_logo.png"
    prepare_logo(logo_path, ready_logo_path, width, opacity=0.35)
    
    # 2. Metni video genişliğine göre otomatik sar (Wrap text)
    # 120px logo genişliğine göre yaklaşık 35 karakter satır sınırı idealdir.
    wrapped_lines = textwrap.wrap(text, width=35)
    wrapped_text = "\n".join(wrapped_lines)
    
    # Metni geçici bir dosyaya yaz (FFmpeg drawtext tırnak/karakter hatalarını önler)
    temp_text_file = "temp_text.txt"
    with open(temp_text_file, "w", encoding="utf-8") as f:
        f.write(wrapped_text)
        
    # Dinamik yazı boyutu (Yüksekliğin %3.5'i)
    font_size = int(height * 0.035)
    font_size = max(font_size, 16)
    
    # Metin dikey konumu (Alt bölgeye yakın yerleşim)
    text_y = int(height * 0.80)

    # 5 Noktalı Grid Filtresi (Pillow ile ölçeklendiği için scale işlemine gerek kalmadı)
    filter_parts = [
        '[0:v][1:v]overlay=x=W*0.1:y=H*0.1[v1]',
        '[v1][1:v]overlay=x=W*0.9-w:y=H*0.1[v2]',
        '[v2][1:v]overlay=x=(W-w)/2:y=(H-h)/2[v3]',
        '[v3][1:v]overlay=x=W*0.1:y=H*0.80-h[v4]',
        '[v4][1:v]overlay=x=W*0.9-w:y=H*0.80-h[v5]',
        f"[v5]drawtext=textfile='{temp_text_file}':x=(w-text_w)/2:y={text_y}:"
        f"fontsize={font_size}:fontcolor=white:box=1:boxcolor=black@0.65:boxborderw=15"
    ]
    
    filter_complex_str = ";".join(filter_parts)

    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', ready_logo_path,
        '-filter_complex', filter_complex_str,
        '-c:a', 'copy',
        output_path
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # İşlem sonrası geçici metin ve işlenmiş logo dosyalarını temizle
    if os.path.exists(temp_text_file):
        os.remove(temp_text_file)
    if os.path.exists(ready_logo_path):
        os.remove(ready_logo_path)
        
    if result.returncode != 0:
        raise Exception(f"FFmpeg Hatası: {result.stderr}")

if st.button("Videoyu İşle") and video_url and uploaded_logo:
    with st.spinner("İşlem gerçekleştiriliyor, lütfen bekleyin..."):
        input_video = "temp_input.mp4"
        input_logo = "temp_logo.png"
        output_video = "processed_output.mp4"
        
        # Eski geçici dosyaların temizliği
        for f in [input_video, input_logo, output_video]:
            if os.path.exists(f):
                os.remove(f)

        try:
            # Gelen logoyu geçici olarak diske kaydet
            with open(input_logo, "wb") as f:
                f.write(uploaded_logo.getbuffer())
            
            # Videoyu sosyal medyadan indir
            st.info("Video indiriliyor...")
            download_video(video_url, input_video)
            
            # Dinamik olarak boyutlandır ve birleştir
            st.info("Logolar optimize ediliyor ve metin sığdırılıyor...")
            process_video(input_video, input_logo, description, output_video)
            
            if os.path.exists(output_video):
                with open(output_video, "rb") as file:
                    st.success("Video başarıyla hazırlandı!")
                    st.download_button(
                        label="Düzenlenmiş Videoyu İndir",
                        data=file,
                        file_name="islenmis_video.mp4",
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
