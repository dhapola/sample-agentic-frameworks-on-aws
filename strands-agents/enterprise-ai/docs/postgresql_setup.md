## Instructions to Install and Configure PostgreSQL on Mac

1. Install PostgreSQL v17 on mac using brew

`brew install postgresql@17`

2. Install PostgreSQL Admin client app 

`brew install --cask pgadmin4`

3. Start database engine

`brew services restart postgresql@17`

4. Connect to the database engine using default user 'postgres'

```
createuser -s postgres
psql -h localhost -U postgres
ALTER USER postgres with encrypted password 'dbpwd@1234';
```


5. Create database owners and databases
```
    CREATE USER txuser WITH PASSWORD 'payapp@2025';
    CREATE DATABASE trans_db OWNER txuser;

    CREATE USER eaiuser WITH PASSWORD 'eaiuser@2025';
    CREATE DATABASE eaidb OWNER eaiuser;

```

Now you are all set to create data in the databases.
