--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.2

-- Started on 2025-03-24 07:30:00

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
-- TOC entry 7 (class 2615 OID 90462)
-- Name: public; Type: SCHEMA; Schema: -; Owner: skinspire_admin
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO skinspire_admin;

--
-- TOC entry 5033 (class 0 OID 0)
-- Dependencies: 7
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: skinspire_admin
--

COMMENT ON SCHEMA public IS '';


--
-- TOC entry 3 (class 3079 OID 90463)
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- TOC entry 5035 (class 0 OID 0)
-- Dependencies: 3
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- TOC entry 2 (class 3079 OID 90500)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 5036 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- TOC entry 291 (class 1255 OID 90511)
-- Name: cleanup_user_roles(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.cleanup_user_roles() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Remove all role mappings for this user
    DELETE FROM user_role_mapping
    WHERE user_id = OLD.user_id;
    
    RETURN OLD;
END;
$$;


ALTER FUNCTION public.cleanup_user_roles() OWNER TO postgres;

--
-- TOC entry 292 (class 1255 OID 90512)
-- Name: create_audit_triggers(text); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.create_audit_triggers(schema_name text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    table_rec RECORD;
    has_updated_at BOOLEAN;
    has_user_tracking BOOLEAN;
BEGIN
    -- Get all tables in the schema
    FOR table_rec IN 
        SELECT tablename AS table_name
        FROM pg_tables 
        WHERE schemaname = schema_name
    LOOP
        -- Check if table has updated_at column
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = schema_name 
              AND table_name = table_rec.table_name 
              AND column_name = 'updated_at'
        ) INTO has_updated_at;
        
        -- Check if table has user tracking columns
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = schema_name 
              AND table_name = table_rec.table_name 
              AND column_name = 'created_by'
        ) AND EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = schema_name 
              AND table_name = table_rec.table_name 
              AND column_name = 'updated_by'
        ) INTO has_user_tracking;
        
        -- First, safely remove any existing triggers
        PERFORM drop_existing_triggers(schema_name, table_rec.table_name);
        
        -- Create timestamp trigger if needed
        IF has_updated_at THEN
            BEGIN
                EXECUTE format(
                    'CREATE TRIGGER update_timestamp
                     BEFORE UPDATE ON %I.%I
                     FOR EACH ROW
                     EXECUTE FUNCTION update_timestamp()',
                    schema_name,
                    table_rec.table_name
                );
                RAISE NOTICE 'Created update_timestamp trigger on %.%', 
                    schema_name, table_rec.table_name;
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Failed to create update_timestamp trigger on %.%: %', 
                    schema_name, table_rec.table_name, SQLERRM;
            END;
        END IF;
        
        -- Create user tracking trigger if needed
        IF has_user_tracking THEN
            BEGIN
                EXECUTE format(
                    'CREATE TRIGGER track_user_changes
                     BEFORE INSERT OR UPDATE ON %I.%I
                     FOR EACH ROW
                     EXECUTE FUNCTION track_user_changes()',
                    schema_name,
                    table_rec.table_name
                );
                RAISE NOTICE 'Created track_user_changes trigger on %.%', 
                    schema_name, table_rec.table_name;
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Failed to create track_user_changes trigger on %.%: %', 
                    schema_name, table_rec.table_name, SQLERRM;
            END;
        END IF;
    END LOOP;
END;
$$;


ALTER FUNCTION public.create_audit_triggers(schema_name text) OWNER TO skinspire_admin;

--
-- TOC entry 293 (class 1255 OID 90513)
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
-- TOC entry 294 (class 1255 OID 90514)
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
-- TOC entry 295 (class 1255 OID 90515)
-- Name: drop_existing_triggers(text, text); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.drop_existing_triggers(schema_name text, table_name text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    trigger_rec RECORD;
BEGIN
    -- Find all triggers on this table and drop them one by one
    FOR trigger_rec IN
        SELECT trigger_name
        FROM information_schema.triggers
        WHERE event_object_schema = schema_name
          AND event_object_table = table_name
    LOOP
        BEGIN
            EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I',
                trigger_rec.trigger_name,
                schema_name,
                table_name
            );
            RAISE NOTICE 'Dropped trigger % on %.%', 
                trigger_rec.trigger_name, schema_name, table_name;
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Failed to drop trigger % on %.%: %', 
                trigger_rec.trigger_name, schema_name, table_name, SQLERRM;
        END;
    END LOOP;
