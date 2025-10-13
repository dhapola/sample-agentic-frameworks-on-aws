# Database Management Guide

## Overview

The sales data preparation system now includes comprehensive database management tools to handle existing data and ensure fresh starts for data generation.

## Key Features

### 🔄 Automatic Table Recreation
- **Problem Solved**: Previously, if tables existed, the system would append to existing data
- **Solution**: New recreation functionality drops and recreates tables for fresh starts

### 🧹 Data Cleanup Utilities
- **Interactive Cleanup**: User-friendly interface for data management
- **Status Monitoring**: View current database state and record counts
- **Safe Operations**: Confirmation prompts for destructive actions

### 🔌 Connection Testing
- **Pre-flight Checks**: Verify database connectivity before operations
- **Permission Validation**: Ensure user has required database permissions
- **Troubleshooting**: Clear error messages and resolution steps

## Usage Scenarios

### Scenario 1: Fresh Data Generation
```bash
# Recommended approach - handles everything automatically
./generate_all_data.sh
```

This will:
1. ✅ Test database connection
2. 🧹 Clean existing data (truncate tables)
3. 🏗️ Recreate tables with fresh schema
4. 📊 Generate all synthetic data

### Scenario 2: Manual Database Management
```bash
# Check current database status
python3 cleanup_database.py status

# Clean data but keep schema
python3 cleanup_database.py truncate

# Drop all tables and schema
python3 cleanup_database.py drop

# Recreate tables only
python3 create_tables.py recreate
```

### Scenario 3: Troubleshooting
```bash
# Test database connection
python3 test_connection.py

# Interactive cleanup with options
python3 cleanup_database.py
```

## Command Reference

### Database Connection Testing
```bash
python3 test_connection.py
```
- Tests PostgreSQL connection
- Verifies database permissions
- Shows database version and user info
- Provides troubleshooting guidance

### Table Management
```bash
# Drop and recreate all tables (recommended for fresh start)
python3 create_tables.py recreate

# Only create tables (if they don't exist)
python3 create_tables.py create

# Only drop existing tables
python3 create_tables.py drop
```

### Data Cleanup
```bash
# Interactive mode with menu options
python3 cleanup_database.py

# Show current database status
python3 cleanup_database.py status

# Remove data but keep table structure
python3 cleanup_database.py truncate

# Remove all tables and data
python3 cleanup_database.py drop

# Force truncate without confirmation (for scripts)
python3 cleanup_database.py force-truncate
```

## Safety Features

### 🛡️ Confirmation Prompts
- All destructive operations require user confirmation
- Clear warnings about data loss
- Option to cancel operations

### 🔍 Status Monitoring
- View current record counts before operations
- Identify which tables contain data
- Monitor total database size

### 🚫 Foreign Key Handling
- Proper order for table operations
- Temporary constraint disabling during cleanup
- Cascade operations for related data

## Integration with Data Generation

### Updated generate_all_data.sh
The master script now includes:
1. **Connection Testing**: Verifies database is accessible
2. **Automatic Cleanup**: Removes existing data without prompts
3. **Fresh Schema**: Recreates tables with latest structure
4. **Data Generation**: Proceeds with synthetic data creation

### Backward Compatibility
- Existing scripts continue to work
- New functionality is opt-in
- Default behavior ensures fresh starts

## Error Handling

### Connection Issues
```
❌ Database connection failed: connection refused
🔧 Troubleshooting:
   1. Check if PostgreSQL is running
   2. Verify .env file configuration
   3. Ensure database exists and user has access
```

### Permission Issues
```
⚠️ Limited permissions: permission denied for table
```
- Check user has CREATE/DROP privileges
- Verify database ownership
- Review PostgreSQL user permissions

### Data Conflicts
```
✅ Current record counts:
  📋 transactions: 601,000 records
⚠️ Are you sure you want to truncate all tables? (yes/no):
```
- Clear visibility of existing data
- Explicit confirmation required
- Safe cancellation options

## Best Practices

### 🎯 For Development
1. Always test connection first: `python3 test_connection.py`
2. Check database status: `python3 cleanup_database.py status`
3. Use recreation for fresh starts: `python3 create_tables.py recreate`

### 🎯 For Production
1. Backup data before cleanup operations
2. Use interactive mode for safety: `python3 cleanup_database.py`
3. Verify operations with status checks

### 🎯 For Automation
1. Use `force-truncate` for scripted cleanup
2. Include connection testing in pipelines
3. Monitor exit codes for error handling

## Migration from Previous Version

### If You Have Existing Data
1. **Check Status**: `python3 cleanup_database.py status`
2. **Backup** (if needed): Export important data
3. **Clean Start**: Run `./generate_all_data.sh`

### If You Have Custom Scripts
- Update to use new `create_tables.py recreate`
- Add connection testing with `test_connection.py`
- Consider using cleanup utilities for data management

## Troubleshooting Common Issues

### "Table already exists" Errors
**Solution**: Use `python3 create_tables.py recreate` instead of `create`

### Foreign Key Constraint Violations
**Solution**: Use proper cleanup order with `cleanup_database.py`

### Permission Denied Errors
**Solution**: Check database user permissions and ownership

### Connection Refused
**Solution**: Verify PostgreSQL is running and .env configuration

## Summary

The enhanced database management system provides:
- ✅ **Reliable Fresh Starts**: No more data conflicts
- ✅ **Safe Operations**: Confirmation prompts and status checks
- ✅ **Better Debugging**: Connection testing and clear error messages
- ✅ **Flexible Management**: Multiple cleanup and recreation options
- ✅ **Automated Workflows**: Seamless integration with data generation

This ensures consistent, reliable data generation for testing and development purposes.