"""CSV file parsing utilities for dataset uploads."""

import csv
import io
import uuid
from typing import List

from app.models.test_case import TestCase
from app.middleware.error_handler import ValidationError


def parse_csv_to_test_cases(file_content: bytes) -> List[TestCase]:
    """
    Parse CSV file content into a list of TestCase objects.
    
    Expected CSV format:
    - Header row: input,expected_output,metadata (optional)
    - Data rows: test case data
    
    Args:
        file_content: Raw bytes of the CSV file
        
    Returns:
        List of TestCase objects
        
    Raises:
        ValidationError: If CSV format is invalid
    """
    try:
        # Decode bytes to string
        content = file_content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(content))
        
        # Validate headers
        if not csv_reader.fieldnames:
            raise ValidationError("CSV file is empty or has no headers")
        
        required_fields = {'input'}
        headers = set(csv_reader.fieldnames)
        
        if not required_fields.issubset(headers):
            raise ValidationError(
                f"CSV must contain 'input' column. Found columns: {', '.join(headers)}"
            )
        
        # Parse rows into test cases
        test_cases = []
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            # Skip empty rows
            if not any(row.values()):
                continue
            
            # Validate input is not empty
            input_text = row.get('input', '').strip()
            if not input_text:
                raise ValidationError(f"Row {row_num}: 'input' field cannot be empty")
            
            # Get expected output (optional)
            expected_output = row.get('expected_output', '').strip() or None
            
            # Parse metadata (optional, can be JSON-like or simple key-value)
            metadata = {}
            for key, value in row.items():
                if key not in ['input', 'expected_output'] and value:
                    metadata[key] = value
            
            # Create test case
            test_case = TestCase(
                id=f"tc_{uuid.uuid4().hex[:12]}",
                input=input_text,
                expected_output=expected_output,
                metadata=metadata if metadata else None
            )
            test_cases.append(test_case)
        
        if not test_cases:
            raise ValidationError("CSV file contains no valid test cases")
        
        return test_cases
        
    except UnicodeDecodeError:
        raise ValidationError("File must be a valid UTF-8 encoded CSV file")
    except csv.Error as e:
        raise ValidationError(f"Invalid CSV format: {str(e)}")
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Error parsing CSV file: {str(e)}")


def validate_csv_file(filename: str, file_size: int, max_size_mb: int = 10) -> None:
    """
    Validate CSV file before processing.
    
    Args:
        filename: Name of the uploaded file
        file_size: Size of the file in bytes
        max_size_mb: Maximum allowed file size in MB
        
    Raises:
        ValidationError: If file is invalid
    """
    # Check file extension
    if not filename.lower().endswith('.csv'):
        raise ValidationError("File must be a CSV file (.csv extension)")
    
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise ValidationError(f"File size exceeds maximum allowed size of {max_size_mb}MB")
    
    if file_size == 0:
        raise ValidationError("File is empty")