END;
$$;


ALTER FUNCTION public.drop_existing_triggers(schema_name text, table_name text) OWNER TO skinspire_admin;

--
-- TOC entry 296 (class 1255 OID 90516)
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
-- TOC entry 297 (class 1255 OID 90517)
-- Name: hash_password_on_change(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.hash_password_on_change() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
BEGIN
    -- Only hash if password is provided in plain text
    IF NEW.password_hash IS NOT NULL AND 
       (TG_OP = 'INSERT' OR NEW.password_hash <> OLD.password_hash) AND
       NOT NEW.password_hash LIKE '$2b$%' THEN  -- Not already a bcrypt hash
        
        -- Hash the password using pgcrypto if available
        NEW.password_hash = crypt(NEW.password_hash, gen_salt('bf', 10));
    END IF;
    RETURN NEW;
END;
$_$;


ALTER FUNCTION public.hash_password_on_change() OWNER TO postgres;

--
-- TOC entry 298 (class 1255 OID 90518)
-- Name: track_user_changes(); Type: FUNCTION; Schema: public; Owner: skinspire_admin
--

CREATE FUNCTION public.track_user_changes() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    current_user_value text;
BEGIN
    -- Try different ways to get the current user ID
    BEGIN
        -- Try using the app.current_user setting first
        current_user_value := current_setting('app.current_user', TRUE);
    EXCEPTION WHEN OTHERS THEN
        BEGIN
            -- Fall back to application.app_user setting
            current_user_value := current_setting('application.app_user', TRUE);
        EXCEPTION WHEN OTHERS THEN
            BEGIN
                -- Fall back to session_user if no application variable is set
                current_user_value := session_user;
            EXCEPTION WHEN OTHERS THEN
                -- Finally, use a default value if all else fails
                current_user_value := 'system';
            END;
        END;
    END;

    -- For INSERT operations
    IF TG_OP = 'INSERT' THEN
        -- Check and set created_by if column exists
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
                  AND column_name = 'created_by') THEN
            NEW.created_by = current_user_value;
        END IF;
        
        -- Check and set updated_by if column exists
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
                  AND column_name = 'updated_by') THEN
            NEW.updated_by = current_user_value;
        END IF;
    
    -- For UPDATE operations
    ELSIF TG_OP = 'UPDATE' THEN
        -- Check and set updated_by if column exists
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
                  AND column_name = 'updated_by') THEN
            NEW.updated_by = current_user_value;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.track_user_changes() OWNER TO skinspire_admin;

--
-- TOC entry 299 (class 1255 OID 90519)
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
-- TOC entry 220 (class 1259 OID 90520)
-- Name: branches; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.branches (
    branch_id uuid NOT NULL,
    hospital_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    address jsonb,
    contact_details jsonb,
    settings jsonb,
    is_active boolean,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50),
    deleted_at timestamp with time zone,
    deleted_by character varying(50)
);


ALTER TABLE public.branches OWNER TO skinspire_admin;

--
-- TOC entry 221 (class 1259 OID 90525)
-- Name: hospitals; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.hospitals (
    hospital_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    license_no character varying(50),
    address jsonb,
    contact_details jsonb,
    settings jsonb,
    encryption_enabled boolean,
    encryption_key character varying(255),
    encryption_config jsonb,
    is_active boolean,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50),
    deleted_at timestamp with time zone,
    deleted_by character varying(50)
);


ALTER TABLE public.hospitals OWNER TO skinspire_admin;

--
-- TOC entry 222 (class 1259 OID 90530)
-- Name: login_history; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.login_history (
    history_id uuid NOT NULL,
    user_id character varying(15) NOT NULL,
    login_time timestamp with time zone NOT NULL,
    logout_time timestamp with time zone,
    ip_address character varying(45),
    user_agent character varying(255),
    status character varying(20),
    failure_reason character varying(100),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50)
);


ALTER TABLE public.login_history OWNER TO skinspire_admin;

--
-- TOC entry 223 (class 1259 OID 90535)
-- Name: module_master; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.module_master (
    module_id integer NOT NULL,
    module_name character varying(50) NOT NULL,
    description character varying(200),
    parent_module integer,
    sequence integer,
    icon character varying(50),
    route character varying(100),
    status character varying(20),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50)
);


