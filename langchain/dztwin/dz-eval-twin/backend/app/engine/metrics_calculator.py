"""Metrics calculator for evaluation results.

This module implements the MetricsCalculator class that calculates
individual and aggregated metrics for evaluation runs.
"""

import logging
import statistics
from typing import List, Optional

from app.models.metrics import AggregatedMetrics, IndividualMetrics
from app.models.response import Response
from app.models.test_case import TestCase

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculator for evaluation metrics.
    
    The metrics calculator provides methods to:
    - Calculate accuracy by comparing responses to expected outputs
    - Calculate relevance using keyword matching
    - Calculate latency from timestamps
    - Aggregate metrics across all responses in a run
    
    All metrics are normalized to a 0-1 scale where applicable.
    """
    
    def calculate_accuracy(
        self,
        response: str,
        expected_output: Optional[str]
    ) -> Optional[float]:
        """
        Calculate accuracy score comparing response to expected output.
        
        Uses simple string comparison with normalization:
        - Exact match (case-insensitive, whitespace-normalized): 1.0
        - Partial match: Ratio of matching words
        - No match: 0.0
        
        If no expected output is provided, returns None.
        
        Args:
            response: The actual response from the application
            expected_output: The expected output to compare against
        
        Returns:
            Accuracy score between 0.0 and 1.0, or None if no expected output
        
        Examples:
            >>> calc = MetricsCalculator()
            >>> calc.calculate_accuracy("Paris", "Paris")
            1.0
            >>> calc.calculate_accuracy("paris", "Paris")
            1.0
            >>> calc.calculate_accuracy("The capital is Paris", "Paris")
            0.25
            >>> calc.calculate_accuracy("London", "Paris")
            0.0
            >>> calc.calculate_accuracy("Paris", None)
            None
        """
        if expected_output is None:
            return None
        
        # Normalize strings: lowercase and strip whitespace
        response_normalized = response.lower().strip()
        expected_normalized = expected_output.lower().strip()
        
        # Exact match
        if response_normalized == expected_normalized:
            return 1.0
        
        # If either is empty, no match
        if not response_normalized or not expected_normalized:
            return 0.0
        
        # Partial match: calculate word overlap
        response_words = set(response_normalized.split())
        expected_words = set(expected_normalized.split())
        
        if not expected_words:
            return 0.0
        
        # Calculate Jaccard similarity (intersection over union)
        intersection = response_words & expected_words
        union = response_words | expected_words
        
        if not union:
            return 0.0
        
        accuracy = len(intersection) / len(union)
        
        logger.debug(
            f"Calculated accuracy: {accuracy:.2f} "
            f"(response: '{response[:50]}...', expected: '{expected_output[:50]}...')"
        )
        
        return accuracy
    
    def calculate_relevance(self, input_text: str, response: str) -> float:
        """
        Calculate relevance score of response to input.
        
        Uses basic keyword matching to determine if the response
        is relevant to the input:
        - Calculates word overlap between input and response
        - Returns ratio of input words found in response
        
        Args:
            input_text: The input text sent to the application
            response: The response from the application
        
        Returns:
            Relevance score between 0.0 and 1.0
        
        Examples:
            >>> calc = MetricsCalculator()
            >>> calc.calculate_relevance("What is Paris?", "Paris is the capital of France")
            0.5
            >>> calc.calculate_relevance("capital France", "Paris is the capital of France")
            1.0
            >>> calc.calculate_relevance("weather", "The capital is Paris")
            0.0
        """
        # Normalize strings: lowercase and strip whitespace
        input_normalized = input_text.lower().strip()
        response_normalized = response.lower().strip()
        
        # If either is empty, return 0
        if not input_normalized or not response_normalized:
            return 0.0
        
        # Extract words (filter out common stop words for better relevance)
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can',
            'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
            'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over',
            'under', 'again', 'further', 'then', 'once'
        }
        
        # First try with stop words filtered and length > 1
        # Remove punctuation from words
        import re
        input_words_raw = [re.sub(r'[^\w\s]', '', word) for word in input_normalized.split()]
        input_words = set(
            word for word in input_words_raw
            if word and word not in stop_words and len(word) > 1
        )
        
        # If no meaningful words after filtering, use all words (fallback)
        if not input_words:
            input_words = set(
                word for word in input_words_raw
                if word
            )
        
        response_words_raw = [re.sub(r'[^\w\s]', '', word) for word in response_normalized.split()]
        response_words = set(word for word in response_words_raw if word)
        
        # If no meaningful input words, return 0
        if not input_words:
            return 0.0
        
        # Calculate how many input keywords appear in response
        matching_words = input_words & response_words
        relevance = len(matching_words) / len(input_words)
        
        logger.debug(
            f"Calculated relevance: {relevance:.2f} "
            f"(input: '{input_text[:50]}...', response: '{response[:50]}...')"
        )
        
        return relevance
    
    def calculate_latency(self, start_time: float, end_time: float) -> float:
        """
        Calculate latency in milliseconds.
        
        Args:
            start_time: Start timestamp (seconds since epoch)
            end_time: End timestamp (seconds since epoch)
        
        Returns:
            Latency in milliseconds
        
        Examples:
            >>> calc = MetricsCalculator()
            >>> calc.calculate_latency(1000.0, 1000.5)
            500.0
            >>> calc.calculate_latency(1000.0, 1000.0)
            0.0
        """
        latency_seconds = end_time - start_time
        latency_ms = latency_seconds * 1000.0
        
        # Ensure non-negative
        if latency_ms < 0:
            logger.warning(
                f"Negative latency calculated: {latency_ms}ms. "
                f"Setting to 0.0"
            )
            return 0.0
        
        return latency_ms
    
    def calculate_individual_metrics(
        self,
        response: Response,
        expected_output: Optional[str] = None
    ) -> IndividualMetrics:
        """
        Calculate individual metrics for a single response.
        
        Args:
            response: Response object containing input, output, and latency
            expected_output: Optional expected output for accuracy calculation
        
        Returns:
            IndividualMetrics with accuracy and relevance scores
        """
        accuracy = self.calculate_accuracy(response.output, expected_output)
        relevance = self.calculate_relevance(response.input, response.output)
        
        return IndividualMetrics(
            accuracy=accuracy,
            relevance=relevance
        )
    
    def aggregate_metrics(
        self,
        responses: List[Response],
        test_cases: Optional[List[TestCase]] = None
    ) -> AggregatedMetrics:
        """
        Aggregate metrics across all responses in an evaluation run.
        
        Calculates:
        - Average accuracy (only for responses with expected outputs)
        - Average relevance across all responses
        - Average, median, and P95 latency
        - Success rate (percentage of responses without errors)
        - Total and failed test case counts
        
        Args:
            responses: List of Response objects from the evaluation run
            test_cases: Optional list of TestCase objects for expected outputs
        
        Returns:
            AggregatedMetrics with run-level statistics
        
        Raises:
            ValueError: If responses list is empty
        """
        if not responses:
            raise ValueError("Cannot aggregate metrics for empty response list")
        
        # Create a mapping of test_case_id to expected_output if test_cases provided
        expected_outputs = {}
        if test_cases:
            expected_outputs = {
                tc.id: tc.expected_output
                for tc in test_cases
                if tc.expected_output is not None
            }
        
        # Calculate individual metrics for each response
        accuracy_scores = []
        relevance_scores = []
        latencies = []
        failed_count = 0
        
        for response in responses:
            # Count failures
            if response.error:
                failed_count += 1
            
            # Calculate metrics only for successful responses
            if not response.error:
                # Accuracy (only if expected output exists)
                expected = expected_outputs.get(response.test_case_id)
                accuracy = self.calculate_accuracy(response.output, expected)
                if accuracy is not None:
                    accuracy_scores.append(accuracy)
                
                # Relevance
                relevance = self.calculate_relevance(response.input, response.output)
                relevance_scores.append(relevance)
            
            # Latency (include all responses, even failed ones)
            latencies.append(response.latency)
        
        # Calculate aggregated metrics
        total_test_cases = len(responses)
        success_rate = (total_test_cases - failed_count) / total_test_cases
        
        # Average accuracy (only if we have accuracy scores)
        average_accuracy = (
            statistics.mean(accuracy_scores) if accuracy_scores else 0.0
        )
        
        # Average relevance (only if we have relevance scores)
        average_relevance = (
            statistics.mean(relevance_scores) if relevance_scores else 0.0
        )
        
        # Latency statistics
        average_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        
        # P95 latency (95th percentile)
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[min(p95_index, len(sorted_latencies) - 1)]
        
        logger.info(
            f"Aggregated metrics for {total_test_cases} responses: "
            f"accuracy={average_accuracy:.2f}, relevance={average_relevance:.2f}, "
            f"latency={average_latency:.2f}ms, success_rate={success_rate:.2f}"
        )
        
        return AggregatedMetrics(
            average_accuracy=average_accuracy,
            average_relevance=average_relevance,
            average_latency=average_latency,
            median_latency=median_latency,
            p95_latency=p95_latency,
            success_rate=success_rate,
            total_test_cases=total_test_cases,
            failed_test_cases=failed_count
        )
