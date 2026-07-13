import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd

# Fungsi untuk mengambil semua link internal (turunan) dalam satu halaman
def get_internal_links(base_url, soup):
    internal_links = set()
    domain = urlparse(base_url).netloc
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href")
        full_url = urljoin(base_url, href)
        
        # Memastikan link masih berada di domain yang sama
        if domain in urlparse(full_url).netloc:
            # Menghapus fragment/anchor (misal: #section1) agar tidak duplicate
            full_url = full_url.split('#')[0]
            internal_links.add(full_url)
            
    return internal_links

# Fungsi crawler dan scraper
def scan_pages(start_url, max_pages):
    visited = set()
    queue = [start_url]
    results = []
    
    # Header user-agent agar request tidak diblokir oleh sistem anti-bot
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    progress_bar = st.progress(0)
    status_text = st.empty()

    while queue and len(visited) < max_pages:
        current_url = queue.pop(0)
        
        if current_url in visited:
            continue
            
        try:
            status_text.text(f"Scanning: {current_url}")
            response = requests.get(current_url, headers=headers, timeout=10)
            
            # Lewati jika halaman tidak ditemukan atau error
            if response.status_code != 200:
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            visited.add(current_url)
            
            # 1. Ambil Nama Page (Title)
            title_tag = soup.find('title')
            page_title = title_tag.text.strip() if title_tag else "Tidak ada judul"
            
            # 2. Ambil semua Image dan extract 'alt'
            images = soup.find_all('img')
            alts = []
            for img in images:
                alt_text = img.get('alt', '').strip()
                if alt_text: # Hanya ambil yang alt-nya tidak kosong
                    alts.append(alt_text)
                    
            # Gabungkan dengan separator ';'
            alt_text_combined = " ; ".join(alts) if alts else "Tidak ada/kosong"
            
            # Simpan hasil
            results.append({
                "Page Name": page_title,
                "Permalink": current_url,
                "Image Alt Tag": alt_text_combined
            })
            
            # Update progress bar
            progress = int((len(visited) / max_pages) * 100)
            progress_bar.progress(progress if progress <= 100 else 100)
            
            # 3. Cari link turunan untuk di-scan selanjutnya
            new_links = get_internal_links(current_url, soup)
            for link in new_links:
                # Pastikan link memiliki prefix base url target agar tidak melebar ke seluruh situs
                if link.startswith(start_url) and link not in visited and link not in queue:
                    queue.append(link)
                    
        except Exception as e:
            st.error(f"Error pada {current_url}: {e}")
            
    progress_bar.empty()
    status_text.empty()
    return results

# ==========================================
# KONFIGURASI DASHBOARD (STREAMLIT UI)
# ==========================================
st.set_page_config(page_title="Image Alt Tag Scanner", layout="wide")
st.title("🖼️ Dashboard Scanner Alt Image")
st.write("Tools ini digunakan untuk melakukan *crawl* pada sebuah situs beserta turunannya untuk mengambil tag *alt* pada setiap gambar.")

# Form Input
with st.form("scan_form"):
    col1, col2 = st.columns([3, 1])
    with col1:
        url_input = st.text_input("Masukkan Target URL", value="https://www.intime.co.id/rolex/")
    with col2:
        max_pages = st.number_input("Maksimal Halaman (Limit)", min_value=1, max_value=500, value=15)
        
    submit_button = st.form_submit_button("Mulai Scan")

# Eksekusi saat tombol diklik
if submit_button:
    if not url_input.startswith("http"):
        st.error("Harap masukkan URL yang valid (dimulai dengan http:// atau https://)")
    else:
        with st.spinner('Sedang melakukan inisialisasi...'):
            data = scan_pages(url_input, max_pages)
            
            if data:
                df = pd.DataFrame(data)
                st.success(f"✅ Selesai! Berhasil memindai {len(data)} halaman.")
                
                # Tampilkan Tabel
                st.dataframe(df, use_container_width=True)
                
                # Tombol Download CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Data (CSV)",
                    data=csv,
                    file_name='hasil_scan_alt_image.csv',
                    mime='text/csv',
                )
            else:
                st.warning("Tidak ada data yang ditemukan. Pastikan URL dapat diakses atau coba naikkan limit halaman.")