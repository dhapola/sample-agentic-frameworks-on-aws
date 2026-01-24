#!/usr/bin/env python3
"""
Benchmark script to estimate ingestion time based on configuration
"""
import json
from pathlib import Path
from config import config


def estimate_processing_time():
    """Estimate processing time based on current configuration"""
    
    # Load document count
    data_dir = Path(config.CRAWLER_DATA_PATH)
    index_file = data_dir / "index.json"
    
    if not index_file.exists():
        print(f"❌ Index file not found: {index_file}")
        return
    
    with open(index_file, "r", encoding="utf-8") as f:
        index = json.load(f)
    
    num_docs = len(index)
    
    # Estimate chunks (rough average: 6 chunks per document)
    estimated_chunks = num_docs * 6
    
    # Calculate batches
    num_batches = (estimated_chunks + config.BATCH_SIZE - 1) // config.BATCH_SIZE
    
    # Estimate time (more realistic for Bedrock API)
    # Each batch takes ~2-3 seconds (API call + network + processing)
    time_per_batch = 2.5  # seconds (realistic for Bedrock)
    
    # Old configuration estimate (BATCH_SIZE=32, sequential)
    old_batches = (estimated_chunks + 32 - 1) // 32
    old_time = old_batches * time_per_batch
    
    # New configuration (concurrent processing)
    # Total time = (total_batches / concurrent_batches) * time_per_batch
    concurrent_time = (num_batches / config.MAX_CONCURRENT_BATCHES) * time_per_batch
    
    print("=" * 60)
    print("📊 INGESTION PERFORMANCE ESTIMATE")
    print("=" * 60)
    print(f"\n📁 Dataset:")
    print(f"   Documents: {num_docs:,}")
    print(f"   Estimated chunks: {estimated_chunks:,}")
    
    print(f"\n⚙️  Current Configuration:")
    print(f"   Batch size: {config.BATCH_SIZE}")
    print(f"   Concurrent batches: {config.MAX_CONCURRENT_BATCHES}")
    print(f"   Total batches: {num_batches}")
    
    print(f"\n⏱️  Estimated Processing Time:")
    print(f"   Sequential (old): {old_time/60:.1f} minutes ({old_time/3600:.1f} hours)")
    print(f"   Concurrent (new): {concurrent_time/60:.1f} minutes")
    print(f"   Speedup: {old_time/concurrent_time:.1f}x faster")
    
    print(f"\n💡 Optimization Tips:")
    if concurrent_time > 1800:  # > 30 minutes
        print(f"   ⚠️  Processing will take {concurrent_time/60:.0f} minutes")
        print(f"   💡 Consider increasing MAX_CONCURRENT_BATCHES to {config.MAX_CONCURRENT_BATCHES * 2}")
        print(f"   💡 Or increase BATCH_SIZE to {config.BATCH_SIZE * 2}")
    elif concurrent_time < 300:  # < 5 minutes
        print(f"   ✅ Fast processing expected ({concurrent_time/60:.1f} minutes)")
    else:
        print(f"   ✅ Reasonable processing time ({concurrent_time/60:.1f} minutes)")
    
    print(f"\n🎯 Throughput:")
    if concurrent_time > 0:
        print(f"   Chunks per minute: {estimated_chunks / (concurrent_time / 60):.0f}")
        print(f"   Batches per second: {num_batches / concurrent_time:.2f}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    estimate_processing_time()
