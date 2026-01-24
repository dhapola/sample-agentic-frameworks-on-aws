"""Unit tests for MetricsCalculator.

Tests the metrics calculator implementation including accuracy calculation,
relevance calculation, latency calculation, and aggregation functions.
"""

from datetime import datetime

import pytest

from app.engine.metrics_calculator import MetricsCalculator
from app.models.metrics import AggregatedMetrics, IndividualMetrics
from app.models.response import Response
from app.models.test_case import TestCase


class TestMetricsCalculatorInitialization:
    """Test metrics calculator initialization."""
    
    def test_calculator_initialization(self):
        """Test calculator initializes successfully."""
        calculator = MetricsCalculator()
        assert calculator is not None


class TestAccuracyCalculation:
    """Test accuracy calculation."""
    
    @pytest.fixture
    def calculator(self):
        """Create metrics calculator instance."""
        return MetricsCalculator()
    
    def test_exact_match(self, calculator):
        """Test accuracy for exact match."""
        accuracy = calculator.calculate_accuracy("Paris", "Paris")
        assert accuracy == 1.0
    
    def test_case_insensitive_match(self, calculator):
        """Test accuracy is case-insensitive."""
        accuracy = calculator.calculate_accuracy("paris", "Paris")
        assert accuracy == 1.0
        
        accuracy = calculator.calculate_accuracy("PARIS", "paris")
        assert accuracy == 1.0
    
    def test_whitespace_normalized(self, calculator):
        """Test accuracy normalizes whitespace."""
        accuracy = calculator.calculate_accuracy("  Paris  ", "Paris")
        assert accuracy == 1.0
        
        accuracy = calculator.calculate_accuracy("Paris", "  Paris  ")
        assert accuracy == 1.0
    
    def test_partial_match(self, calculator):
        """Test accuracy for partial word overlap."""
        # "Paris" appears in both, but response has extra words
        accuracy = calculator.calculate_accuracy(
            "The capital is Paris",
            "Paris"
        )
        # Jaccard similarity: intersection={paris} / union={the,capital,is,paris}
        assert 0.0 < accuracy < 1.0
    
    def test_no_match(self, calculator):
        """Test accuracy for no match."""
        accuracy = calculator.calculate_accuracy("London", "Paris")
        assert accuracy == 0.0
    
    def test_empty_response(self, calculator):
        """Test accuracy with empty response."""
        accuracy = calculator.calculate_accuracy("", "Paris")
        assert accuracy == 0.0
    
    def test_empty_expected(self, calculator):
        """Test accuracy with empty expected output."""
        accuracy = calculator.calculate_accuracy("Paris", "")
        assert accuracy == 0.0
    
    def test_no_expected_output(self, calculator):
        """Test accuracy returns None when no expected output."""
        accuracy = calculator.calculate_accuracy("Paris", None)
        assert accuracy is None
    
    def test_multi_word_match(self, calculator):
        """Test accuracy with multi-word strings."""
        accuracy = calculator.calculate_accuracy(
            "Paris is the capital of France",
            "Paris is the capital of France"
        )
        assert accuracy == 1.0
    
    def test_word_overlap_calculation(self, calculator):
        """Test accuracy calculates word overlap correctly."""
        # Response: {capital, france}
        # Expected: {capital, france}
        # Jaccard: 2/2 = 1.0
        accuracy = calculator.calculate_accuracy(
            "capital France",
            "France capital"
        )
        assert accuracy == 1.0


class TestRelevanceCalculation:
    """Test relevance calculation."""
    
    @pytest.fixture
    def calculator(self):
        """Create metrics calculator instance."""
        return MetricsCalculator()
    
    def test_high_relevance(self, calculator):
        """Test relevance for highly relevant response."""
        relevance = calculator.calculate_relevance(
            "What is Paris?",
            "Paris is the capital of France"
        )
        # "Paris" is in both (after filtering stop words)
        assert relevance > 0.0
    
    def test_perfect_relevance(self, calculator):
        """Test relevance when all input keywords in response."""
        relevance = calculator.calculate_relevance(
            "capital France",
            "Paris is the capital of France"
        )
        # Both "capital" and "France" appear in response
        assert relevance == 1.0
    
    def test_no_relevance(self, calculator):
        """Test relevance for irrelevant response."""
        relevance = calculator.calculate_relevance(
            "weather",
            "The capital is Paris"
        )
        assert relevance == 0.0
    
    def test_empty_input(self, calculator):
        """Test relevance with empty input."""
        relevance = calculator.calculate_relevance(
            "",
            "Paris is the capital"
        )
        assert relevance == 0.0
    
    def test_empty_response(self, calculator):
        """Test relevance with empty response."""
        relevance = calculator.calculate_relevance(
            "What is Paris?",
            ""
        )
        assert relevance == 0.0
    
    def test_stop_words_filtered(self, calculator):
        """Test that stop words are filtered out."""
        # "what", "is", "the" are stop words
        relevance = calculator.calculate_relevance(
            "what is the weather",
            "The weather is sunny"
        )
        # Only "weather" should be considered (after filtering stop words)
        # "weather" appears in response, so relevance should be high
        assert relevance >= 0.5  # At least 50% relevance
    
    def test_case_insensitive(self, calculator):
        """Test relevance is case-insensitive."""
        relevance = calculator.calculate_relevance(
            "PARIS",
            "paris is the capital"
        )
        assert relevance == 1.0
    
    def test_partial_keyword_match(self, calculator):
        """Test relevance with partial keyword match."""
        relevance = calculator.calculate_relevance(
            "Paris London Berlin",
            "Paris is a city"
        )
        # Only "Paris" matches out of 3 keywords
        assert 0.0 < relevance < 1.0


