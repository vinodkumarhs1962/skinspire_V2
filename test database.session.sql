-- First, create a temporary test table that mirrors the structure of your users table
CREATE TEMP TABLE test_users AS 
SELECT * FROM users WHERE 1=0;

-- If your users table has triggers, add the same triggers to the test table
CREATE TRIGGER hash_password_trigger
BEFORE INSERT OR UPDATE ON test_users
FOR EACH ROW
EXECUTE FUNCTION hash_password();

-- Insert a test user
INSERT INTO test_users (
  user_id, 
  hospital_id, 
  entity_type, 
  entity_id, 
  password_hash, 
  is_active
) VALUES (
  'test_trigger_user', 
  (SELECT hospital_id FROM hospitals LIMIT 1), 
  'staff', 
  uuid_generate_v4(), 
  'plain_password', 
  true
);

-- Check if the password was hashed
SELECT 
  user_id, 
  password_hash, 
  password_hash LIKE '$2%' AS is_hashed,
  password_hash = 'plain_password' AS is_plaintext
FROM test_users
WHERE user_id = 'test_trigger_user';

-- Clean up
DROP TABLE test_users;