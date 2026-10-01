import json
import os
import re
import requests
from bs4 import BeautifulSoup
from xhtml2pdf import pisa

PROGRESS_FILE = "download_progress.json"


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"completed_urls": []}
    return {"completed_urls": []}


def save_progress(completed_url):
    progress = load_progress()
    if completed_url not in progress["completed_urls"]:
        progress["completed_urls"].append(completed_url)

    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=4)


def convert_html_to_pdf(html_content, output_path):
    with open(output_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
    return not pisa_status.err


def sanitize_filename(filename):
    clean_name = re.sub(r'[\\/*?:"<>|]', "", filename)
    clean_name = re.sub(r"\s+", " ", clean_name).strip()
    return clean_name[:150]


def clean_and_format_content(content_div):
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

    for tag in content_div.find_all(
        class_=re.compile(r"blog-pager|post-footer|share|nav|pager", re.I)
    ):
        tag.decompose()

    for tag in content_div.find_all(
        id=re.compile(r"blog-pager|post-footer|nav|pager", re.I)
    ):
        tag.decompose()

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

    for tag in content_div.find_all(True):
        if "style" in tag.attrs:
            del tag.attrs["style"]
        if "class" in tag.attrs:
            del tag.attrs["class"]

    raw_html = str(content_div)
    raw_html = re.sub(r"(<br\s*/?>\s*){2,}", "</p><p>", raw_html)

    soup = BeautifulSoup(raw_html, "html.parser")

    for p in soup.find_all(["p", "div", "span"]):
        text = " ".join(p.get_text().split()).strip().lower()
        if not text and not p.find_all("img"):
            p.decompose()
        elif any(kw in text for kw in nav_keywords) and len(text) < 30:
            p.decompose()

    return str(soup)


def get_post_mapping_from_feed(blog_domain):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    url_to_title = {}
    start_index = 1
    max_results = 150

    print("=== Mengambil Metadata Judul Asli dari Blogger Feed ===")

    while True:
        feed_url = f"https://{blog_domain}/feeds/posts/default?alt=json&max-results={max_results}&start-index={start_index}"
        try:
            res = requests.get(feed_url, headers=headers, timeout=15)
            if res.status_code != 200:
                break

            data = res.json()
            entries = data.get("feed", {}).get("entry", [])

            if not entries:
                break

            for entry in entries:
                title = entry.get("title", {}).get("$t", "").strip()
                link_url = ""
                for link in entry.get("link", []):
                    if (
                        link.get("rel") == "alternate"
                        and link.get("type") == "text/html"
                    ):
                        link_url = link.get("href")
                        break

                if link_url and title:
                    clean_url = (
                        link_url.replace("http://", "")
                        .replace("https://", "")
                        .strip()
                    )
                    url_to_title[clean_url] = title

            if len(entries) < max_results:
                break

            start_index += max_results

        except Exception as e:
            print(f"[-] Gagal membaca Feed JSON: {e}")
            break

    print(f"[+] Berhasil memetakan {len(url_to_title)} judul asli dari Feed!")
    return url_to_title


def fetch_all_posts_from_sitemap(blog_domain):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    all_entries = []
    seen_urls = set()
    page = 1

    print(f"=== Memindai Sitemap XML ({blog_domain}) ===")

    while True:
        sitemap_url = (
            f"https://{blog_domain}/sitemap.xml?page={page}&max-results=500"
        )

        try:
            res = requests.get(sitemap_url, headers=headers, timeout=15)
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.content, "xml")
            urls = soup.find_all("url")

            if not urls:
                break

            for url_tag in urls:
                loc = url_tag.find("loc")
                if not loc:
                    continue

                link_url = loc.text.strip()

                if (
                    ".html" in link_url
                    and "/p/" not in link_url
                    and link_url not in seen_urls
                ):
                    seen_urls.add(link_url)
                    all_entries.append({"url": link_url})

            print(
                f"[+] Sitemap Halaman {page}: Terdeteksi {len(all_entries)} postingan..."
            )
            page += 1

        except Exception as e:
            print(f"[-] Error membaca sitemap: {e}")
            break

    all_entries.reverse()
    return all_entries


def backup_full_blog(blog_domain, export_folder="Exports PDF"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    os.makedirs(export_folder, exist_ok=True)

    progress = load_progress()
    completed_urls = set(progress.get("completed_urls", []))

    feed_titles = get_post_mapping_from_feed(blog_domain)
    posts = fetch_all_posts_from_sitemap(blog_domain)

    print(
        f"\n[SUMMARY] Berhasil mengindeks {len(posts)} total postingan dari Sitemap!"
    )

    if not posts:
        print("[-] Tidak ada postingan yang ditemukan.")
        return

    for index, post in enumerate(posts, start=1):
        url = post["url"]
        clean_url_key = (
            url.replace("http://", "").replace("https://", "").strip()
        )

        if url in completed_urls:
            print(f"[{index}/{len(posts)}] Skip (Sudah terproses): {url}")
            continue

        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200:
                print(f"[-] Skip. Status Code: {res.status_code}")
                continue

            soup = BeautifulSoup(res.text, "html.parser")

            title_text = feed_titles.get(clean_url_key)

            if not title_text:
                title_tag = (
                    soup.find(
                        "h3",
                        class_=re.compile(r"post-title|entry-title", re.I),
                    )
                    or soup.find(
                        "h1",
                        class_=re.compile(r"post-title|entry-title", re.I),
                    )
                    or soup.find("h1")
                )

                if title_tag:
                    title_text = title_tag.get_text().strip()
                else:
                    slug = (
                        url.split("/")[-1]
                        .replace(".html", "")
                        .replace("-", " ")
                    )
                    title_text = slug.title()

            title_text = re.sub(
                r"\s*[-|~:]\s*Grensia.*$", "", title_text, flags=re.I
            ).strip()

            safe_title = sanitize_filename(title_text)

            # PENYESUAIAN: Hanya menggunakan judul artikel tanpa prefix angka
            file_name = f"{safe_title}.pdf"
            pdf_path = os.path.join(export_folder, file_name)

            if os.path.exists(pdf_path):
                print(f"[{index}/{len(posts)}] Skip (PDF Ada): {safe_title}")
                save_progress(url)
                continue

            print(f"[{index}/{len(posts)}] Mengunduh: {title_text}")

            content_div = (
                soup.find("div", class_="post-body")
                or soup.find("div", class_="post-entry")
                or soup.find("article")
            )

            if not content_div:
                print("[-] Konten postingan tidak ditemukan, skip.")
                continue

            cleaned_html = clean_and_format_content(content_div)

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
                            font-family: Georgia, serif;
                            font-size: 9pt;
                            color: #666666;
                        }}
                    }}
                    body {{
                        font-family: Georgia, serif;
                        font-size: 11pt;
                        line-height: 1.6;
                        color: #111111;
                        text-align: justify;
                    }}
                    h1.post-title {{
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
                </style>
            </head>
            <body>
                <h1 class="post-title">{title_text}</h1>
                <div>{cleaned_html}</div>
            </body>
            </html>
            """

            if convert_html_to_pdf(html_content, pdf_path):
                print(f"[+] Tersimpan: {file_name}")
                save_progress(url)
            else:
                print(f"[-] Gagal konversi PDF: {file_name}")

        except Exception as e:
            print(f"[-] Error saat mengunduh: {e}")

    print(
        f"\n🎉 Selesai! Seluruh postingan tersimpan di '{export_folder}/'."
    )


if __name__ == "__main__":
    backup_full_blog(
        blog_domain="target.blogspot.com",
        export_folder="folder_name_pdf"  
    )