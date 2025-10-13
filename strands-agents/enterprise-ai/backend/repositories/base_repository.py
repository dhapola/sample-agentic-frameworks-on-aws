"""
Base repository class for database operations.
"""

from typing import Any, Dict, List, Optional, TypeVar, Generic, Type

from utils.database import DatabaseManager
from utils.utility import Utility

T = TypeVar('T')



class BaseRepository(Generic[T]):
    """
    Base repository class that provides common database operations.
    """
    
    def __init__(self, table_name: str):
        """
        Initialize the repository with a table name.
        
        Args:
            table_name: Name of the database table
        """
        self.table_name = table_name
        self.db = DatabaseManager()
        self.util = Utility()
    
    def find_all(self) -> List[Dict[str, Any]]:
        """
        Find all records in the table.
        
        Returns:
            List of dictionaries representing all records
        """
        query = f"SELECT * FROM {self.table_name}"
        return self.db.execute_query(query)
    
    def find_by_id(self, id_value: Any) -> Optional[Dict[str, Any]]:
        """
        Find a record by its ID.
        
        Args:
            id_value: ID value to search for
            
        Returns:
            Dictionary representing the record, or None if not found
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = :id"
        params = {"id": id_value}
        results = self.db.execute_query(query, params)
        return results[0] if results else None
    
    def find_by_field(self, field: str, value: Any) -> List[Dict[str, Any]]:
        """
        Find records by a specific field value.
        
        Args:
            field: Field name to search on
            value: Value to search for
            
        Returns:
            List of dictionaries representing matching records
        """
        query = f"SELECT * FROM {self.table_name} WHERE {field} = :value"
        params = {"value": value}
        return self.db.execute_query(query, params)
    
    def create(self, data: Dict[str, Any]) -> int:
        """
        Create a new record.
        
        Args:
            data: Dictionary of field values
            
        Returns:
            ID of the created record
        """
        fields = list(data.keys())
        placeholders = [f":{field}" for field in fields]
        
        fields_str = ", ".join(fields)
        placeholders_str = ", ".join(placeholders)
        
        query = f"INSERT INTO {self.table_name} ({fields_str}) VALUES ({placeholders_str}) RETURNING id"
        results = self.db.execute_query(query, data)
        return results[0]["id"] if results else None
    
    def update(self, id_value: Any, data: Dict[str, Any]) -> bool:
        """
        Update a record by its ID.
        
        Args:
            id_value: ID of the record to update
            data: Dictionary of field values to update
            
        Returns:
            True if update was successful
        """
        if not data:
            return False
            
        set_clauses = [f"{field} = :{field}" for field in data.keys()]
        set_clause_str = ", ".join(set_clauses)
        
        query = f"UPDATE {self.table_name} SET {set_clause_str} WHERE id = :id"
        params = {**data, "id": id_value}
        
        rowcount = self.db.execute_write(query, params)
        return rowcount > 0
    
    def delete(self, id_value: Any) -> bool:
        """
        Delete a record by its ID.
        
        Args:
            id_value: ID of the record to delete
            
        Returns:
            True if deletion was successful
        """
        query = f"DELETE FROM {self.table_name} WHERE id = :id"
        params = {"id": id_value}
        
        rowcount = self.db.execute_write(query, params)
        return rowcount > 0
    
    def count(self) -> int:
        """
        Count the number of records in the table.
        
        Returns:
            Number of records
        """
        query = f"SELECT COUNT(*) as count FROM {self.table_name}"
        results = self.db.execute_query(query)
        return results[0]["count"] if results else 0
    
    def execute_custom_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom query.
        
        Args:
            query: SQL query string
            params: Parameters for the query
            
        Returns:
            List of dictionaries representing the query results
        """
        return self.db.execute_query(query, params)
    
    def execute_custom_write(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        Execute a custom write operation.
        
        Args:
            query: SQL query string
            params: Parameters for the query
            
        Returns:
            Number of affected rows
        """
        return self.db.execute_write(query, params)