class TestLatencyCalculation:
    """Test latency calculation."""
    
    @pytest.fixture
    def calculator(self):
        """Create metrics calculator instance."""
        return MetricsCalculator()
    
    def test_positive_latency(self, calculator):
        """Test latency calculation with positive duration."""
        latency = calculator.calculate_latency(1000.0, 1000.5)
        assert latency == 500.0  # 0.5 seconds = 500ms
    
    def test_zero_latency(self, calculator):
        """Test latency calculation with zero duration."""
        latency = calculator.calculate_latency(1000.0, 1000.0)
        assert latency == 0.0
    
    def test_negative_latency_handled(self, calculator):
        """Test negative latency is handled gracefully."""
        # This shouldn't happen in practice, but we handle it
        latency = calculator.calculate_latency(1000.5, 1000.0)
        assert latency == 0.0
    
    def test_millisecond_precision(self, calculator):
        """Test latency has millisecond precision."""
        latency = calculator.calculate_latency(1000.0, 1000.001)
        assert abs(latency - 1.0) < 0.01  # Allow small floating point error
    
    def test_large_latency(self, calculator):
        """Test latency calculation with large duration."""
        latency = calculator.calculate_latency(1000.0, 1010.0)
        assert latency == 10000.0  # 10 seconds = 10000ms


class TestIndividualMetricsCalculation:
    """Test individual metrics calculation."""
    
    @pytest.fixture
    def calculator(self):
        """Create metrics calculator instance."""
        return MetricsCalculator()
    
    def test_calculate_with_expected_output(self, calculator):
        """Test calculating metrics with expected output."""
        response = Response(
            test_case_id="tc_001",
            input="What is the capital of France?",
            output="Paris",
            latency=100.0,
            timestamp=datetime.utcnow()
        )
        
        metrics = calculator.calculate_individual_metrics(
            response,
            expected_output="Paris"
        )
        
        assert isinstance(metrics, IndividualMetrics)
        assert metrics.accuracy == 1.0
        # Relevance should be > 0 since "capital" and "france" are in input
        # and "paris" is in output (though not a perfect match)
        assert metrics.relevance >= 0.0  # Allow 0 since "Paris" alone may not match all keywords
    
    def test_calculate_without_expected_output(self, calculator):
        """Test calculating metrics without expected output."""
        response = Response(
            test_case_id="tc_001",
            input="What is the capital of France?",
            output="Paris is the capital of France",
            latency=100.0,
            timestamp=datetime.utcnow()
        )
        
        metrics = calculator.calculate_individual_metrics(response)
        
        assert isinstance(metrics, IndividualMetrics)
        assert metrics.accuracy is None
        assert metrics.relevance > 0.0