ALTER TABLE public.module_master OWNER TO skinspire_admin;

--
-- TOC entry 224 (class 1259 OID 90540)
-- Name: module_master_module_id_seq; Type: SEQUENCE; Schema: public; Owner: skinspire_admin
--

CREATE SEQUENCE public.module_master_module_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.module_master_module_id_seq OWNER TO skinspire_admin;

--
-- TOC entry 5037 (class 0 OID 0)
-- Dependencies: 224
-- Name: module_master_module_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: skinspire_admin
--

ALTER SEQUENCE public.module_master_module_id_seq OWNED BY public.module_master.module_id;


--
-- TOC entry 225 (class 1259 OID 90541)
-- Name: parameter_settings; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.parameter_settings (
    param_code character varying(50) NOT NULL,
    param_value character varying(500),
    data_type character varying(20),
    module character varying(50),
    is_editable boolean,
    description text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50)
);


ALTER TABLE public.parameter_settings OWNER TO skinspire_admin;

--
-- TOC entry 226 (class 1259 OID 90546)
-- Name: patients; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.patients (
    patient_id uuid NOT NULL,
    hospital_id uuid NOT NULL,
    branch_id uuid,
    mrn character varying(20),
    title character varying(10),
    blood_group character varying(5),
    personal_info jsonb NOT NULL,
    contact_info jsonb NOT NULL,
    medical_info text,
    emergency_contact jsonb,
    documents jsonb,
    preferences jsonb,
    is_active boolean,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50),
    deleted_at timestamp with time zone,
    deleted_by character varying(50)
);


ALTER TABLE public.patients OWNER TO skinspire_admin;

--
-- TOC entry 227 (class 1259 OID 90551)
-- Name: role_master; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.role_master (
    role_id integer NOT NULL,
    hospital_id uuid,
    role_name character varying(50) NOT NULL,
    description character varying(200),
    is_system_role boolean,
    status character varying(20),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50)
);


ALTER TABLE public.role_master OWNER TO skinspire_admin;

--
-- TOC entry 228 (class 1259 OID 90554)
-- Name: role_master_role_id_seq; Type: SEQUENCE; Schema: public; Owner: skinspire_admin
--

CREATE SEQUENCE public.role_master_role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.role_master_role_id_seq OWNER TO skinspire_admin;

--
-- TOC entry 5038 (class 0 OID 0)
-- Dependencies: 228
-- Name: role_master_role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: skinspire_admin
--

ALTER SEQUENCE public.role_master_role_id_seq OWNED BY public.role_master.role_id;


--
-- TOC entry 229 (class 1259 OID 90555)
-- Name: role_module_access; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.role_module_access (
    role_id integer NOT NULL,
    module_id integer NOT NULL,
    can_view boolean,
    can_add boolean,
    can_edit boolean,
    can_delete boolean,
    can_export boolean,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50)
);


ALTER TABLE public.role_module_access OWNER TO skinspire_admin;

--
-- TOC entry 230 (class 1259 OID 90558)
-- Name: staff; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.staff (
    staff_id uuid NOT NULL,
    hospital_id uuid NOT NULL,
    branch_id uuid,
    employee_code character varying(20),
    title character varying(10),
    specialization character varying(100),
    personal_info jsonb NOT NULL,
    contact_info jsonb NOT NULL,
    professional_info jsonb,
    employment_info jsonb,
    documents jsonb,
    is_active boolean,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50),
    deleted_at timestamp with time zone,
    deleted_by character varying(50)
);


ALTER TABLE public.staff OWNER TO skinspire_admin;

--
-- TOC entry 231 (class 1259 OID 90563)
-- Name: user_role_mapping; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.user_role_mapping (
    user_id character varying(15) NOT NULL,
    role_id integer NOT NULL,
    is_active boolean,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50)
);


ALTER TABLE public.user_role_mapping OWNER TO skinspire_admin;

--
-- TOC entry 232 (class 1259 OID 90566)
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.user_sessions (
    session_id uuid NOT NULL,
    user_id character varying(15) NOT NULL,
    token character varying(500) NOT NULL,
    created_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    is_active boolean,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50)
);


ALTER TABLE public.user_sessions OWNER TO skinspire_admin;

--
-- TOC entry 233 (class 1259 OID 90571)
-- Name: users; Type: TABLE; Schema: public; Owner: skinspire_admin
--

