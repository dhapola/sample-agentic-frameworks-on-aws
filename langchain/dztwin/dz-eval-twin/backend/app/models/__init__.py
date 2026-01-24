"""Data models for the Gen AI Evaluation Platform.

This module contains all Pydantic models used throughout the platform,
including models for multi-tenant customer management, application profiles,
datasets, test cases, evaluation runs, and metrics.
"""

from .application_profile import ApplicationProfile, ApplicationType
from .connection_config import ConnectionConfig
from .customer import Customer
from .dataset import Dataset
from .evaluation_run import EvaluationRun, EvaluationStatus
from .metrics import AggregatedMetrics, IndividualMetrics
from .response import Response
from .test_case import TestCase

__all__ = [
    # Customer and tenant isolation
    "Customer",
    # Application configuration
    "ApplicationProfile",
    "ApplicationType",
    "ConnectionConfig",
    # Dataset and test cases
    "Dataset",
    "TestCase",
    # Evaluation execution
    "EvaluationRun",
    "EvaluationStatus",
    "Response",
    # Metrics
    "IndividualMetrics",
    "AggregatedMetrics",
]