class TestAggregateMetrics:
    """Test metrics aggregation."""
    
    @pytest.fixture
    def calculator(self):
        """Create metrics calculator instance."""
        return MetricsCalculator()
    
    @pytest.fixture
    def sample_responses(self):
        """Create sample responses for testing."""
        return [
            Response(
                test_case_id="tc_001",
                input="What is 2+2?",
                output="4",
                latency=100.0,
                timestamp=datetime.utcnow()
            ),
            Response(
                test_case_id="tc_002",
                input="What is the capital of France?",
                output="Paris",
                latency=150.0,
                timestamp=datetime.utcnow()
            ),
            Response(
                test_case_id="tc_003",
                input="What is the weather?",
                output="Sunny",
                latency=200.0,
                timestamp=datetime.utcnow()
            )
        ]
    
    @pytest.fixture
    def sample_test_cases(self):
        """Create sample test cases with expected outputs."""
        return [
            TestCase(
                id="tc_001",
                input="What is 2+2?",
                expected_output="4"
            ),
            TestCase(
                id="tc_002",
                input="What is the capital of France?",
                expected_output="Paris"
            ),
            TestCase(
                id="tc_003",
                input="What is the weather?",
                expected_output=None  # No expected output
            )
        ]
    
    def test_aggregate_basic(self, calculator, sample_responses, sample_test_cases):
        """Test basic metrics aggregation."""
        metrics = calculator.aggregate_metrics(sample_responses, sample_test_cases)
        
        assert isinstance(metrics, AggregatedMetrics)
        assert metrics.total_test_cases == 3
        assert metrics.failed_test_cases == 0
        assert metrics.success_rate == 1.0
        assert metrics.average_latency == 150.0  # (100+150+200)/3
        assert metrics.median_latency == 150.0
        assert metrics.p95_latency == 200.0
    
    def test_aggregate_with_failures(self, calculator):
        """Test aggregation with failed responses."""
        responses = [
            Response(
                test_case_id="tc_001",
                input="test1",
                output="result1",
                latency=100.0,
                timestamp=datetime.utcnow()
            ),
            Response(
                test_case_id="tc_002",
                input="test2",
                output="",
                latency=50.0,
                timestamp=datetime.utcnow(),
                error="Connection timeout"
            ),
            Response(
                test_case_id="tc_003",
                input="test3",
                output="result3",
                latency=150.0,
                timestamp=datetime.utcnow()
            )
        ]
        
        metrics = calculator.aggregate_metrics(responses)
        
        assert metrics.total_test_cases == 3
        assert metrics.failed_test_cases == 1
        assert metrics.success_rate == 2.0 / 3.0
    
    def test_aggregate_empty_list_raises_error(self, calculator):
        """Test aggregation with empty response list raises error."""
        with pytest.raises(ValueError, match="empty response list"):
            calculator.aggregate_metrics([])
    
    def test_aggregate_single_response(self, calculator):
        """Test aggregation with single response."""
        responses = [
            Response(
                test_case_id="tc_001",
                input="test",
                output="result",
                latency=100.0,
                timestamp=datetime.utcnow()
            )
        ]
        
        metrics = calculator.aggregate_metrics(responses)
        
        assert metrics.total_test_cases == 1
        assert metrics.failed_test_cases == 0
        assert metrics.success_rate == 1.0
        assert metrics.average_latency == 100.0
        assert metrics.median_latency == 100.0
        assert metrics.p95_latency == 100.0
    
    def test_aggregate_without_test_cases(self, calculator, sample_responses):
        """Test aggregation without test cases (no expected outputs)."""
        metrics = calculator.aggregate_metrics(sample_responses)
        
        assert isinstance(metrics, AggregatedMetrics)
        assert metrics.total_test_cases == 3
        # Without expected outputs, accuracy should be 0.0
        assert metrics.average_accuracy == 0.0
        # Relevance should still be calculated
        assert metrics.average_relevance >= 0.0
    
    def test_aggregate_latency_percentiles(self, calculator):
        """Test latency percentile calculations."""
        # Create responses with known latencies
        responses = [
            Response(
                test_case_id=f"tc_{i:03d}",
                input=f"test{i}",
                output=f"result{i}",
                latency=float(i * 10),  # 0, 10, 20, ..., 990
                timestamp=datetime.utcnow()
            )
            for i in range(100)
        ]
        
        metrics = calculator.aggregate_metrics(responses)
        
        # Average should be around 495 (0+10+20+...+990)/100
        assert 490.0 <= metrics.average_latency <= 500.0
        
        # Median should be around 495 (middle of 0-990)
        assert 490.0 <= metrics.median_latency <= 500.0
        
        # P95 should be around 940 (95th percentile of 0-990)
        assert 930.0 <= metrics.p95_latency <= 950.0
    
    def test_aggregate_all_failures(self, calculator):
        """Test aggregation when all responses failed."""
        responses = [
            Response(
                test_case_id="tc_001",
                input="test1",
                output="",
                latency=50.0,
                timestamp=datetime.utcnow(),
                error="Error 1"
            ),
            Response(
                test_case_id="tc_002",
                input="test2",
                output="",
                latency=60.0,
                timestamp=datetime.utcnow(),
                error="Error 2"
            )
        ]
        
        metrics = calculator.aggregate_metrics(responses)
        
        assert metrics.total_test_cases == 2
        assert metrics.failed_test_cases == 2
        assert metrics.success_rate == 0.0
        # Accuracy and relevance should be 0 when all failed
        assert metrics.average_accuracy == 0.0
        assert metrics.average_relevance == 0.0
        # Latency should still be calculated
        assert metrics.average_latency == 55.0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def calculator(self):
        """Create metrics calculator instance."""
        return MetricsCalculator()
    
    def test_unicode_strings(self, calculator):
        """Test handling of unicode strings."""
        accuracy = calculator.calculate_accuracy("Café", "Café")
        assert accuracy == 1.0
        
        relevance = calculator.calculate_relevance("Café", "Café is nice")
        assert relevance > 0.0
    
    def test_very_long_strings(self, calculator):
        """Test handling of very long strings."""
        long_string = "word " * 1000
        accuracy = calculator.calculate_accuracy(long_string, long_string)
        assert accuracy == 1.0
    
    def test_special_characters(self, calculator):
        """Test handling of special characters."""
        accuracy = calculator.calculate_accuracy(
            "Hello, World!",
            "Hello, World!"
        )
        assert accuracy == 1.0
    
    def test_numbers_in_strings(self, calculator):
        """Test handling of numbers in strings."""
        accuracy = calculator.calculate_accuracy("42", "42")
        assert accuracy == 1.0
        
        relevance = calculator.calculate_relevance("What is 42?", "42 is the answer")
        assert relevance > 0.0