CREATE TABLE public.users (
    user_id character varying(15) NOT NULL,
    hospital_id uuid,
    entity_type character varying(10) NOT NULL,
    entity_id uuid NOT NULL,
    password_hash character varying(255),
    failed_login_attempts integer,
    last_login timestamp with time zone,
    is_active boolean,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(50),
    updated_by character varying(50),
    deleted_at timestamp with time zone,
    deleted_by character varying(50)
);


ALTER TABLE public.users OWNER TO skinspire_admin;

--
-- TOC entry 4798 (class 2604 OID 90574)
-- Name: module_master module_id; Type: DEFAULT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.module_master ALTER COLUMN module_id SET DEFAULT nextval('public.module_master_module_id_seq'::regclass);


--
-- TOC entry 4799 (class 2604 OID 90575)
-- Name: role_master role_id; Type: DEFAULT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.role_master ALTER COLUMN role_id SET DEFAULT nextval('public.role_master_role_id_seq'::regclass);


--
-- TOC entry 5014 (class 0 OID 90520)
-- Dependencies: 220
-- Data for Name: branches; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.branches (branch_id, hospital_id, name, address, contact_details, settings, is_active, created_at, updated_at, created_by, updated_by, deleted_at, deleted_by) FROM stdin;
\.


--
-- TOC entry 5015 (class 0 OID 90525)
-- Dependencies: 221
-- Data for Name: hospitals; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.hospitals (hospital_id, name, license_no, address, contact_details, settings, encryption_enabled, encryption_key, encryption_config, is_active, created_at, updated_at, created_by, updated_by, deleted_at, deleted_by) FROM stdin;
\.


--
-- TOC entry 5016 (class 0 OID 90530)
-- Dependencies: 222
-- Data for Name: login_history; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.login_history (history_id, user_id, login_time, logout_time, ip_address, user_agent, status, failure_reason, created_at, updated_at, created_by, updated_by) FROM stdin;
\.


--
-- TOC entry 5017 (class 0 OID 90535)
-- Dependencies: 223
-- Data for Name: module_master; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.module_master (module_id, module_name, description, parent_module, sequence, icon, route, status, created_at, updated_at, created_by, updated_by) FROM stdin;
\.


--
-- TOC entry 5019 (class 0 OID 90541)
-- Dependencies: 225
-- Data for Name: parameter_settings; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.parameter_settings (param_code, param_value, data_type, module, is_editable, description, created_at, updated_at, created_by, updated_by) FROM stdin;
\.


--
-- TOC entry 5020 (class 0 OID 90546)
-- Dependencies: 226
-- Data for Name: patients; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.patients (patient_id, hospital_id, branch_id, mrn, title, blood_group, personal_info, contact_info, medical_info, emergency_contact, documents, preferences, is_active, created_at, updated_at, created_by, updated_by, deleted_at, deleted_by) FROM stdin;
\.


--
-- TOC entry 5021 (class 0 OID 90551)
-- Dependencies: 227
-- Data for Name: role_master; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.role_master (role_id, hospital_id, role_name, description, is_system_role, status, created_at, updated_at, created_by, updated_by) FROM stdin;
\.


--
-- TOC entry 5023 (class 0 OID 90555)
-- Dependencies: 229
-- Data for Name: role_module_access; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.role_module_access (role_id, module_id, can_view, can_add, can_edit, can_delete, can_export, created_at, updated_at, created_by, updated_by) FROM stdin;
\.


--
-- TOC entry 5024 (class 0 OID 90558)
-- Dependencies: 230
-- Data for Name: staff; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.staff (staff_id, hospital_id, branch_id, employee_code, title, specialization, personal_info, contact_info, professional_info, employment_info, documents, is_active, created_at, updated_at, created_by, updated_by, deleted_at, deleted_by) FROM stdin;
\.


--
-- TOC entry 5025 (class 0 OID 90563)
-- Dependencies: 231
-- Data for Name: user_role_mapping; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.user_role_mapping (user_id, role_id, is_active, created_at, updated_at, created_by, updated_by) FROM stdin;
\.


--
-- TOC entry 5026 (class 0 OID 90566)
-- Dependencies: 232
-- Data for Name: user_sessions; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.user_sessions (session_id, user_id, token, created_at, expires_at, is_active, updated_at, created_by, updated_by) FROM stdin;
\.


