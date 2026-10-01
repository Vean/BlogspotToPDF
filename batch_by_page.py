import os
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from xhtml2pdf import pisa


def convert_html_to_pdf(html_content, output_path):
    """Mengonversi string HTML menjadi file PDF."""
    with open(output_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
    return not pisa_status.err


def clean_and_format_content(content_div):
    """Membersihkan dan merapikan struktur HTML konten agar bagus di PDF."""
    # 1. Hapus elemen yang tidak perlu (script, style, iframe, iklan, widget share, dsb)
    for tag in content_div.find_all(
        [
            "script",
            "style",
            "iframe",
            "ins",
            "noscript",
            "button",
            "form",
            "input",
        ]
    ):
        tag.decompose()

    # 2. Hapus widget/div navigasi bawaan web berdasarkan class atau ID
    for tag in content_div.find_all(
        class_=re.compile(r"blog-pager|post-footer|share|nav|pager", re.I)
    ):
        tag.decompose()

    for tag in content_div.find_all(
        id=re.compile(r"blog-pager|post-footer|nav|pager", re.I)
    ):
        tag.decompose()

    # 3. Hapus tag <a> yang mengandung kata kunci tombol navigasi (Next/Prev)
    nav_keywords = [
        "next post",
        "prev post",
        "previous post",
        "« prev",
        "next »",
        "next",
        "prev",
        "sebelumnya",
        "selanjutnya",
    ]

    for a in content_div.find_all("a"):
        text = " ".join(a.get_text().split()).strip().lower()
        if any(kw in text for kw in nav_keywords):
            a.decompose()

    # 4. Hapus atribut style & class bawaan dari sisa tag
    for tag in content_div.find_all(True):
        if "style" in tag.attrs:
            del tag.attrs["style"]
        if "class" in tag.attrs:
            del tag.attrs["class"]

    # 5. Ganti tag <br> berurutan menjadi paragraf baru agar spasi antar paragraf konsisten
    raw_html = str(content_div)
    raw_html = re.sub(r"(<br\s*/?>\s*){2,}", "</p><p>", raw_html)

    soup = BeautifulSoup(raw_html, "html.parser")

    # 6. Hapus paragraf/div/span kosong atau yang hanya berisi teks navigasi pendek
    for p in soup.find_all(["p", "div", "span"]):
        text = " ".join(p.get_text().split()).strip().lower()
        if not text and not p.find_all("img"):
            p.decompose()
        elif any(kw in text for kw in nav_keywords) and len(text) < 30:
            p.decompose()

    return str(soup)


def download_blogspot_batch(
    start_url, base_filename="Novel", export_folder="export"
):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    os.makedirs(export_folder, exist_ok=True)

    visited_urls = set()
    current_url = start_url
    page_count = 1

    print(f"=== Memulai Auto-Download dari: {start_url} ===")

    while current_url:
        if current_url in visited_urls:
            print(
                "\n[SELESAI] Terdeteksi kembali ke URL yang sudah pernah didownload."
            )
            break

        print(f"\n[{page_count}] Mengakses: {current_url}")
        visited_urls.add(current_url)

        try:
            response = requests.get(current_url, headers=headers, timeout=15)
        except Exception as e:
            print(f"[-] Gagal mengakses URL: {e}")
            break

        if response.status_code != 200:
            print(
                f"[-] Gagal mengakses halaman. Status code: {response.status_code}"
            )
            break

        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Ambil Judul Post
        title_tag = soup.find(["h1", "h3"], class_="post-title")
        title_text = (
            title_tag.get_text(strip=True) if title_tag else "Blogspot Post"
        )

        # 2. Ambil Konten Utama
        content_div = (
            soup.find("div", class_="post-body")
            or soup.find("div", class_="post-entry")
            or soup.find("article")
        )

        if not content_div:
            print("[-] Konten artikel tidak ditemukan pada halaman ini.")
            break

        # 3. Cari URL Berikutnya TERLEBIH DAHULU sebelum div konten dibersihkan/di-decompose
        next_tag = soup.find("a", id="Blog1_blog-pager-newer-link") or soup.find(
            "a", class_="blog-pager-newer-link"
        )

        if not next_tag:
            for a in soup.find_all("a", href=True):
                text = " ".join(a.get_text().split()).strip().lower()
                if "prev post" in text or "« prev" in text:
                    next_tag = a
                    break

        next_url = None
        if next_tag and next_tag.get("href"):
            next_url = urljoin(current_url, next_tag["href"])

        # 4. Bersihkan HTML konten dari tombol navigasi & style bawaan
        cleaned_body_html = clean_and_format_content(content_div)

        # 5. Format CSS Template Khusus Layak Baca / PDF Book Styling
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{
                    size: A4;
                    margin-top: 2cm;
                    margin-bottom: 2cm;
                    margin-left: 2.5cm;
                    margin-right: 2.5cm;
                    @bottom-right {{
                        content: counter(page);
                        font-family: Georgia, "Times New Roman", serif;
                        font-size: 9pt;
                        color: #666666;
                    }}
                }}
                
                body {{
                    font-family: Georgia, "Times New Roman", serif;
                    font-size: 11pt;
                    line-height: 1.6;
                    color: #111111;
                    text-align: justify;
                }}

                h1.chapter-title {{
                    font-family: Helvetica, Arial, sans-serif;
                    font-size: 18pt;
                    font-weight: bold;
                    color: #1a2a3a;
                    text-align: center;
                    margin-bottom: 25px;
                    padding-bottom: 10px;
                    border-bottom: 1.5px solid #1a2a3a;
                }}

                p {{
                    text-indent: 1.5em;
                    margin-top: 0px;
                    margin-bottom: 8px;
                    line-height: 1.6;
                }}

                h1 + p, div > p:first-child {{
                    text-indent: 0;
                }}

                img {{
                    max-width: 100%;
                    height: auto;
                    display: block;
                    margin: 15px auto;
                }}

                hr {{
                    border: none;
                    border-top: 1px solid #ccc;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <h1 class="chapter-title">{title_text}</h1>
            <div>{cleaned_body_html}</div>
        </body>
        </html>
        """

        # Simpan PDF
        file_name = f"{base_filename}_{page_count}.pdf"
        pdf_path = os.path.join(export_folder, file_name)

        if convert_html_to_pdf(html_content, pdf_path):
            print(f"[+] Berhasil disimpan (Rapi): {pdf_path}")
        else:
            print(f"[-] Gagal mengonversi ke PDF: {file_name}")

        # 6. Pindah ke URL Berikutnya
        if next_url and next_url not in visited_urls:
            print(f"[->] Pindah ke bab berikutnya via: {next_url}")
            current_url = next_url
            page_count += 1
        else:
            print("\n[SELESAI] Tidak ditemukan link urutan berikutnya.")
            break

    print(
        f"\n🎉 Selesai! Total {len(visited_urls)} PDF rapi telah disimpan di folder '{export_folder}/'."
    )


if __name__ == "__main__":
    start_url = "https://target.blogspot.com/2026/10/url-post.html"

    download_blogspot_batch(
        start_url=start_url,
        base_filename="file_name",
        export_folder="export",
    )