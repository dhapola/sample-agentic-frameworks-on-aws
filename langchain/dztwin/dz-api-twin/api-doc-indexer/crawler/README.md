# API Documentation Crawler

Web crawler using Crawl4AI for LLM-optimized extraction of API documentation.

## Features

- **Crawl4AI powered** - LLM-optimized content extraction
- **Async architecture** - Fast parallel processing with asyncio
- **Clean markdown output** - AI-friendly content format
- **Domain-restricted** - Stays within your documentation site
- **Configurable depth** - Control crawl scope and limits
- **Polite crawling** - Configurable delays between requests
- **Smart link extraction** - Handles relative and absolute URLs
- **Fallback parsing** - Multiple strategies for content extraction
- **MD5 hash filenames** - Unique, collision-free file naming
- **Master index** - Quick lookup of all crawled pages

## Quick Setup

```bash
./setup.sh  # Unix/macOS
# or
setup.bat   # Windows
```

This will:
1. Install Python dependencies
2. Install Playwright browsers
3. Copy `.env.example` to `.env` (if needed)

## Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

## Configuration

### Environment Variables

Create `.env` file (copy from `.env.example`):

```env
# Required: Base URL of API documentation
API_DOC_URL=https://docs.stripe.com/api

# Storage path for crawled data
API_DOC_STORAGE_PATH=./data

# Maximum crawl depth (0 = only base URL)
API_DOC_MAX_DEPTH=3

# Delay between requests in seconds (be polite!)
API_DOC_CRAWL_DELAY=1.0

# Maximum number of pages to crawl
API_DOC_MAX_PAGES=100

# Enable verbose logging
API_DOC_VERBOSE=false
```

### Configuration Options

- `API_DOC_URL` (required) - Base URL to start crawling
  - Example: `https://docs.stripe.com/api`
  - Must be a valid HTTP/HTTPS URL
  - Crawler will stay within this domain

- `API_DOC_STORAGE_PATH` (default: `./data`) - Output directory
  - Relative or absolute path
  - Created automatically if doesn't exist

- `API_DOC_MAX_DEPTH` (default: `3`) - Maximum crawl depth
  - `0` = Only base URL
  - `1` = Base URL + direct links
  - `2` = Base URL + links + their links
  - `3` = Three levels deep (recommended)

- `API_DOC_CRAWL_DELAY` (default: `1.0`) - Delay between requests
  - In seconds (float)
  - Recommended: 1.0-2.0 seconds
  - Be respectful to the server

- `API_DOC_MAX_PAGES` (default: `100`) - Maximum pages to crawl
  - Safety limit to prevent runaway crawls
  - Adjust based on documentation size

- `API_DOC_VERBOSE` (default: `false`) - Enable verbose logging
  - `true` = Detailed logging with HTML debugging
  - `false` = Minimal logging

## Usage

### Basic Crawl

```bash
python crawler.py
```

Output:
```
Crawling [0]: https://docs.stripe.com/api
Crawling [1]: https://docs.stripe.com/api/authentication
Crawling [1]: https://docs.stripe.com/api/errors
...
Crawling complete!
Pages crawled: 42
Data saved to: ./data
```

### Check Output

```bash
# List crawled files
ls -la data/

# View index
cat data/index.json

# View specific page
cat data/6dfcce406a27f79f27b782446a2fb4c5.json
```

## Output Format

### Directory Structure

```
data/
├── index.json                              # Master index
├── 6dfcce406a27f79f27b782446a2fb4c5.json  # Page data (MD5 hash)
├── 72bb680d8b52a4cf1538de8053675abb.json
└── ...
```

### Index File (`index.json`)

Master index of all crawled pages:

```json
[
  {
    "url": "https://docs.stripe.com/api",
    "title": "Stripe API Reference",
    "file": "6dfcce406a27f79f27b782446a2fb4c5.json",
    "depth": 0
  },
  {
    "url": "https://docs.stripe.com/api/authentication",
    "title": "Authentication",
    "file": "72bb680d8b52a4cf1538de8053675abb.json",
    "depth": 1
  }
]
```

### Page Data Files

Each page is saved as JSON with MD5 hash filename:

```json
{
  "url": "https://docs.stripe.com/api/authentication",
  "title": "Authentication",
  "content": "# Authentication\n\nAuthenticate your API requests...",
  "links": [
    "https://docs.stripe.com/api/errors",
    "https://docs.stripe.com/api/idempotent_requests"
  ],
  "depth": 1
}
```

**Fields:**
- `url` - Full URL of the page
- `title` - Page title from metadata
- `content` - Markdown-formatted content
- `links` - Array of discovered links (same domain only)
- `depth` - Crawl depth (0 = base URL)

## How It Works

### Crawling Process

1. **Initialize** - Load configuration, create storage directory
2. **Queue** - Start with base URL at depth 0
3. **Crawl** - For each URL:
   - Check if already visited
   - Check depth limit
   - Fetch page with Crawl4AI
   - Extract content and links
   - Save to JSON file
   - Add links to queue
   - Wait for configured delay
4. **Complete** - Save master index

### Content Extraction

The crawler uses multiple strategies:

