"""Required CRUD functions and a command-line interface for PostgreSQL."""

import argparse
from datetime import date
import os
import sys

import psycopg
from psycopg.rows import dict_row


def _connect():
    """Read DATABASE_URL or standard PG* variables; never embed credentials."""
    return psycopg.connect(
        os.environ.get("DATABASE_URL", ""),
        row_factory=dict_row,
        connect_timeout=5,
    )


def getAllStudents():
    """Retrieve, display, and return every student in primary-key order."""
    with _connect() as connection:
        rows = connection.execute(
            "SELECT student_id, first_name, last_name, email, enrollment_date "
            "FROM students ORDER BY student_id"
        ).fetchall()
    if not rows:
        print("No students found.")
    for row in rows:
        # Display every field, including nullable enrollment dates.
        print(" | ".join(str(value) if value is not None else "NULL"
                         for value in row.values()))
    print(f"Total students: {len(rows)}")
    return rows


def addStudent(first_name, last_name, email, enrollment_date):
    """Insert one student and return the generated ID after the commit."""
    if isinstance(enrollment_date, str):
        enrollment_date = date.fromisoformat(enrollment_date)
    # Bound parameters keep names and email addresses separate from SQL code.
    with _connect() as connection:
        row = connection.execute(
            "INSERT INTO students (first_name, last_name, email, enrollment_date) "
            "VALUES (%s, %s, %s, %s) RETURNING student_id",
            (first_name, last_name, email, enrollment_date),
        ).fetchone()
    # The connection context commits on success and rolls back on exceptions.
    return row["student_id"]


def updateStudentEmail(student_id, new_email):
    """Update a student's email; return False if the ID does not exist."""
    with _connect() as connection:
        row = connection.execute(
            "UPDATE students SET email = %s WHERE student_id = %s "
            "RETURNING student_id", (new_email, student_id),
        ).fetchone()
    return row is not None


def deleteStudent(student_id):
    """Delete the specified student; return False if the ID does not exist."""
    with _connect() as connection:
        row = connection.execute(
            "DELETE FROM students WHERE student_id = %s RETURNING student_id",
            (student_id,),
        ).fetchone()
    return row is not None


def _positive_id(value):
    """Reject nonpositive IDs at the command-line boundary."""
    try:
        result = int(value)
        if result > 0:
            return result
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("student_id must be a positive integer")


def _date(value):
    """Convert a command-line date into a PostgreSQL-compatible Python date."""
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("use a valid date in YYYY-MM-DD format") from error


def main(argv=None):
    """Dispatch one CRUD command and return a useful process exit status."""
    parser = argparse.ArgumentParser(description="Manage PostgreSQL students.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Display all students")
    add = commands.add_parser("add", help="Insert a student")
    add.add_argument("first_name")
    add.add_argument("last_name")
    add.add_argument("email")
    add.add_argument("--enrollment-date", type=_date, default=None)
    update = commands.add_parser("update-email", help="Update a student's email")
    update.add_argument("student_id", type=_positive_id)
    update.add_argument("new_email")
    delete = commands.add_parser("delete", help="Delete a student")
    delete.add_argument("student_id", type=_positive_id)
    args = parser.parse_args(argv)

    try:
        if args.command == "list":
            getAllStudents()
        elif args.command == "add":
            student_id = addStudent(args.first_name, args.last_name, args.email,
                                    args.enrollment_date)
            print(f"Added student with student_id={student_id}.")
        elif args.command == "update-email":
            if not updateStudentEmail(args.student_id, args.new_email):
                print(f"Student {args.student_id} not found.", file=sys.stderr)
                return 1
            print(f"Updated email for student {args.student_id}.")
        elif args.command == "delete":
            if not deleteStudent(args.student_id):
                print(f"Student {args.student_id} not found.", file=sys.stderr)
                return 1
            print(f"Deleted student {args.student_id}.")
    except psycopg.errors.UniqueViolation:
        print("Email already exists. No changes were committed.", file=sys.stderr)
        return 1
    except psycopg.errors.NotNullViolation:
        print("First name, last name, and email cannot be NULL.", file=sys.stderr)
        return 1
    except psycopg.OperationalError:
        print("Cannot connect to PostgreSQL. Check that the server is running "
              "and that your connection settings are correct.", file=sys.stderr)
        return 1
    except psycopg.Error as error:
        # SQLSTATE helps diagnose errors without printing passwords or a DSN.
        print(f"Database operation failed (SQLSTATE {error.sqlstate or 'unknown'}). "
              "Check the database setup and input.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
