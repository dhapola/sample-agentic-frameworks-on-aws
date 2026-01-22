"""
Performance timing instrumentation for agent nodes.

Provides decorators and utilities to measure and log execution time
of agent operations for performance monitoring and optimization.
"""

import time
from functools import wraps
from typing import Callable, Any, Dict


class PerformanceMonitor:
    """Tracks timing metrics for agent operations."""

    def __init__(self):
        self.timings: Dict[str, list] = {}
        self.enabled = True

    def record(self, operation: str, duration_ms: float):
        """Record a timing measurement."""
        if not self.enabled:
            return

        if operation not in self.timings:
            self.timings[operation] = []
        self.timings[operation].append(duration_ms)

    def get_stats(self, operation: str = None) -> Dict[str, Any]:
        """Get timing statistics for an operation or all operations."""
        if operation:
            if operation not in self.timings:
                return {}

            durations = self.timings[operation]
            return {
                "operation": operation,
                "count": len(durations),
                "total_ms": sum(durations),
                "avg_ms": sum(durations) / len(durations) if durations else 0,
                "min_ms": min(durations) if durations else 0,
                "max_ms": max(durations) if durations else 0
            }

        # Return stats for all operations
        return {
            op: self.get_stats(op)
            for op in self.timings.keys()
        }

    def print_summary(self):
        """Print a summary of all timing statistics."""
        if not self.timings:
            print("[Timing] No timing data recorded")
            return

        print("\n" + "=" * 70)
        print("PERFORMANCE SUMMARY")
        print("=" * 70)

        all_stats = self.get_stats()
        for operation, stats in sorted(all_stats.items()):
            if not stats:
                continue

            print(f"\n{operation}:")
            print(f"  Count:   {stats['count']}")
            print(f"  Total:   {stats['total_ms']:.2f}ms")
            print(f"  Average: {stats['avg_ms']:.2f}ms")
            print(f"  Min:     {stats['min_ms']:.2f}ms")
            print(f"  Max:     {stats['max_ms']:.2f}ms")

        print("=" * 70 + "\n")

    def clear(self):
        """Clear all timing data."""
        self.timings.clear()


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def timing_decorator(operation_name: str):
    """
    Decorator to measure and log execution time of a function.

    Args:
        operation_name: Name of the operation being timed

    Example:
        @timing_decorator("load_memory")
        def load_memory(state: State):
            # ... function code
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                _performance_monitor.record(operation_name, elapsed_ms)
                print(f"[Timing] {operation_name}: {elapsed_ms:.2f}ms")

        return wrapper
    return decorator


def measure_time(operation_name: str):
    """
    Context manager to measure execution time of a code block.

    Example:
        with measure_time("opensearch_query"):
            result = client.search(...)
    """
    class TimingContext:
        def __init__(self, name: str):
            self.name = name
            self.start_time = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed_ms = (time.time() - self.start_time) * 1000
            _performance_monitor.record(self.name, elapsed_ms)
            print(f"[Timing] {self.name}: {elapsed_ms:.2f}ms")

    return TimingContext(operation_name)
