import asyncio
import json
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Set, Dict, List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import html2text
from config import config


class APIDocCrawler:
    def __init__(self):
        self.base_url = config.API_DOC_URL
        self.storage_path = Path(config.API_DOC_STORAGE_PATH)
        self.max_depth = config.API_DOC_MAX_DEPTH
        self.crawl_delay = config.API_DOC_CRAWL_DELAY
        self.max_pages = config.API_DOC_MAX_PAGES
        self.verbose = config.API_DOC_VERBOSE
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.visited: Set[str] = set()
        self.index: List[Dict] = []
        self.base_domain = urlparse(self.base_url).netloc
    
    def _get_file_hash(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()
    
    def _is_same_domain(self, url: str) -> bool:
        return urlparse(url).netloc == self.base_domain
    
    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    async def _crawl_page(self, crawler: AsyncWebCrawler, url: str, depth: int) -> Dict:
        if self.verbose:
            print(f"Crawling [{depth}]: {url}")
        
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for_images=False,
            process_iframes=False,
            remove_overlay_elements=False,  # Keep overlays for now
            page_timeout=60000,
            wait_until="networkidle",
            delay_before_return_html=5.0,  # Give React time to render
            js_code=[
                "const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));",
                "await sleep(3000);"  # Additional wait
            ]
        )
        
        result = await crawler.arun(url=url, config=run_config)
        
        if not result.success:
            if self.verbose:
                print(f"Failed to crawl: {url}")
            return None
        
        # Debug output
        if self.verbose:
            print(f"HTML length: {len(result.html) if result.html else 0}")
            print(f"Markdown length: {len(result.markdown.raw_markdown) if result.markdown else 0}")
            print(f"Links found: {len(result.links.get('internal', [])) if result.links else 0}")
            
            # Save HTML for debugging
            with open('debug.html', 'w', encoding='utf-8') as f:
                f.write(result.html)
        
        # Initialize links list
        links = []
        
        # Manual markdown conversion if Crawl4AI fails
        content = ""
        if result.markdown and result.markdown.fit_markdown:
            content = result.markdown.fit_markdown
        elif result.markdown and result.markdown.raw_markdown and len(result.markdown.raw_markdown) > 10:
            content = result.markdown.raw_markdown
        else:
            # Fallback: manual conversion focusing on main content
            soup = BeautifulSoup(result.html, 'html.parser')
            
            # Try to find the main content area (ReadMe.io specific)
            main_content = (
                soup.find(class_='markdown-body') or
                soup.find('article') or
                soup.find('main') or
                soup.find(attrs={'class': lambda x: x and 'Article' in x}) or
                soup.find('body')
            )
            
            if main_content:
                # Remove unwanted elements
                for element in main_content.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()
                
                # Convert to markdown
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.body_width = 0
                content = h.handle(str(main_content))
        
        # Extract links from HTML manually
        soup = BeautifulSoup(result.html, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            link_url = a_tag['href']
            
            # Skip anchor links and javascript
            if link_url.startswith('#') or link_url.startswith('javascript:'):
                continue
                
            # Convert relative URLs to absolute
            if not link_url.startswith(('http://', 'https://')):
                link_url = urljoin(url, link_url)
                
            if link_url and self._is_same_domain(link_url):
                normalized = self._normalize_url(link_url)
                if normalized not in self.visited and normalized not in links:
                    links.append(normalized)
        
        page_data = {
            "url": url,
            "title": result.metadata.get("title", ""),
            "content": content,
            "links": list(set(links)),
            "depth": depth
        }
        
        return page_data
    
    async def _save_page(self, page_data: Dict):
        file_hash = self._get_file_hash(page_data["url"])
        file_path = self.storage_path / f"{file_hash}.json"
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(page_data, f, indent=2, ensure_ascii=False)
        
        self.index.append({
            "url": page_data["url"],
            "title": page_data["title"],
            "file": f"{file_hash}.json",
            "depth": page_data["depth"]
        })
    
    async def crawl(self):
        browser_config = BrowserConfig(
            headless=True,
            verbose=self.verbose
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            queue = [(self.base_url, 0)]
            
            while queue and len(self.visited) < self.max_pages:
                url, depth = queue.pop(0)
                
                if url in self.visited or depth > self.max_depth:
                    continue
                
                self.visited.add(url)
                
                page_data = await self._crawl_page(crawler, url, depth)
                
                if page_data:
                    await self._save_page(page_data)
                    
                    if depth < self.max_depth:
                        for link in page_data["links"]:
                            if link not in self.visited:
                                queue.append((link, depth + 1))
                
                await asyncio.sleep(self.crawl_delay)
        
        # Save index
        index_path = self.storage_path / "index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
        
        print(f"\nCrawling complete!")
        print(f"Pages crawled: {len(self.visited)}")
        print(f"Data saved to: {self.storage_path}")


async def main():
    crawler = APIDocCrawler()
    await crawler.crawl()


if __name__ == "__main__":
    asyncio.run(main())