--
-- TOC entry 5027 (class 0 OID 90571)
-- Dependencies: 233
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: skinspire_admin
--

COPY public.users (user_id, hospital_id, entity_type, entity_id, password_hash, failed_login_attempts, last_login, is_active, created_at, updated_at, created_by, updated_by, deleted_at, deleted_by) FROM stdin;
\.


--
-- TOC entry 5039 (class 0 OID 0)
-- Dependencies: 224
-- Name: module_master_module_id_seq; Type: SEQUENCE SET; Schema: public; Owner: skinspire_admin
--

SELECT pg_catalog.setval('public.module_master_module_id_seq', 1, false);


--
-- TOC entry 5040 (class 0 OID 0)
-- Dependencies: 228
-- Name: role_master_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: skinspire_admin
--

SELECT pg_catalog.setval('public.role_master_role_id_seq', 1, false);


--
-- TOC entry 4801 (class 2606 OID 90577)
-- Name: branches branches_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_pkey PRIMARY KEY (branch_id);


--
-- TOC entry 4803 (class 2606 OID 90579)
-- Name: hospitals hospitals_license_no_key; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.hospitals
    ADD CONSTRAINT hospitals_license_no_key UNIQUE (license_no);


--
-- TOC entry 4805 (class 2606 OID 90581)
-- Name: hospitals hospitals_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.hospitals
    ADD CONSTRAINT hospitals_pkey PRIMARY KEY (hospital_id);


--
-- TOC entry 4807 (class 2606 OID 90583)
-- Name: login_history login_history_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.login_history
    ADD CONSTRAINT login_history_pkey PRIMARY KEY (history_id);


--
-- TOC entry 4809 (class 2606 OID 90585)
-- Name: module_master module_master_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.module_master
    ADD CONSTRAINT module_master_pkey PRIMARY KEY (module_id);


--
-- TOC entry 4811 (class 2606 OID 90587)
-- Name: parameter_settings parameter_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.parameter_settings
    ADD CONSTRAINT parameter_settings_pkey PRIMARY KEY (param_code);


--
-- TOC entry 4813 (class 2606 OID 90589)
-- Name: patients patients_mrn_key; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_mrn_key UNIQUE (mrn);


--
-- TOC entry 4815 (class 2606 OID 90591)
-- Name: patients patients_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_pkey PRIMARY KEY (patient_id);


--
-- TOC entry 4817 (class 2606 OID 90593)
-- Name: role_master role_master_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.role_master
    ADD CONSTRAINT role_master_pkey PRIMARY KEY (role_id);


--
-- TOC entry 4819 (class 2606 OID 90595)
-- Name: role_module_access role_module_access_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.role_module_access
    ADD CONSTRAINT role_module_access_pkey PRIMARY KEY (role_id, module_id);


--
-- TOC entry 4821 (class 2606 OID 90597)
-- Name: staff staff_employee_code_key; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.staff
    ADD CONSTRAINT staff_employee_code_key UNIQUE (employee_code);


--
-- TOC entry 4823 (class 2606 OID 90599)
-- Name: staff staff_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.staff
    ADD CONSTRAINT staff_pkey PRIMARY KEY (staff_id);


--
-- TOC entry 4825 (class 2606 OID 90601)
-- Name: user_role_mapping user_role_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.user_role_mapping
    ADD CONSTRAINT user_role_mapping_pkey PRIMARY KEY (user_id, role_id);


--
-- TOC entry 4827 (class 2606 OID 90603)
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (session_id);


--
-- TOC entry 4829 (class 2606 OID 90605)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4866 (class 2620 OID 90606)
-- Name: users hash_password; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER hash_password BEFORE INSERT OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.hash_password();


--
-- TOC entry 4844 (class 2620 OID 90607)
-- Name: branches track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.branches FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4846 (class 2620 OID 90608)
-- Name: hospitals track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.hospitals FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4848 (class 2620 OID 90609)
-- Name: login_history track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.login_history FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4850 (class 2620 OID 90610)
-- Name: module_master track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.module_master FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4852 (class 2620 OID 90611)
-- Name: parameter_settings track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.parameter_settings FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4854 (class 2620 OID 90612)
-- Name: patients track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.patients FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4856 (class 2620 OID 90613)
-- Name: role_master track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.role_master FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4858 (class 2620 OID 90614)
-- Name: role_module_access track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.role_module_access FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4860 (class 2620 OID 90615)
-- Name: staff track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.staff FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4862 (class 2620 OID 90616)
-- Name: user_role_mapping track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.user_role_mapping FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4864 (class 2620 OID 90617)
-- Name: user_sessions track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.user_sessions FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4867 (class 2620 OID 90618)
-- Name: users track_user_changes; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.track_user_changes();


