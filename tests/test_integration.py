"""Real PostgreSQL tests isolated in a fresh schema; no public tables changed."""

from contextlib import redirect_stdout, redirect_stderr
from datetime import date
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app import students


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "set TEST_DATABASE_URL to run")
class StudentsIntegrationTests(unittest.TestCase):
    """Exercise real commits, constraints, rollback, and command dispatch."""

    def setUp(self):
        self.dsn = os.environ["TEST_DATABASE_URL"]
        self.schema = "test_students_" + uuid4().hex
        with psycopg.connect(self.dsn) as connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)
        # Each function still uses its own real connection and transaction.
        self.connection_patch = patch.object(students, "_connect", self.connect)
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)
        seed = Path(__file__).resolve().parents[1] / "database/02_schema_and_seed.sql"
        with self.connect() as connection:
            connection.execute(seed.read_text(encoding="utf-8"))

    def connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row,
                               options=f"-csearch_path={self.schema}")

    def drop_schema(self):
        with psycopg.connect(self.dsn) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))

    def rows(self):
        with redirect_stdout(io.StringIO()):
            return students.getAllStudents()

    def test_exact_seed_and_display(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rows = students.getAllStudents()
        self.assertEqual([(r["first_name"], r["last_name"], r["email"], r["enrollment_date"])
                          for r in rows], [
            ("John", "Doe", "john.doe@example.com", date(2023, 9, 1)),
            ("Jane", "Smith", "jane.smith@example.com", date(2023, 9, 1)),
            ("Jim", "Beam", "jim.beam@example.com", date(2023, 9, 2)),
        ])
        self.assertIn("Total students: 3", output.getvalue())
        self.assertIn("john.doe@example.com", output.getvalue())

    def test_crud_committed_across_connections(self):
        student_id = students.addStudent("Alice", "Brown", "alice@example.com", "2023-09-03")
        self.assertGreater(student_id, 3)
        self.assertEqual(len(self.rows()), 4)
        self.assertTrue(students.updateStudentEmail(student_id, "alice.new@example.com"))
        self.assertEqual(self.rows()[-1]["email"], "alice.new@example.com")
        self.assertTrue(students.deleteStudent(student_id))
        self.assertEqual(len(self.rows()), 3)

    def test_unique_and_failed_update_rollback(self):
        with self.assertRaises(psycopg.errors.UniqueViolation):
            students.addStudent("Duplicate", "Email", "john.doe@example.com", None)
        with self.assertRaises(psycopg.errors.UniqueViolation):
            students.updateStudentEmail(2, "john.doe@example.com")
        self.assertEqual(self.rows()[1]["email"], "jane.smith@example.com")
        self.assertEqual(len(self.rows()), 3)

    def test_not_null_constraints(self):
        for values in [(None, "Name", "one@example.com"),
                       ("Name", None, "two@example.com"), ("Name", "Name", None)]:
            with self.assertRaises(psycopg.errors.NotNullViolation):
                students.addStudent(*values, None)
        self.assertEqual(len(self.rows()), 3)

    def test_null_date_and_parameterized_text(self):
        name = "O'Brien'); DROP TABLE students; --"
        student_id = students.addStudent(name, "Test", "quoted@example.com", None)
        row = next(r for r in self.rows() if r["student_id"] == student_id)
        self.assertEqual(row["first_name"], name)
        self.assertIsNone(row["enrollment_date"])
        self.assertEqual(len(self.rows()), 4)

    def test_missing_ids(self):
        self.assertFalse(students.updateStudentEmail(999999, "missing@example.com"))
        self.assertFalse(students.deleteStudent(999999))

    def test_cli_operations_and_errors(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(students.main(["list"]), 0)
            self.assertEqual(students.main(["add", "CLI", "User", "cli@example.com",
                                            "--enrollment-date", "2023-09-03"]), 0)
            student_id = self.rows()[-1]["student_id"]
            self.assertEqual(students.main(["update-email", str(student_id), "cli.new@example.com"]), 0)
            self.assertEqual(students.main(["delete", str(student_id)]), 0)
            self.assertEqual(students.main(["delete", str(student_id)]), 1)
            self.assertEqual(students.main(["add", "John", "Doe", "john.doe@example.com"]), 1)
            for args in [["delete", "0"], ["delete", "abc"],
                         ["add", "A", "B", "a@example.com", "--enrollment-date", "2023-02-30"]]:
                with self.assertRaises(SystemExit) as error:
                    students.main(args)
                self.assertEqual(error.exception.code, 2)

    def test_empty_table(self):
        for row in self.rows():
            students.deleteStudent(row["student_id"])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(students.getAllStudents(), [])
        self.assertIn("No students found.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
