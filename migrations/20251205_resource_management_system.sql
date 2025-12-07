-- Migration: Resource Management System
-- Date: 2025-12-05
-- Description: Creates tables for room management, resource requirements, and appointment resource allocation
--              Enables front desk to allocate rooms and staff to appointments

-- ============================================================================
-- 1. ROOMS MASTER TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS rooms (
    room_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),

    -- Room identification
    room_code VARCHAR(20) NOT NULL,
    room_name VARCHAR(100) NOT NULL,

    -- Room type determines what procedures can be done here
    room_type VARCHAR(30) NOT NULL,  -- 'procedure', 'ot', 'consultation', 'treatment', 'laser', 'recovery'

    -- Capacity and features
    capacity INTEGER DEFAULT 1,  -- How many patients can be in room simultaneously
    features JSONB,  -- {"has_ac": true, "equipment": ["laser_machine", "surgical_bed"]}

    -- Scheduling
    default_slot_duration_minutes INTEGER DEFAULT 30,
    buffer_minutes INTEGER DEFAULT 10,  -- Buffer time between appointments for cleaning/prep

    -- Operating hours (can override branch hours)
    operating_start_time TIME,
    operating_end_time TIME,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(100),

    -- Constraints
    CONSTRAINT uq_room_code UNIQUE (branch_id, room_code)
);

-- Indexes for rooms
CREATE INDEX IF NOT EXISTS idx_rooms_hospital ON rooms(hospital_id);
CREATE INDEX IF NOT EXISTS idx_rooms_branch ON rooms(branch_id);
CREATE INDEX IF NOT EXISTS idx_rooms_type ON rooms(branch_id, room_type) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_rooms_active ON rooms(branch_id, is_active) WHERE is_deleted = FALSE;

COMMENT ON TABLE rooms IS 'Master table for clinic rooms - procedure rooms, OT, consultation rooms, etc.';
COMMENT ON COLUMN rooms.room_type IS 'Room type: procedure, ot, consultation, treatment, laser, recovery';
COMMENT ON COLUMN rooms.buffer_minutes IS 'Time needed between appointments for room preparation/cleaning';


-- ============================================================================
-- 2. ROOM SLOTS (Availability Calendar for Rooms)
-- ============================================================================
CREATE TABLE IF NOT EXISTS room_slots (
    slot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    room_id UUID NOT NULL REFERENCES rooms(room_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),

    -- Slot timing
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,

    -- Availability
    is_available BOOLEAN DEFAULT TRUE,
    is_blocked BOOLEAN DEFAULT FALSE,
    block_reason VARCHAR(255),
    blocked_by UUID,
    blocked_at TIMESTAMP WITH TIME ZONE,

    -- Allocation (when booked)
    allocated_to_appointment_id UUID REFERENCES appointments(appointment_id),

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT room_slot_valid_time CHECK (start_time < end_time),
    CONSTRAINT uq_room_slot UNIQUE (room_id, slot_date, start_time)
);

-- Indexes for room_slots
CREATE INDEX IF NOT EXISTS idx_room_slots_date ON room_slots(slot_date);
CREATE INDEX IF NOT EXISTS idx_room_slots_room ON room_slots(room_id, slot_date);
CREATE INDEX IF NOT EXISTS idx_room_slots_available ON room_slots(room_id, slot_date, is_available, is_blocked);
CREATE INDEX IF NOT EXISTS idx_room_slots_appointment ON room_slots(allocated_to_appointment_id) WHERE allocated_to_appointment_id IS NOT NULL;

COMMENT ON TABLE room_slots IS 'Availability calendar for rooms - similar to appointment_slots but for rooms';