--
-- TOC entry 4845 (class 2620 OID 90619)
-- Name: branches update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.branches FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4847 (class 2620 OID 90620)
-- Name: hospitals update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.hospitals FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4849 (class 2620 OID 90621)
-- Name: login_history update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.login_history FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4851 (class 2620 OID 90622)
-- Name: module_master update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.module_master FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4853 (class 2620 OID 90623)
-- Name: parameter_settings update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.parameter_settings FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4855 (class 2620 OID 90624)
-- Name: patients update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.patients FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4857 (class 2620 OID 90625)
-- Name: role_master update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.role_master FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4859 (class 2620 OID 90626)
-- Name: role_module_access update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.role_module_access FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4861 (class 2620 OID 90627)
-- Name: staff update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.staff FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4863 (class 2620 OID 90628)
-- Name: user_role_mapping update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.user_role_mapping FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4865 (class 2620 OID 90629)
-- Name: user_sessions update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.user_sessions FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4868 (class 2620 OID 90630)
-- Name: users update_timestamp; Type: TRIGGER; Schema: public; Owner: skinspire_admin
--

CREATE TRIGGER update_timestamp BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();


--
-- TOC entry 4830 (class 2606 OID 90631)
-- Name: branches branches_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT branches_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(hospital_id);


--
-- TOC entry 4831 (class 2606 OID 90636)
-- Name: login_history login_history_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.login_history
    ADD CONSTRAINT login_history_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- TOC entry 4832 (class 2606 OID 90641)
-- Name: module_master module_master_parent_module_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.module_master
    ADD CONSTRAINT module_master_parent_module_fkey FOREIGN KEY (parent_module) REFERENCES public.module_master(module_id);


--
-- TOC entry 4833 (class 2606 OID 90646)
-- Name: patients patients_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id);


--
-- TOC entry 4834 (class 2606 OID 90651)
-- Name: patients patients_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.patients
    ADD CONSTRAINT patients_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(hospital_id);


--
-- TOC entry 4835 (class 2606 OID 90656)
-- Name: role_master role_master_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.role_master
    ADD CONSTRAINT role_master_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(hospital_id);


--
-- TOC entry 4836 (class 2606 OID 90661)
-- Name: role_module_access role_module_access_module_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.role_module_access
    ADD CONSTRAINT role_module_access_module_id_fkey FOREIGN KEY (module_id) REFERENCES public.module_master(module_id);


--
-- TOC entry 4837 (class 2606 OID 90666)
-- Name: role_module_access role_module_access_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.role_module_access
    ADD CONSTRAINT role_module_access_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.role_master(role_id);


--
-- TOC entry 4838 (class 2606 OID 90671)
-- Name: staff staff_branch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.staff
    ADD CONSTRAINT staff_branch_id_fkey FOREIGN KEY (branch_id) REFERENCES public.branches(branch_id);


--
-- TOC entry 4839 (class 2606 OID 90676)
-- Name: staff staff_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.staff
    ADD CONSTRAINT staff_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(hospital_id);


--
-- TOC entry 4840 (class 2606 OID 90681)
-- Name: user_role_mapping user_role_mapping_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.user_role_mapping
    ADD CONSTRAINT user_role_mapping_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.role_master(role_id);


--
-- TOC entry 4841 (class 2606 OID 90686)
-- Name: user_role_mapping user_role_mapping_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.user_role_mapping
    ADD CONSTRAINT user_role_mapping_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- TOC entry 4842 (class 2606 OID 90691)
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id);


--
-- TOC entry 4843 (class 2606 OID 90696)
-- Name: users users_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: skinspire_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(hospital_id);


--
-- TOC entry 5034 (class 0 OID 0)
-- Dependencies: 7
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: skinspire_admin
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


-- Completed on 2025-03-24 07:30:00

--
-- PostgreSQL database dump complete
--

