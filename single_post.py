import os
import re
import requests
from bs4 import BeautifulSoup
from xhtml2pdf import pisa


def clean_and_format_content(content_div):
    """Membersihkan elemen pengganggu dan merapikan format konten agar rapi di PDF."""
    # 1. Hapus script, style, iframe, iklan, form, dsb.
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

    # 2. Hapus widget/div navigasi bawaan web
    for tag in content_div.find_all(
        class_=re.compile(r"blog-pager|post-footer|share|nav|pager", re.I)
    ):
        tag.decompose()

    for tag in content_div.find_all(
        id=re.compile(r"blog-pager|post-footer|nav|pager", re.I)
    ):
        tag.decompose()

    # 3. Hapus teks/tombol navigasi (Next/Prev) di dalam konten agar PDF bersih
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

    # 5. Ganti tag <br> berurutan menjadi paragraf baru
    raw_html = str(content_div)
    raw_html = re.sub(r"(<br\s*/?>\s*){2,}", "</p><p>", raw_html)

    soup = BeautifulSoup(raw_html, "html.parser")

    # 6. Hapus paragraf/div kosong atau sisa teks navigasi
    for p in soup.find_all(["p", "div", "span"]):
        text = " ".join(p.get_text().split()).strip().lower()
        if not text and not p.find_all("img"):
            p.decompose()
        elif any(kw in text for kw in nav_keywords) and len(text) < 30:
            p.decompose()

    return str(soup)


def blogspot_to_pdf(post_url, output_pdf_name="Hasil_Backup.pdf"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"Mengambil data dari: {post_url}...")
    try:
        response = requests.get(post_url, headers=headers, timeout=15)
    except Exception as e:
        print(f"Gagal melakukan request: {e}")
        return

    if response.status_code != 200:
        print(f"Gagal mengakses halaman. Status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Ambil Judul Post
    title_tag = soup.find(["h1", "h3"], class_="post-title")
    title_text = title_tag.get_text(strip=True) if title_tag else "Blogspot Post"

    # 2. Ambil Konten Utama
    content_div = (
        soup.find("div", class_="post-body")
        or soup.find("div", class_="post-entry")
        or soup.find("article")
    )

    if not content_div:
        print("Gagal menemukan konten artikel pada halaman.")
        return

    # Bersihkan isi konten dari elemen navigasi/style bawaan web
    cleaned_body_html = clean_and_format_content(content_div)

    # 3. Format CSS Layak Baca / PDF Book Styling
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

            blockquote {{
                background: #f9f9f9;
                border-left: 4px solid #ccc;
                margin: 10px 0;
                padding: 10px;
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

    # 4. Simpan ke PDF
    print("Mengonversi ke PDF...")
    with open(output_pdf_name, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

    if pisa_status.err:
        print("Terjadi kesalahan saat membuat PDF.")
    else:
        print(f"Berhasil! PDF tersimpan di: {os.path.abspath(output_pdf_name)}")


if __name__ == "__main__":
    url = "https://target.blogspot.com/2026/10/url-post.html"
    blogspot_to_pdf(url, "single_post.pdf")