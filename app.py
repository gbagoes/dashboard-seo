# version 4.1.2
import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import time
import csv
import re

# ==========================================
# FUNGSI METODE 1: CRAWLING (UNTUK PAGE)
# ==========================================
def get_internal_links(base_url, soup):
    internal_links = set()
    domain = urlparse(base_url).netloc
    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href")
        if href:
            full_url = urljoin(base_url, href)
            if domain in urlparse(full_url).netloc:
                full_url = full_url.split('#')[0]
                internal_links.add(full_url)
    return internal_links

def crawl_pages(start_url, max_pages, delay_seconds):
    visited = set()
    queue = [start_url]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    progress_bar = st.progress(0)
    status_text = st.empty()

    while queue and len(visited) < max_pages:
        current_url = queue.pop(0)
        if current_url in visited:
            continue
            
        if len(visited) > 0 and delay_seconds > 0:
            time.sleep(delay_seconds)
            
        try:
            status_text.text(f"Memindai Halaman ({len(visited)+1}/{max_pages}): {current_url}")
            response = requests.get(current_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            visited.add(current_url)
            
            for link in get_internal_links(current_url, soup):
                if link.startswith(start_url) and link not in visited and link not in queue:
                    queue.append(link)
            
            if "/rolex/jam-tangan-rolex/" in current_url and len(current_url.split('/')) > 6:
                continue
                
            # 1. Ekstrak Title Tag (SEO)
            title = soup.find('title')
            seo_title = title.text.strip() if title else "Tidak ada Title Tag"
            
            # 2. Ekstrak Page Title (Representasi get_the_title di frontend)
            og_title = soup.find('meta', attrs={'property': 'og:title'})
            wp_class_title = soup.find(class_=['product_title', 'entry-title'])
            
            if og_title:
                page_title_pure = og_title.get('content', '').strip()
            elif wp_class_title:
                page_title_pure = wp_class_title.text.strip()
            else:
                page_title_pure = "Tidak ditemukan"
            
            # 3. Ekstrak Meta Description
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            meta_description = meta_desc.get('content', '').strip() if meta_desc else "Kosong"
            
            # 4. Ekstrak Image Alt Tag
            images = soup.find_all('img')
            alts = [img.get('alt', '').strip() for img in images if img.get('alt', '').strip()]
            alt_combined = " ; ".join(alts) if alts else "Kosong"
            
            results.append({
                "Type": "Page",
                "Page Title (WP)": page_title_pure,
                "Title Tag": seo_title,
                "Meta Description": meta_description,
                "Permalink": current_url,
                "Image Alt Tag": alt_combined
            })
            
            progress_bar.progress(min(int((len(visited) / max_pages) * 100), 100))
                    
        except Exception as e:
            st.error(f"Error pada {current_url}: {e}")
            
    progress_bar.empty()
    status_text.empty()
    return results


# ==========================================
# FUNGSI METODE 2: SITEMAP (UNTUK PRODUCT)
# ==========================================
def scan_from_sitemap(sitemap_url, target_prefix, max_pages, delay_seconds):
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    st.info("Membaca XML Sitemap dari server...")
    
    try:
        response = requests.get(sitemap_url, headers=headers, timeout=15)
        if response.status_code != 200:
            st.error(f"Gagal membaca Sitemap. Status code: {response.status_code}")
            return []
            
        all_urls = re.findall(r'<loc>(.*?)</loc>', response.text)
        target_urls = [url for url in all_urls if url.startswith(target_prefix)]
        
        if not target_urls:
            st.warning("Tidak ada URL yang cocok dengan kriteria (prefix) di dalam Sitemap ini.")
            return []
            
        st.success(f"Berhasil menemukan {len(target_urls)} URL produk di Sitemap! Memulai proses scan...")
        
        urls_to_scan = target_urls[:max_pages]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, current_url in enumerate(urls_to_scan):
            if i > 0 and delay_seconds > 0:
                time.sleep(delay_seconds)
                
            try:
                status_text.text(f"Memindai Produk ({i+1}/{len(urls_to_scan)}): {current_url}")
                page_resp = requests.get(current_url, headers=headers, timeout=10)
                
                if page_resp.status_code == 200:
                    soup = BeautifulSoup(page_resp.text, 'html.parser')
                    
                    # 1. Ekstrak Title Tag (SEO)
                    title = soup.find('title')
                    seo_title = title.text.strip() if title else "Tidak ada Title Tag"
                    
                    # 2. Ekstrak Page Title (Representasi get_the_title di frontend)
                    og_title = soup.find('meta', attrs={'property': 'og:title'})
                    wp_class_title = soup.find(class_=['product_title', 'entry-title'])
                    
                    if og_title:
                        page_title_pure = og_title.get('content', '').strip()
                    elif wp_class_title:
                        page_title_pure = wp_class_title.text.strip()
                    else:
                        page_title_pure = "Tidak ditemukan"
                    
                    # 3. Ekstrak Meta Description
                    meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
                    meta_description = meta_desc.get('content', '').strip() if meta_desc else "Kosong"
                    
                    # 4. Ekstrak Image Alt Tag
                    images = soup.find_all('img')
                    alts = [img.get('alt', '').strip() for img in images if img.get('alt', '').strip()]
                    alt_combined = " ; ".join(alts) if alts else "Kosong"
                    
                    results.append({
                        "Type": "Product",
                        "Page Title (WP)": page_title_pure,
                        "Title Tag": seo_title,
                        "Meta Description": meta_description,
                        "Permalink": current_url,
                        "Image Alt Tag": alt_combined
                    })
                    
            except Exception as e:
                st.error(f"Error pada produk {current_url}: {e}")
                
            progress_bar.progress(min(int(((i + 1) / len(urls_to_scan)) * 100), 100))
            
        progress_bar.empty()
        status_text.empty()
        return results
        
    except Exception as e:
        st.error(f"Error saat memproses Sitemap: {e}")
        return []


# ==========================================
# KONFIGURASI DASHBOARD (STREAMLIT UI)
# ==========================================
st.set_page_config(page_title="SEO & Image Alt Scanner v4.2", layout="wide")
st.title("🚀 Dashboard SEO & Image Alt Scanner v4.2")
st.write("Tools audit *On-Page SEO* dengan pemisahan kolom Page Title (Representasi WP) dan Title Tag (SEO).")

scan_mode = st.radio(
    "Pilih Metode Scanning:",
    ("Metode Crawling (Cocok untuk Halaman/Page Umum)", "Metode Sitemap XML (Akurat untuk Ratusan Produk)"),
    horizontal=True
)

st.markdown("---")

with st.form("scan_form"):
    if "Sitemap" in scan_mode:
        col1, col2 = st.columns([2, 2])
        with col1:
            sitemap_url = st.text_input("URL XML Sitemap", value="https://www.intime.co.id/product-sitemap.xml")
        with col2:
            target_prefix = st.text_input("Syarat Awalan URL (Prefix)", value="https://www.intime.co.id/rolex/jam-tangan-rolex/")
    else:
        url_input = st.text_input("Masukkan Target URL / Halaman Awal", value="https://www.intime.co.id/rolex/")

    col3, col4 = st.columns([2, 2])
    with col3:
        max_pages = st.number_input("Batas Total Data/URL Diproses", min_value=1, max_value=2000, value=50)
    with col4:
        delay = st.number_input("Jeda per Halaman (Detik)", min_value=0.0, max_value=10.0, value=1.0, step=0.5)
        
    submit_button = st.form_submit_button("Mulai Scan SEO")

if submit_button:
    with st.spinner('Sistem sedang bekerja, harap tunggu...'):
        if "Sitemap" in scan_mode:
            data = scan_from_sitemap(sitemap_url, target_prefix, int(max_pages), float(delay))
            file_name = 'hasil_audit_produk_sitemap.csv'
        else:
            data = crawl_pages(url_input, int(max_pages), float(delay))
            file_name = 'hasil_audit_page_crawling.csv'
        
        if data:
            df = pd.DataFrame(data)
            st.success(f"✅ Selesai! Berhasil mengumpulkan {len(data)} baris data.")
            
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False, sep=';', quoting=csv.QUOTE_ALL).encode('utf-8')
            
            st.download_button(
                label="📥 Download Data Laporan (CSV)",
                data=csv_data,
                file_name=file_name,
                mime='text/csv',
            )
