import os
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from langchain.schema import Document
import json

class DocumentScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.visited_urls = set()
        self.docs = []
    
    def crawl(self, max_pages: int = 300) -> List[Document]:
        """Crawl the documentation site and extract content"""
        # Check if URL is reachable first
        try:
            # Use a timeout to avoid hanging
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                self._crawl_page(self.base_url, max_pages)
            else:
                print(f"Warning: Site returned status code {response.status_code}")
                self._use_fallback_data()
        except Exception as e:
            print(f"Error accessing {self.base_url}: {e}")
            print("Using fallback documentation data...")
            self._use_fallback_data()
            
        return self.docs
    

            
    def _extract_api_info_from_text(self, text: str) -> Dict[str, Any]:
        """Extract API info from text content"""
        api_info = {
            "endpoints": [],
            "methods": [],
            "parameters": []
        }
        
        # Extract endpoints and methods
        endpoint_matches = re.findall(r'Endpoint:\s+((?:GET|POST|PUT|DELETE|PATCH)\s+/\S+)', text)
        for endpoint_str in endpoint_matches:
            parts = endpoint_str.split()
            if len(parts) >= 2:
                method, path = parts[0], parts[1]
                api_info["endpoints"].append(path)
                api_info["methods"].append(method)
        
        # Extract parameters
        param_section = re.search(r'Parameters:(.+?)(?:Response:|$)', text, re.DOTALL)
        if param_section:
            param_lines = param_section.group(1).strip().split('\n')
            for line in param_lines:
                # Look for parameter name and description
                param_match = re.search(r'-\s+(\w+):\s+(\w+)\s+\(([^)]+)\)\s*-\s*(.*)', line)
                if param_match:
                    name, type_str, required, description = param_match.groups()
                    api_info["parameters"].append({
                        "name": name,
                        "type": type_str,
                        "required": "Required" in required,
                        "description": description.strip()
                    })
        
        return api_info
        
    def _crawl_page(self, url: str, max_pages: int, depth: int = 0) -> None:
        """Recursively crawl pages up to max_pages"""
        if len(self.visited_urls) >= max_pages or url in self.visited_urls:
            return
            
        if not url.startswith(self.base_url):
            return
            
        print(f"Crawling: {url}")
        self.visited_urls.add(url)
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract main content
            main_content = soup.find('main') or soup.find('div', class_='content') or soup.find('article')
            if main_content:
                # Clean the content
                for tag in main_content.find_all(['script', 'style']):
                    tag.decompose()
                
                content = main_content.get_text(separator='\n').strip()
                # Remove extra whitespace
                content = re.sub(r'\n+', '\n', content)
                content = re.sub(r'\s+', ' ', content)
                
                # Extract title
                title = soup.find('title')
                title_text = title.get_text() if title else url
                
                # Extract API endpoints, methods, parameters from content
                api_info = self._extract_api_info(main_content)
                
                # Create document
                if content:
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": url,
                            "title": title_text,
                            "api_info": api_info
                        }
                    )
                    self.docs.append(doc)
            
            # Find more links to crawl
            if depth < 3:  # Limit depth to avoid crawling too deep
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('/'):
                        href = self.base_url + href
                    elif not href.startswith('http'):
                        continue
                    
                    if href.startswith(self.base_url) and href not in self.visited_urls:
                        self._crawl_page(href, max_pages, depth + 1)
                        
        except Exception as e:
            print(f"Error crawling {url}: {e}")
    
    def _extract_api_info(self, content) -> Dict[str, Any]:
        """Extract API information from the content"""
        api_info = {
            "endpoints": [],
            "methods": [],
            "parameters": []
        }
        
        # Look for API endpoints in code blocks
        code_blocks = content.find_all('pre')
        for block in code_blocks:
            code = block.get_text()
            # Look for HTTP methods and URLs
            endpoint_matches = re.findall(r'(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)', code)
            for method, endpoint in endpoint_matches:
                api_info["endpoints"].append(endpoint)
                api_info["methods"].append(method)
            
            # Look for parameters in code or tables
            param_matches = re.findall(r'["\']([\w_]+)["\']:\s*(?:["\'](.*?)["\']|(\d+))', code)
            for param, string_value, num_value in param_matches:
                value = string_value or num_value
                api_info["parameters"].append({"name": param, "example": value})
                
        # Also look for tables which often contain API parameters
        tables = content.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            headers = [th.get_text().strip().lower() for th in rows[0].find_all(['th', 'td'])] if rows else []
            
            if 'parameter' in headers or 'name' in headers:
                name_index = headers.index('parameter') if 'parameter' in headers else headers.index('name')
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > name_index:
                        param_name = cells[name_index].get_text().strip()
                        param_info = {"name": param_name}
                        
                        # Look for description, type, required fields
                        for i, header in enumerate(headers):
                            if i < len(cells) and i != name_index:
                                param_info[header] = cells[i].get_text().strip()
                                
                        api_info["parameters"].append(param_info)
                        
        return api_info

# Example usage
if __name__ == "__main__":
    scraper = DocumentScraper("https://docs.creditchek.africa/category/nigeria-")
    docs = scraper.crawl(max_pages=500)
    print(f"Total documents collected: {docs}")
    
   