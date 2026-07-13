# V.3
import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import time

# Fungsi untuk mengambil semua link internal
def get_internal_links(base_url, soup):
    internal_links = set()
    domain = urlparse(base_url).netloc
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href")
        full_url = urljoin(base_url, href)
        if domain in urlparse(full_url).netloc:
            full_url = full_url.split('#')[0]
            internal_links.add(full_url)
            
    return internal_links

# Logika untuk mendeteksi apakah URL adalah "Product" atau "Page"
def is_product_url(url):
    path_parts = [p for p in urlparse(url).path.strip('/').split('/') if p]
    if len(path_parts) >= 3 and any(char.isdigit() for char in path_parts[-1]):
        return True
    return False

# Fungsi crawler dan scraper utama
def scan_pages(start_url, max_pages, post_type_filter, delay_seconds):
    visited = set()
    queue = [start_url]
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    progress_bar = st.progress(0)
    status_text = st.empty()

    while queue and len(visited) < max_pages:
        current_url = queue.pop(0)
        
        if current_url in visited:
            continue
            
        if len(visited) > 0 and delay_seconds > 0:
            time.sleep(delay_seconds)
            
        try:
            status_text.text(f"Memindai ({len(visited)+1}/{max_pages}): {current_url}")
            response = requests.get(current_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            visited.add(current_url)
            
            new_links = get_internal_links(current_url, soup)
            for link in new_links:
                if link.startswith(start_url) and link not in visited and link not in queue:
                    queue.append(link)
            
            is_product = is_product_url(current_url)
            
            if post_type_filter == "Page Saja" and is_product:
                continue 
            elif post_type_filter == "Product Saja" and not is_product:
                continue
                
            # 1. Ambil Title Tag
            title_tag = soup.find('title')
            page_title = title_tag.text.strip() if title_tag else "Tidak ada Title"
            
            # 2. Ambil Meta Description
            meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
            if not meta_desc_tag: # Fallback jika menggunakan standar Open Graph
                meta_desc_tag = soup.find('meta', attrs={'property': 'og:description'})
            meta_description = meta_desc_tag.get('content', '').strip() if meta_desc_tag else "Kosong / Tidak ada Meta Description"
            
            # 3. Ambil Image Alt Tag
            images = soup.find_all('img')
            alts = [img.get('alt', '').strip() for img in images if img.get('alt', '').strip()]
            alt_text_combined = " ; ".join(alts) if alts else "Kosong / Tidak ada Alt Image"
            
            # Simpan hasil dengan susunan kolom SEO
            results.append({
                "Type": "Product" if is_product else "Page",
                "Title Tag": page_title,
                "Meta Description": meta_description,
                "Permalink": current_url,
                "Image Alt Tag": alt_text_combined
            })
            
            # Update progress bar
            progress = int((len(visited) / max_pages) * 100)
            progress_bar.progress(progress if progress <= 100 else 100)
                    
        except Exception as e:
            st.error(f"Error pada {current_url}: {e}")
            
    progress_bar.empty()
    status_text.empty()
    return results

# ==========================================
# KONFIGURASI DASHBOARD (STREAMLIT UI)
# ==========================================
st.set_page_config(page_title="SEO & Image Alt Scanner", layout="wide")
st.title("🚀 Dashboard SEO & Image Alt Scanner v3.0")
st.write("Tools untuk melakukan audit dasar *On-Page SEO* (Title, Meta Description, dan Alt Image) dari sebuah situs beserta turunannya.")

# Form Input
with st.form("scan_form"):
    col1, col2 = st.columns([3, 1])
    with col1:
        url_input = st.text_input("Masukkan Target URL", value="https://www.intime.co.id/rolex/")
    with col2:
        max_pages = st.number_input("Maksimal Halaman Di-*Crawl*", min_value=1, max_value=1000, value=20)
        
    col3, col4 = st.columns([2, 2])
    with col3:
        post_type = st.selectbox(
            "Target Post Type", 
            ["Semua (Page & Product)", "Page Saja", "Product Saja"],
            help="Product akan difilter berdasarkan struktur URL (contoh: mengandung kode referensi jam)."
        )
    with col4:
        delay = st.number_input(
            "Jeda per Halaman (Detik)", 
            min_value=0.0, max_value=10.0, value=1.0, step=0.5,
            help="Waktu tunggu sebelum membuka halaman berikutnya agar tidak diblokir server target."
        )
        
    submit_button = st.form_submit_button("Mulai Scan SEO")

# Eksekusi saat tombol diklik
if submit_button:
    if not url_input.startswith("http"):
        st.error("Harap masukkan URL yang valid (dimulai dengan http:// atau https://)")
    else:
        with st.spinner('Sedang memindai data SEO, harap tunggu...'):
            data = scan_pages(url_input, int(max_pages), post_type, float(delay))
            
            if data:
                df = pd.DataFrame(data)
                st.success(f"✅ Selesai! Menemukan {len(data)} hasil dari {max_pages} halaman yang di-*crawl*.")
                
                # Tampilkan Tabel
                st.dataframe(df, use_container_width=True)
                
                # Tombol Download CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Data Laporan (CSV)",
                    data=csv,
                    file_name=f'hasil_audit_seo_{post_type.split()[0].lower()}.csv',
                    mime='text/csv',
                )
            else:
                st.warning("Tidak ada data yang ditemukan. Coba ubah opsi Post Type atau naikkan batas limit halaman.")
