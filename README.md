# PostgreSQL Student CRUD Application

A Python command-line application implementing the assignment's four required
functions against a real PostgreSQL `students` table. This delivery is a ZIP
archive with a written demonstration script, as requested.

## 1. Create the database in pgAdmin

1. Open pgAdmin and connect to your PostgreSQL server. For a local server,
   the usual host is `localhost`, port `5432`, and login `postgres`. Use the
   password you chose during PostgreSQL installation.
2. Select the existing `postgres` database and open **Tools > Query Tool**.
   Make sure Auto-commit is enabled. Open and run
   `database/01_create_database.sql`. Execute `CREATE DATABASE` by itself;
   it cannot run inside a transaction.
3. Refresh the server's **Databases** node. Select `student_management` and
   open a **new Query Tool connected to that database**.
4. Open and run `database/02_schema_and_seed.sql` once. It creates the table
   and inserts John Doe, Jane Smith, and Jim Beam in one transaction.
5. Run the first SELECT in `database/03_verify.sql`. Expect three students
   with IDs 1, 2, and 3 in a fresh database. Run the other queries to inspect
   types, nullability, identity generation, and constraints.

The table uses an integer identity primary key, required text names, a required
unique text email, and a nullable date. Setup scripts deliberately do not drop
or overwrite existing data. If the database or table already exists, use it
as-is or choose a new database name and point the application at that database.
Do not rerun the seed script after each command. If a failed script leaves the
Query Tool in an aborted transaction, run `ROLLBACK;` before correcting the issue.

Alternatively, with `psql` installed, run these from the project folder (enter
your server password if prompted):

```sh
psql -h localhost -U postgres -d postgres -f database/01_create_database.sql
psql -h localhost -U postgres -d student_management -v ON_ERROR_STOP=1 -f database/02_schema_and_seed.sql
```

## 2. Create a Python environment and install the dependency

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Use `.venv\Scripts\python.exe` wherever the following examples say `python`;
this works without changing PowerShell's execution policy.

## 3. Configure the connection

Set these variables in the **same terminal** you use to launch the application.
Replace `YOUR_POSTGRES_PASSWORD` with your local PostgreSQL password. These
settings must match the server and database open in pgAdmin.

Windows PowerShell:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "student_management"
$env:PGUSER = "postgres"
$env:PGPASSWORD = "pass123"
```

The program also accepts a `DATABASE_URL` connection string, if set. Values
in that string take precedence over the equivalent PG variables. Clear an
unintended `DATABASE_URL` if the application connects to the wrong database.
For longer-term use, PostgreSQL's password file (`.pgpass`/`pgpass.conf`) avoids
keeping a password in the command environment. No `.env` file is loaded.
Do not include real credentials in your submitted files or recording.

## 4. Run each required function

Run all commands from the extracted project folder. On Windows, substitute the
virtual environment's Python executable as described above.

### Read: getAllStudents()

```sh
python -m app.students list
```

Displays every field of every row, sorted by ID, followed by a count.

### Create: addStudent(first_name, last_name, email, enrollment_date)

```sh
python -m app.students add Alice Brown alice.brown@example.com --enrollment-date 2023-09-03
```

The application prints the newly generated `student_id`. In a fresh database
it is 4, but **use the actual returned ID** for subsequent commands. Sequences
can have gaps, including after an unsuccessful insertion. Omitting
`--enrollment-date` stores SQL NULL, as allowed by the assignment.

### Update: updateStudentEmail(student_id, new_email)

```sh
python -m app.students update-email 4 alice.updated@example.com
```

Replace `4` if the insertion returned a different ID.

### Delete: deleteStudent(student_id)

```sh
python -m app.students delete 4
python -m app.students list
```

Expected progression: three seed rows; four after insertion; Alice's new email
after update; three seed rows again after deletion. Each command opens and
closes a connection. Successful operations commit; exceptions roll back.

## Function behavior and error handling

| Function | Result |
| --- | --- |
| `getAllStudents()` | Prints rows and returns a list of dictionaries |
| `addStudent(...)` | Returns the integer ID of the committed new record |
| `updateStudentEmail(...)` | Returns `True` when updated, `False` if absent |
| `deleteStudent(...)` | Returns `True` when deleted, `False` if absent |
