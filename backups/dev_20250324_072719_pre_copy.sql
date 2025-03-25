--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.2

-- Started on 2025-03-24 07:27:19

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 8 (class 2615 OID 73771)
-- Name: application; Type: SCHEMA; Schema: -; Owner: skinspire_admin
--

CREATE SCHEMA application;


ALTER SCHEMA application OWNER TO skinspire_admin;

--
-- TOC entry 3 (class 3079 OID 57442)
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- TOC entry 4903 (class 0 OID 0)
-- Dependencies: 3
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- TOC entry 2 (class 3079 OID 73772)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 4904 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- TOC entry 279 (class 1255 OID 33248)
-- Name: create_audit_triggers(text); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.create_audit_triggers(schema_name text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN 
        SELECT table_name 
        FROM information_schema.tables
        WHERE table_schema = schema_name 
        AND table_type = 'BASE TABLE'
    LOOP
        PERFORM create_audit_triggers(schema_name, table_record.table_name);
    END LOOP;
END;
$$;


ALTER FUNCTION public.create_audit_triggers(schema_name text) OWNER TO skinspire_admin;

--
-- TOC entry 282 (class 1255 OID 57479)
-- Name: create_audit_triggers(text, text); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.create_audit_triggers(target_schema text, target_table text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    has_updated_at BOOLEAN;
    has_created_at BOOLEAN;
    has_updated_by BOOLEAN;
    has_created_by BOOLEAN;
BEGIN
    SELECT 
        EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = target_schema AND table_name = target_table AND column_name = 'updated_at') AS has_updated_at,
        EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = target_schema AND table_name = target_table AND column_name = 'created_at') AS has_created_at,
        EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = target_schema AND table_name = target_table AND column_name = 'updated_by') AS has_updated_by,
        EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = target_schema AND table_name = target_table AND column_name = 'created_by') AS has_created_by
    INTO 
        has_updated_at, has_created_at, has_updated_by, has_created_by;
    
    IF has_updated_at THEN
        EXECUTE format('DROP TRIGGER IF EXISTS update_timestamp ON %I.%I', 
                      target_schema, target_table);
        EXECUTE format('CREATE TRIGGER update_timestamp BEFORE UPDATE ON %I.%I 
                      FOR EACH ROW EXECUTE FUNCTION update_timestamp()', 
                      target_schema, target_table);
    END IF;
    
    IF has_updated_by OR has_created_by THEN
        EXECUTE format('DROP TRIGGER IF EXISTS track_user_changes ON %I.%I', 
                      target_schema, target_table);
        EXECUTE format('CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON %I.%I 
                      FOR EACH ROW EXECUTE FUNCTION track_user_changes()', 
                      target_schema, target_table);
    END IF;
END;
$$;


ALTER FUNCTION public.create_audit_triggers(target_schema text, target_table text) OWNER TO skinspire_admin;

--
-- TOC entry 283 (class 1255 OID 57393)
-- Name: create_audit_triggers_all_schemas(); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.create_audit_triggers_all_schemas() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    schema_record RECORD;
BEGIN
    FOR schema_record IN 
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname NOT LIKE 'pg_%' 
          AND nspname != 'information_schema'
    LOOP
        PERFORM create_audit_triggers(schema_record.schema_name);
    END LOOP;
END;
$$;


ALTER FUNCTION public.create_audit_triggers_all_schemas() OWNER TO skinspire_admin;

--
-- TOC entry 278 (class 1255 OID 49196)
-- Name: drop_existing_triggers(text, text); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.drop_existing_triggers(schema_name text, table_name text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    trigger_rec RECORD;
BEGIN
    FOR trigger_rec IN 
        SELECT trigger_name 
        FROM information_schema.triggers
        WHERE trigger_schema = schema_name AND event_object_table = table_name
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I', 
                      trigger_rec.trigger_name, schema_name, table_name);
    END LOOP;
END;
$$;


ALTER FUNCTION public.drop_existing_triggers(schema_name text, table_name text) OWNER TO skinspire_admin;

--
-- TOC entry 284 (class 1255 OID 57480)
-- Name: hash_password(); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.hash_password() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
BEGIN
    DECLARE
        password_column TEXT := NULL;
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password_hash') THEN
            password_column := 'password_hash';
        ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password') THEN
            password_column := 'password';
        END IF;
        
        IF password_column IS NOT NULL THEN
            IF password_column = 'password_hash' THEN
                IF (TG_OP = 'INSERT' OR NEW.password_hash <> OLD.password_hash) AND 
                   NEW.password_hash IS NOT NULL AND 
                   NOT (NEW.password_hash LIKE '$2%' OR length(NEW.password_hash) > 50) THEN
                    BEGIN
                        NEW.password_hash = crypt(NEW.password_hash, gen_salt('bf', 10));
                    EXCEPTION WHEN undefined_function THEN
                        NEW.password_hash = '$2a$10$mock_hash_' || NEW.password_hash;
                    END;
                END IF;
            ELSIF password_column = 'password' THEN
                IF (TG_OP = 'INSERT' OR NEW.password <> OLD.password) AND 
                   NEW.password IS NOT NULL AND 
                   NOT (NEW.password LIKE '$2%' OR length(NEW.password) > 50) THEN
                    BEGIN
                        NEW.password = crypt(NEW.password, gen_salt('bf', 10));
                    EXCEPTION WHEN undefined_function THEN
                        NEW.password = '$2a$10$mock_hash_' || NEW.password;
                    END;
                END IF;
            END IF;
        END IF;
    END;
    
    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Error in hash_password trigger: %', SQLERRM;
    RETURN NEW;
END;
$_$;


ALTER FUNCTION public.hash_password() OWNER TO skinspire_admin;

--
-- TOC entry 281 (class 1255 OID 33247)
-- Name: track_user_changes(); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.track_user_changes() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
            AND column_name = 'created_by'
        ) THEN
            BEGIN
                NEW.created_by = current_setting('app.current_user', true);
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END;
        END IF;
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
        AND column_name = 'updated_by'
    ) THEN
        BEGIN
            NEW.updated_by = current_setting('app.current_user', true);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.track_user_changes() OWNER TO skinspire_admin;

--
-- TOC entry 221 (class 1255 OID 33246)
-- Name: update_timestamp(); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.update_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_timestamp() OWNER TO skinspire_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 220 (class 1259 OID 33295)
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO skinspire_admin;

--
-- TOC entry 4897 (class 0 OID 33295)
-- Dependencies: 220
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.alembic_version (version_num) FROM stdin;
\.


--
-- TOC entry 4751 (class 2606 OID 33299)
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


-- Completed on 2025-03-24 07:27:19

--
-- PostgreSQL database dump complete
--

