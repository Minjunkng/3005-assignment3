-- Rerun in pgAdmin after each application command to observe committed changes.
SELECT student_id, first_name, last_name, email, enrollment_date
FROM students
ORDER BY student_id;

-- Inspect the types, nullable columns, and auto-increment configuration.
SELECT column_name, data_type, is_nullable, is_identity
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'students'
ORDER BY ordinal_position;

-- Inspect PRIMARY KEY and UNIQUE constraints.
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_schema = 'public' AND table_name = 'students'
ORDER BY constraint_type;
