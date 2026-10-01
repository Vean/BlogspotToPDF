# Blogspot Content to PDF Downloader

A Python-based utility tool to scrape Blogspot content posts and convert them into clean, well-formatted, e-book styled PDF files.

---

## 🌟 Features

- **Single Post Downloader**: Converts a specific Blogspot page into a PDF.
- **Batch Chapter Downloader**: Automatically iterates through chapter navigation links (`« Prev Post`, `Next Post`, etc.) to download entire content series in sequential order.
- **Text-Optimized Layout**: Formats typography using Georgia serif fonts, clean paragraph indentations, justified alignment, headers, and automatic page numbers.
- **Content Sanitization**: Automatically removes unwanted web elements like navigation buttons, headers, footers, embedded ads, and inline styles.

---

## 🛠️ Prerequisites & Setup

Follow these steps to set up the environment and run the scripts without uploading the heavy `venv/` directory to Git.

### 1. Clone the Repository

```bash
git clone https://github.com/Vean/BlogspotToPDF.git
cd BlogspotToPDF
```

### 2. Create & Activate Virtual Environment

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

Install all required Python packages listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 🚀 How to Use

### 1. Batch Download (Multiple Chapters / Entire Series)

Use `batch_by_page.py` to auto-crawl from a starting chapter through subsequent chapters and save each as an individual formatted PDF in the `export/` folder.

1. Open `batch_by_page.py` and set your starting URL at the bottom:
   ```python
   if __name__ == "__main__":
       start_url = "https://target.blogspot.com/2026/10/url-post.html"
       download_blogspot_batch(start_url=start_url, base_filename="Content_Name", export_folder="export")
   ```
2. Run the script:
   ```bash
   python batch_by_page.py
   ```

### 2. Single Page Download

Use `single_post.py` (or your single-script file) to quickly download and convert only one specific article or chapter.

1. Open `single_post.py` and specify the target URL:
   ```python
   if __name__ == "__main__":
       url = "https://target.blogspot.com/2026/10/url-post.html"
       blogspot_to_pdf(url, "single_post.pdf")
   ```
2. Run the script:
   ```bash
   python single_post.py
   ```

---

## 📁 Output Directory Structure

```text
├── batch_by_page.py       # Batch crawler script
├── single_post.py         # Single post downloader script
├── requirements.txt       # Dependencies list
├── .gitignore             # Keeps venv and generated files out of Git
├── README.md              # Project documentation
└── export/                # Generated PDFs directory (auto-created)
    ├── Content_1.pdf
    ├── Content_2.pdf
    └── ...
```

---

## 📄 License

This project is open-source and intended for personal archiving and offline reading purposes, use with heart.