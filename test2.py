from langchain_core.documents import Document
import PyPDF2
from io import BytesIO
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse


def extract_text_from_pdf(url):
    """Extract text from PDF files"""
    try:
        response = requests.get(url)
        pdf_file = BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_file)
        return "\n".join([page.extract_text() for page in reader.pages])
    except Exception as e:
        print(f"Error processing PDF {url}: {e}")
        return ""

def fetch_all_pages(start_url):
    """Recursively crawl all pages under the same domain"""
    parsed_start = urlparse(start_url)
    visited = set()
    queue = [start_url]
    pages_content = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            # Handle PDF files
            if url.lower().endswith('.pdf'):
                text = extract_text_from_pdf(url)
                if text:
                    pages_content.append(Document(page_content=text, metadata={"source": url}))
                continue

            # Handle HTML pages
            response = requests.get(url, headers=headers, timeout=10)
            content_type = response.headers.get('Content-Type', '')

            if 'text/html' not in content_type:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text(separator='\n', strip=True)
            pages_content.append(Document(page_content=page_text, metadata={"source": url}))

            # Extract and queue links
            for link in soup.find_all('a', href=True):
                href = link['href'].split('#')[0]  # Remove anchors
                absolute_url = urljoin(url, href)
                parsed = urlparse(absolute_url)

                # Normalize URL and check domain
                if parsed.netloc == parsed_start.netloc:
                    normalized = parsed.geturl()
                    if normalized not in visited:
                        queue.append(normalized)

        except Exception as e:
            print(f"Error processing {url}: {e}")

    return pages_content

# Scrape all content from the documentation site
pages_content = fetch_all_pages("https://docs.creditchek.africa")
print(pages_content)