-- ============================================================================
-- 3. SERVICE RESOURCE REQUIREMENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS service_resource_requirements (
    requirement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    service_id UUID NOT NULL REFERENCES services(service_id),

    -- Resource type requirement
    resource_type VARCHAR(20) NOT NULL,  -- 'room', 'staff'

    -- For rooms: which room type is needed
    room_type VARCHAR(30),  -- 'procedure', 'ot', 'laser', etc.

    -- For staff: which staff type is needed
    staff_type VARCHAR(20),  -- 'doctor', 'therapist', 'nurse'
    staff_role VARCHAR(50),  -- More specific role like 'lead_therapist', 'assisting_nurse'

    -- Requirement details
    quantity_required INTEGER DEFAULT 1,
    is_mandatory BOOLEAN DEFAULT TRUE,
    duration_minutes INTEGER,  -- If different from service duration (e.g., doctor only needed for 15 min of 60 min procedure)

    -- Specific resource (optional - for services requiring specific room/staff)
    specific_resource_id UUID,  -- Can point to room_id or staff_id

    -- Notes
    notes TEXT,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_resource_type CHECK (resource_type IN ('room', 'staff'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_service_requirements_service ON service_resource_requirements(service_id);
CREATE INDEX IF NOT EXISTS idx_service_requirements_hospital ON service_resource_requirements(hospital_id);

COMMENT ON TABLE service_resource_requirements IS 'Defines what resources (rooms, staff) each service requires';
COMMENT ON COLUMN service_resource_requirements.duration_minutes IS 'Duration this resource is needed - can be less than full service duration';


-- ============================================================================
-- 4. APPOINTMENT RESOURCES (Allocated Resources per Appointment)
-- ============================================================================
CREATE TABLE IF NOT EXISTS appointment_resources (
    allocation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    appointment_id UUID NOT NULL REFERENCES appointments(appointment_id),

    -- Resource allocated
    resource_type VARCHAR(20) NOT NULL,  -- 'room', 'staff'
    resource_id UUID NOT NULL,  -- Points to room_id or staff_id

    -- Timing (may differ from appointment time)
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    allocation_date DATE NOT NULL,

    -- Status
    status VARCHAR(20) DEFAULT 'allocated',  -- 'allocated', 'in_use', 'released', 'cancelled'

    -- Role (for staff)
    role VARCHAR(50),  -- 'primary_therapist', 'assisting_nurse', 'consulting_doctor'

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    allocated_by UUID REFERENCES users(user_id),

    -- Constraints
    CONSTRAINT valid_allocation_resource_type CHECK (resource_type IN ('room', 'staff'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_appointment_resources_appointment ON appointment_resources(appointment_id);
CREATE INDEX IF NOT EXISTS idx_appointment_resources_resource ON appointment_resources(resource_type, resource_id, allocation_date);
CREATE INDEX IF NOT EXISTS idx_appointment_resources_date ON appointment_resources(allocation_date, start_time);

COMMENT ON TABLE appointment_resources IS 'Tracks which rooms and staff are allocated to each appointment';


-- ============================================================================
-- 5. ADD AUTO-APPROVAL FLAG TO SERVICES
-- ============================================================================
DO $$
BEGIN
    -- Add auto_approval_eligible column to services
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'services' AND column_name = 'auto_approval_eligible'
    ) THEN
        ALTER TABLE services ADD COLUMN auto_approval_eligible BOOLEAN DEFAULT FALSE;
        COMMENT ON COLUMN services.auto_approval_eligible IS 'If true, bookings for this service can be auto-approved when fully paid via self-service app';
    END IF;

    -- Add requires_room_allocation column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'services' AND column_name = 'requires_room_allocation'
    ) THEN
        ALTER TABLE services ADD COLUMN requires_room_allocation BOOLEAN DEFAULT FALSE;
        COMMENT ON COLUMN services.requires_room_allocation IS 'If true, room must be allocated before appointment can start';
    END IF;

    -- Add requires_staff_allocation column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'services' AND column_name = 'requires_staff_allocation'
    ) THEN
        ALTER TABLE services ADD COLUMN requires_staff_allocation BOOLEAN DEFAULT TRUE;
        COMMENT ON COLUMN services.requires_staff_allocation IS 'If true, therapist/nurse must be allocated before appointment can start';
    END IF;
END $$;


-- ============================================================================
-- 6. ADD RESOURCE ALLOCATION FIELDS TO APPOINTMENTS
-- ============================================================================
DO $$
BEGIN
    -- Add room_id to appointments
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'appointments' AND column_name = 'room_id'
    ) THEN
        ALTER TABLE appointments ADD COLUMN room_id UUID REFERENCES rooms(room_id);
        COMMENT ON COLUMN appointments.room_id IS 'Primary room allocated for this appointment';
    END IF;

    -- Add therapist_id to appointments (separate from doctor staff_id)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'appointments' AND column_name = 'therapist_id'
    ) THEN
        ALTER TABLE appointments ADD COLUMN therapist_id UUID REFERENCES staff(staff_id);
        COMMENT ON COLUMN appointments.therapist_id IS 'Therapist/nurse allocated for this appointment';
    END IF;

    -- Add resource_allocation_status
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'appointments' AND column_name = 'resource_allocation_status'
    ) THEN
        ALTER TABLE appointments ADD COLUMN resource_allocation_status VARCHAR(20) DEFAULT 'pending';
        COMMENT ON COLUMN appointments.resource_allocation_status IS 'Status: pending, partial, complete, not_required';
    END IF;

    -- Add approval fields
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'appointments' AND column_name = 'requires_approval'
    ) THEN
        ALTER TABLE appointments ADD COLUMN requires_approval BOOLEAN DEFAULT TRUE;
        ALTER TABLE appointments ADD COLUMN approved_at TIMESTAMP WITH TIME ZONE;
        ALTER TABLE appointments ADD COLUMN approved_by UUID REFERENCES users(user_id);
        COMMENT ON COLUMN appointments.requires_approval IS 'Whether this appointment needs front desk approval';
    END IF;