1. **Crawl4AI fit_markdown** - LLM-optimized extraction (preferred)
2. **Crawl4AI raw_markdown** - Raw markdown conversion
3. **Fallback HTML parsing** - BeautifulSoup + html2text
   - Targets main content areas
   - Removes navigation, scripts, styles
   - Converts to clean markdown

### Link Extraction

- Extracts all `<a href>` tags from HTML
- Converts relative URLs to absolute
- Filters to same domain only
- Normalizes URLs (removes fragments, query params)
- Deduplicates links

### File Naming

Uses MD5 hash of URL for filenames:
- Collision-free
- Consistent across runs
- URL-safe
- Easy to lookup

## Advanced Usage

### Crawl Specific Documentation

```bash
# Stripe API
API_DOC_URL=https://docs.stripe.com/api python crawler.py

# OpenAI API
API_DOC_URL=https://platform.openai.com/docs/api-reference python crawler.py

# GitHub API
API_DOC_URL=https://docs.github.com/en/rest python crawler.py
```

### Deep Crawl

For comprehensive documentation:
```env
API_DOC_MAX_DEPTH=5
API_DOC_MAX_PAGES=500
API_DOC_CRAWL_DELAY=2.0
```

### Quick Crawl

For testing or small docs:
```env
API_DOC_MAX_DEPTH=1
API_DOC_MAX_PAGES=20
API_DOC_CRAWL_DELAY=0.5
```

### Debug Mode

Enable verbose logging:
```env
API_DOC_VERBOSE=true
```

This will:
- Log HTML length and markdown length
- Save `debug.html` for inspection
- Show link extraction details

## Integration with Ingester

After crawling, use the ingester to create vector embeddings:

```bash
cd ../ingester
python ingest.py
```

The ingester will:
1. Load documents from `../crawler/data`
2. Generate embeddings
3. Store in Qdrant vector database
4. Enable semantic search

See [ingester README](../ingester/README.md) for details.

## Troubleshooting

### No content extracted

**Symptoms:**
- Empty or very short markdown content
- Missing page data

**Solutions:**
1. Enable verbose mode: `API_DOC_VERBOSE=true`
2. Check `debug.html` for page structure
3. Increase `delay_before_return_html` in `crawler.py`
4. Check if site requires authentication
5. Verify site allows crawling (robots.txt)

### Crawler stops early

**Symptoms:**
- Fewer pages than expected
- Stops before MAX_PAGES

**Solutions:**
1. Check if links are same domain
2. Verify depth limit isn't too low
3. Check for crawl errors in logs
4. Increase MAX_PAGES if needed

### Rate limiting / blocked

**Symptoms:**
- HTTP 429 errors
- Connection timeouts
- Empty responses

**Solutions:**
1. Increase `API_DOC_CRAWL_DELAY` (2.0-5.0 seconds)
2. Reduce `API_DOC_MAX_PAGES`
3. Check site's robots.txt
4. Use VPN if IP is blocked
5. Contact site owner for permission

### Memory issues

**Symptoms:**
- Out of memory errors
- Slow performance

**Solutions:**
1. Reduce `API_DOC_MAX_PAGES`
2. Reduce `API_DOC_MAX_DEPTH`
3. Clear `data/` directory between runs
4. Increase system memory

## Best Practices

### Be Respectful

- Use reasonable delays (1-2 seconds minimum)
- Don't crawl during peak hours
- Respect robots.txt
- Check site's terms of service
- Contact site owner if crawling large amounts

### Optimize Performance

- Start with small depth (1-2) for testing
- Use verbose mode for debugging only
- Clear old data before re-crawling
- Monitor disk space

### Data Quality

- Review crawled content manually
- Check for missing pages
- Verify markdown formatting
- Test with ingester before production

## File Structure

```
crawler/
├── crawler.py           # Main crawler implementation
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── setup.sh/bat        # Setup scripts
├── .env.example        # Environment template
├── .env                # Local config (gitignored)
├── .gitignore          # Ignore data and env files
├── __init__.py         # Package initialization
├── README.md           # This file
└── data/               # Crawled data (gitignored)
    ├── index.json      # Master index
    └── *.json          # Page data files
```

## Dependencies

- `crawl4ai` - LLM-friendly web crawler
- `beautifulsoup4` - HTML parsing (fallback)
- `html2text` - HTML to markdown conversion
- `playwright` - Browser automation
- `python-dotenv` - Environment management
- `pydantic-settings` - Configuration validation

See [requirements.txt](requirements.txt) for complete list.

## Performance

- **Async architecture** - Parallel processing with asyncio
- **Configurable delays** - Balance speed vs. politeness
- **Efficient storage** - JSON with MD5 hash filenames
- **Memory efficient** - Processes pages one at a time

## Limitations

- **Same domain only** - Won't follow external links
- **No authentication** - Can't crawl protected content
- **JavaScript heavy sites** - May miss dynamically loaded content
- **Rate limiting** - May be blocked by aggressive rate limits

## Future Enhancements

- [ ] Authentication support
- [ ] Sitemap.xml parsing
- [ ] Incremental crawling (only new/changed pages)
- [ ] Multi-domain support
- [ ] Custom content selectors
- [ ] Parallel crawling
- [ ] Progress persistence (resume after crash)

## License

MIT
