#!/usr/bin/env python3
"""
Diagnostic tool to analyze crawler data quality
"""
import json
from pathlib import Path
from collections import Counter
from config import config


def analyze_crawler_data():
    """Analyze crawler output for quality issues"""
    
    data_dir = Path(config.CRAWLER_DATA_PATH)
    index_file = data_dir / "index.json"
    
    if not index_file.exists():
        print(f"❌ Index file not found: {index_file}")
        return
    
    with open(index_file, "r", encoding="utf-8") as f:
        index = json.load(f)
    
    print("=" * 60)
    print("📊 CRAWLER DATA DIAGNOSTICS")
    print("=" * 60)
    
    # Load all documents
    documents = []
    for entry in index:
        file_path = data_dir / entry["file"]
        with open(file_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
            documents.append(doc)
    
    # Analyze documents
    total_docs = len(documents)
    empty_docs = sum(1 for d in documents if not d.get("content", "").strip())
    
    content_lengths = [len(d.get("content", "")) for d in documents if d.get("content", "").strip()]
    
    print(f"\n📁 Documents:")
    print(f"   Total: {total_docs}")
    print(f"   Empty: {empty_docs} ({empty_docs/total_docs*100:.1f}%)")
    print(f"   With content: {len(content_lengths)}")
    
    if content_lengths:
        print(f"\n📏 Content Size:")
        print(f"   Average: {sum(content_lengths)/len(content_lengths):.0f} chars")
        print(f"   Min: {min(content_lengths)} chars")
        print(f"   Max: {max(content_lengths)} chars")
        print(f"   Median: {sorted(content_lengths)[len(content_lengths)//2]} chars")
    
    # Analyze URLs
    urls = [d.get("url", "") for d in documents]
    unique_urls = len(set(urls))
    duplicate_urls = total_docs - unique_urls
    
    print(f"\n🔗 URLs:")
    print(f"   Unique: {unique_urls}")
    print(f"   Duplicates: {duplicate_urls}")
    
    # Analyze titles
    empty_titles = sum(1 for d in documents if not str(d.get("title", "")).strip())
    print(f"\n📝 Titles:")
    print(f"   Empty: {empty_titles} ({empty_titles/total_docs*100:.1f}%)")
    
    # Estimate chunks
    estimated_chunks = 0
    for doc in documents:
        content = doc.get("content", "").strip()
        if not content:
            continue
        # Rough estimate: 1500 chars per chunk
        estimated_chunks += max(1, len(content) // 1500)
    
    print(f"\n📦 Estimated Chunks:")
    print(f"   Total: ~{estimated_chunks}")
    print(f"   Avg per doc: {estimated_chunks/total_docs:.1f}")
    
    # Check for common issues
    print(f"\n⚠️  Potential Issues:")
    issues = []
    
    if empty_docs > total_docs * 0.1:
        issues.append(f"   • High empty document rate ({empty_docs/total_docs*100:.1f}%)")
    
    if duplicate_urls > 0:
        issues.append(f"   • {duplicate_urls} duplicate URLs found")
    
    if empty_titles > total_docs * 0.2:
        issues.append(f"   • Many documents missing titles ({empty_titles/total_docs*100:.1f}%)")
    
    very_short = sum(1 for l in content_lengths if l < 100)
    if very_short > len(content_lengths) * 0.2:
        issues.append(f"   • {very_short} very short documents (<100 chars)")
    
    if not issues:
        print(f"   ✅ No major issues detected")
    else:
        for issue in issues:
            print(issue)
    
    # Sample some documents
    print(f"\n📄 Sample Documents:")
    for i, doc in enumerate(documents[:3]):
        content = doc.get("content", "")
        preview = content[:100].replace("\n", " ") if content else "[empty]"
        print(f"\n   {i+1}. {doc.get('title', 'No title')}")
        print(f"      URL: {doc.get('url', 'No URL')}")
        print(f"      Size: {len(content)} chars")
        print(f"      Preview: {preview}...")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    analyze_crawler_data()