END $$;

-- Create indexes for new appointment columns
CREATE INDEX IF NOT EXISTS idx_appointments_room ON appointments(room_id) WHERE room_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_appointments_therapist ON appointments(therapist_id) WHERE therapist_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_appointments_resource_status ON appointments(resource_allocation_status);


-- ============================================================================
-- 7. INSERT SAMPLE ROOMS (for existing hospitals)
-- ============================================================================
INSERT INTO rooms (hospital_id, branch_id, room_code, room_name, room_type, capacity, default_slot_duration_minutes, buffer_minutes, is_active)
SELECT
    h.hospital_id,
    b.branch_id,
    room.code,
    room.name,
    room.type,
    1,
    room.duration,
    room.buffer,
    TRUE
FROM hospitals h
JOIN branches b ON b.hospital_id = h.hospital_id
CROSS JOIN (VALUES
    ('PROC-1', 'Procedure Room 1', 'procedure', 30, 10),
    ('PROC-2', 'Procedure Room 2', 'procedure', 30, 10),
    ('OT-1', 'Operation Theatre 1', 'ot', 60, 30),
    ('LASER-1', 'Laser Room 1', 'laser', 30, 10),
    ('CONSULT-1', 'Consultation Room 1', 'consultation', 15, 5),
    ('CONSULT-2', 'Consultation Room 2', 'consultation', 15, 5),
    ('TREAT-1', 'Treatment Room 1', 'treatment', 30, 10)
) AS room(code, name, type, duration, buffer)
WHERE h.name = 'Skinspire Clinic'
AND NOT EXISTS (
    SELECT 1 FROM rooms r
    WHERE r.branch_id = b.branch_id AND r.room_code = room.code
)
LIMIT 7;  -- One branch


-- ============================================================================
-- 8. INSERT SAMPLE SERVICE RESOURCE REQUIREMENTS
-- ============================================================================
-- For Laser Hair Removal: needs laser room + therapist
INSERT INTO service_resource_requirements (hospital_id, service_id, resource_type, room_type, is_mandatory)
SELECT
    s.hospital_id,
    s.service_id,
    'room',
    'laser',
    TRUE
FROM services s
WHERE s.service_name LIKE '%Laser%'
AND NOT EXISTS (
    SELECT 1 FROM service_resource_requirements srr
    WHERE srr.service_id = s.service_id AND srr.resource_type = 'room'
);

INSERT INTO service_resource_requirements (hospital_id, service_id, resource_type, staff_type, staff_role, is_mandatory)
SELECT
    s.hospital_id,
    s.service_id,
    'staff',
    'therapist',
    'primary_therapist',
    TRUE
FROM services s
WHERE s.service_name LIKE '%Laser%'
AND NOT EXISTS (
    SELECT 1 FROM service_resource_requirements srr
    WHERE srr.service_id = s.service_id AND srr.resource_type = 'staff'
);

-- For procedures: needs procedure room + therapist
INSERT INTO service_resource_requirements (hospital_id, service_id, resource_type, room_type, is_mandatory)
SELECT
    s.hospital_id,
    s.service_id,
    'room',
    'procedure',
    TRUE
FROM services s
WHERE s.service_type IN ('Skin Treatment', 'Cosmetic Procedure')
AND NOT EXISTS (
    SELECT 1 FROM service_resource_requirements srr
    WHERE srr.service_id = s.service_id AND srr.resource_type = 'room'
);


-- ============================================================================
-- VERIFY MIGRATION
-- ============================================================================
SELECT 'rooms' as table_name, COUNT(*) as count FROM rooms
UNION ALL
SELECT 'room_slots', COUNT(*) FROM room_slots
UNION ALL
SELECT 'service_resource_requirements', COUNT(*) FROM service_resource_requirements
UNION ALL
SELECT 'appointment_resources', COUNT(*) FROM appointment_resources;
