# Intelli-Clinic HMS: Complete Patient Lifecycle System
## Implementation Plan Document

**Version:** 1.1
**Created:** December 4, 2025
**Updated:** December 5, 2025
**Author:** Development Team
**Status:** In Progress

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [System Architecture](#3-system-architecture)
4. [Phase 1: Appointment System](#4-phase-1-appointment-system)
5. [Phase 2: Voice AI with Privacy-Preserving Architecture](#5-phase-2-voice-ai-with-privacy-preserving-architecture)
6. [Phase 3: Consultation Module](#6-phase-3-consultation-module)
7. [Phase 4: Procedure & Session Management](#7-phase-4-procedure--session-management)
8. [Phase 5: Patient Self-Service Portal](#8-phase-5-patient-self-service-portal)
9. [Phase 6: EMR Compliance & Patient History](#9-phase-6-emr-compliance--patient-history)
10. [Phase 7: Doctor Dashboard](#10-phase-7-doctor-dashboard)
11. [Privacy & Security Framework](#11-privacy--security-framework)
12. [Database Schema](#12-database-schema)
13. [API Specifications](#13-api-specifications)
14. [Cost Analysis](#14-cost-analysis)
15. [Timeline & Milestones](#15-timeline--milestones)

---

## 1. Executive Summary

### 1.1 Vision
Build a comprehensive patient lifecycle management system with **privacy-preserving Voice AI** that enables hands-free clinical documentation while ensuring complete patient data protection.

### 1.2 Key Features
- **Appointment Scheduling**: Time-slot based booking (self-service + front desk)
- **Voice AI Documentation**: Ambient clinical intelligence with data anonymization
- **Doctor Consultation**: SOAP notes, prescriptions, in-house dispensing
- **Procedure Management**: Multi-session tracking, consent forms, before/after photos
- **Patient Portal**: Self-service booking, prescription history, feedback
- **EMR Compliance**: ABDM-ready structure, FHIR format, audit logging

### 1.3 USP: Privacy-First Voice AI
- Patient identity **masked before cloud processing**
- Only anonymized medical content sent to AI
- Audio recordings stored **encrypted locally** in EMR-compliant tables
- **₹3,000/month** running cost vs ₹55,000+ for competitors

### 1.4 Target Client Profile
- **Skinspire Clinic**: 10-20 consultations/day
- Boutique consultation model
- Doctor doesn't use desktop/laptop during consultation
- High conversion rate, personalized care

---

## 2. Current State Analysis

### 2.1 Modules Already Built

| Module | Status | Notes |
|--------|--------|-------|
| Patient Registration | 80% | Basic registration, soft delete, special groups |
| Billing & Payments | 95% | Multi-tier discounts, GST, payment workflow |
| Inventory/Medicines | 90% | FIFO batch, barcode scanner, expiry tracking |
| Promotions/Discounts | 95% | Campaigns, loyalty, Buy X Get Y |
| Packages & Services | 90% | BOM, session plans, pricing |
| Suppliers | 90% | PO, invoice, payment, GST |
| Staff Management | 60% | Basic staff, approval workflow |
| Security/RBAC | 80% | Role-based access, audit logging |

### 2.2 Modules to Build

| Module | Priority | Complexity |
|--------|----------|------------|
| Appointments | P0 | Medium |
| Voice AI | P0 | High |
| Consultations | P0 | High |
| Procedures | P1 | Medium |
| Patient Portal | P1 | Medium |
| EMR Compliance | P1 | Medium |
| Doctor Dashboard | P2 | Low |

---

## 3. System Architecture

### 3.1 Overall Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INTELLI-CLINIC HMS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   FRONT DESK    │  │  CONSULTATION   │  │  PATIENT APP    │             │
│  │   (Web App)     │  │  (Voice AI)     │  │  (PWA)          │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                                │                                            │
│  ┌─────────────────────────────┴─────────────────────────────────────────┐  │
│  │                         FLASK API LAYER                                │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │  │
│  │  │ Appointments │ │ Consultations│ │  Voice AI    │ │  EMR         │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                │                                            │
│  ┌─────────────────────────────┴─────────────────────────────────────────┐  │
│  │                       PRIVACY & SECURITY LAYER                         │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │  │
│  │  │ Anonymization│ │  Encryption  │ │   Consent    │ │ Audit Trail  │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                │                                            │
│  ┌─────────────────────────────┴─────────────────────────────────────────┐  │
│  │                        POSTGRESQL DATABASE                             │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │  │
│  │  │ Appointments │ │ Consultations│ │  Recordings  │ │ EMR Records  │  │  │
│  │  │              │ │ Prescriptions│ │ (Encrypted)  │ │ (FHIR)       │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │       EXTERNAL SERVICES       │
                    │  ┌─────────┐  ┌─────────────┐ │
                    │  │Deepgram │  │ Claude API  │ │
                    │  │ (STT)   │  │ (AI Notes)  │ │
                    │  └─────────┘  └─────────────┘ │
                    │  (Anonymized data only)       │
                    └───────────────────────────────┘
```

### 3.2 Voice AI Privacy Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRIVACY-PRESERVING VOICE AI PIPELINE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 1: LOCAL CAPTURE                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Patient: "I'm Ramesh Kumar, Aadhaar 1234-5678-9012, headache..."  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  STEP 2: LOCAL ANONYMIZATION                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  • Generate Token: PATIENT_A7X9K2                                    │    │
│  │  • Map: "Ramesh Kumar" → PATIENT_A7X9K2                              │    │
│  │  • Redact: Aadhaar → [REDACTED], Phone → [REDACTED]                  │    │
│  │  • Store mapping ENCRYPTED locally                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  STEP 3: CLOUD PROCESSING (Anonymized Only)                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Deepgram: "PATIENT_A7X9K2 reports headache for 3 days..."          │    │
│  │  Claude: Generates SOAP notes with anonymized references             │    │
│  │  → NO real names, NO Aadhaar, NO phone numbers                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  STEP 4: LOCAL RE-IDENTIFICATION                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  • Lookup: PATIENT_A7X9K2 → patient_id UUID                          │    │
│  │  • Store in EMR tables with proper patient linkage                   │    │
│  │  • Encrypt all PII fields                                            │    │
│  │  • Store audio recording (encrypted, local only)                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Phase 1: Appointment System

### 4.1 Overview
Time-slot based appointment scheduling with doctor availability management.

### 4.2 Database Schema

```sql
-- Doctor weekly schedule template
CREATE TABLE doctor_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Sunday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration_minutes INT NOT NULL DEFAULT 30,
    break_start_time TIME,
    break_end_time TIME,
    max_patients_per_slot INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id),
    updated_by UUID REFERENCES users(user_id),
    UNIQUE(staff_id, branch_id, day_of_week)
);

-- Generated appointment slots
CREATE TABLE appointment_slots (
    slot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    max_bookings INT DEFAULT 1,
    current_bookings INT DEFAULT 0,
    is_available BOOLEAN DEFAULT true,
    is_blocked BOOLEAN DEFAULT false,
    block_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(staff_id, branch_id, slot_date, start_time)
);

-- Appointment types
CREATE TABLE appointment_types (
    type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_code VARCHAR(20) NOT NULL UNIQUE,
    type_name VARCHAR(100) NOT NULL,
    default_duration_minutes INT DEFAULT 30,
    requires_doctor BOOLEAN DEFAULT true,
    allow_self_booking BOOLEAN DEFAULT true,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main appointments table
CREATE TABLE appointments (
    appointment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_number VARCHAR(20) NOT NULL UNIQUE,
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    staff_id UUID REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    slot_id UUID REFERENCES appointment_slots(slot_id),
    appointment_type_id UUID REFERENCES appointment_types(type_id),

    -- Scheduling
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    actual_start_time TIMESTAMP,
    actual_end_time TIMESTAMP,

    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'requested',
    -- requested, confirmed, checked_in, in_progress, completed, cancelled, no_show, rescheduled

    -- Booking info
    booking_source VARCHAR(20) NOT NULL DEFAULT 'front_desk',
    -- front_desk, self_service, whatsapp, phone, walk_in

    -- Clinical info
    chief_complaint TEXT,
    priority VARCHAR(10) DEFAULT 'normal', -- normal, urgent, emergency

    -- Reference to previous appointment (for follow-ups)
    parent_appointment_id UUID REFERENCES appointments(appointment_id),
    is_follow_up BOOLEAN DEFAULT false,

    -- Notes
    patient_notes TEXT,
    internal_notes TEXT,
    cancellation_reason TEXT,

    -- Reminders
    reminder_sent BOOLEAN DEFAULT false,
    reminder_sent_at TIMESTAMP,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id),
    updated_by UUID REFERENCES users(user_id),
    confirmed_by UUID REFERENCES users(user_id),
    confirmed_at TIMESTAMP,
    checked_in_by UUID REFERENCES users(user_id),
    checked_in_at TIMESTAMP
);

-- Appointment status history
CREATE TABLE appointment_status_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(appointment_id),
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_by UUID REFERENCES users(user_id),
    change_reason TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_staff ON appointments(staff_id);
CREATE INDEX idx_appointments_date ON appointments(appointment_date);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_appointment_slots_date ON appointment_slots(slot_date);
CREATE INDEX idx_appointment_slots_staff ON appointment_slots(staff_id);
```

### 4.3 Appointment Workflow

```
┌──────────┐    ┌───────────┐    ┌────────────┐    ┌─────────────┐    ┌───────────┐
│ REQUESTED│───>│ CONFIRMED │───>│ CHECKED_IN │───>│ IN_PROGRESS │───>│ COMPLETED │
└──────────┘    └───────────┘    └────────────┘    └─────────────┘    └───────────┘
      │               │
      │               │
      ▼               ▼
┌──────────┐    ┌───────────┐
│ CANCELLED│    │ NO_SHOW   │
└──────────┘    └───────────┘
      │
      ▼
┌────────────┐
│ RESCHEDULED│
└────────────┘
```

### 4.4 Features

1. **Doctor Schedule Management**
   - Weekly availability templates
   - Break time configuration
   - Holiday/leave blocking
   - Multi-branch support

2. **Slot Generation**
   - Auto-generate slots based on schedule
   - Configurable slot duration (15/30/45/60 min)
   - Block slots for meetings/breaks

3. **Booking Interface**
   - Front desk booking with patient search
   - Patient self-service (OTP verification)
   - Walk-in registration
   - Follow-up scheduling

4. **Calendar Views**
   - Doctor's daily schedule
   - Weekly overview
   - Patient queue for today

5. **Notifications**
   - Booking confirmation (SMS/WhatsApp)
   - 24-hour reminder
   - Check-in notification

### 4.5 API Endpoints

```
GET    /api/appointments/slots?doctor_id=&date=&branch_id=
POST   /api/appointments/book
GET    /api/appointments/{appointment_id}
PUT    /api/appointments/{appointment_id}
POST   /api/appointments/{appointment_id}/check-in
POST   /api/appointments/{appointment_id}/cancel
POST   /api/appointments/{appointment_id}/reschedule
GET    /api/appointments/today?doctor_id=&branch_id=
GET    /api/appointments/calendar?doctor_id=&start_date=&end_date=

GET    /api/doctor-schedules/{staff_id}
POST   /api/doctor-schedules
PUT    /api/doctor-schedules/{schedule_id}
POST   /api/doctor-schedules/generate-slots
POST   /api/doctor-schedules/block-slots
```

### 4.6 Views/Templates

```
/appointments/book              - Booking wizard
/appointments/calendar          - Doctor's calendar view
/appointments/queue             - Today's patient queue
/appointments/list              - All appointments list
/appointments/{id}              - Appointment details
/doctor-schedules/manage        - Schedule management
```

### 4.7 Files to Create

```
app/models/appointment.py
app/views/appointment.py
app/api/routes/appointment_api.py
app/services/appointment_service.py
app/services/slot_generator_service.py
app/forms/appointment_forms.py
app/config/modules/appointment_config.py
app/templates/appointments/book.html
app/templates/appointments/calendar.html
app/templates/appointments/queue.html
app/templates/appointments/list.html
app/templates/appointments/view.html
app/templates/doctor_schedules/manage.html
app/static/js/components/appointment_calendar.js
app/static/js/components/slot_picker.js
migrations/20251204_create_appointment_tables.sql
migrations/20251205_resource_management_system.sql
```

### 4.8 Resource Management System (Added Dec 5, 2025)

Comprehensive resource allocation system for rooms and staff during appointment booking.

#### 4.8.1 Design Decisions

1. **Room Types**: Procedure rooms, OT, Consultation, Treatment, Laser, Recovery
2. **Human Resources**: Therapist/Nurse dedicated for entire procedure, Doctor for certain procedures
3. **Booking Workflow**: Front desk manually selects room and resources
4. **Approval Workflow**:
   - Default: All bookings require front desk approval
   - Exception: Auto-approval for flagged services (fully paid via self-service app)
5. **Slot Duration**: Based on service/package duration, not just doctor slot size
6. **Google Calendar**: One-way sync (HMS → Google) - deferred to later phase

#### 4.8.2 Database Schema - Resource Management

```sql
-- Room master table
CREATE TABLE rooms (
    room_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    room_code VARCHAR(20) NOT NULL,
    room_name VARCHAR(100) NOT NULL,
    room_type VARCHAR(30) NOT NULL CHECK (room_type IN ('procedure', 'ot', 'consultation', 'treatment', 'laser', 'recovery')),
    capacity INTEGER DEFAULT 1,
    features JSONB,  -- e.g., {"has_ac": true, "has_sink": true}
    default_slot_duration_minutes INTEGER DEFAULT 30,
    buffer_minutes INTEGER DEFAULT 10,  -- Cleanup time between appointments
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP,
    UNIQUE(branch_id, room_code)
);

-- Room availability calendar (for blocking/special hours)
CREATE TABLE room_slots (
    slot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES rooms(room_id),
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT true,
    is_blocked BOOLEAN DEFAULT false,
    block_reason VARCHAR(255),
    blocked_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(room_id, slot_date, start_time)
);

-- Service resource requirements
CREATE TABLE service_resource_requirements (
    requirement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES services(service_id),
    package_id UUID REFERENCES packages(package_id),

    -- Room requirements
    requires_room BOOLEAN DEFAULT false,
    room_type VARCHAR(30),  -- Required room type

    -- Staff requirements
    requires_doctor BOOLEAN DEFAULT false,
    requires_therapist BOOLEAN DEFAULT false,
    requires_nurse BOOLEAN DEFAULT false,
    staff_count INTEGER DEFAULT 1,  -- Number of staff needed

    -- Duration and preparation
    preparation_time_minutes INTEGER DEFAULT 0,
    cleanup_time_minutes INTEGER DEFAULT 0,

    -- Special requirements
    special_requirements JSONB,  -- e.g., {"needs_anesthesia": true}
    notes TEXT,

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT service_or_package CHECK (
        (service_id IS NOT NULL AND package_id IS NULL) OR
        (service_id IS NULL AND package_id IS NOT NULL)
    )
);

-- Appointment resource allocation
CREATE TABLE appointment_resources (
    allocation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(appointment_id),

    -- Resource type
    resource_type VARCHAR(20) NOT NULL CHECK (resource_type IN ('room', 'doctor', 'therapist', 'nurse', 'equipment')),

    -- Resource reference
    room_id UUID REFERENCES rooms(room_id),
    staff_id UUID REFERENCES staff(staff_id),

    -- Time allocation
    allocation_start TIMESTAMP NOT NULL,
    allocation_end TIMESTAMP NOT NULL,

    -- Status
    status VARCHAR(20) DEFAULT 'reserved' CHECK (status IN ('reserved', 'confirmed', 'in_use', 'completed', 'cancelled')),

    -- Audit
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    allocated_by VARCHAR(100),
    confirmed_at TIMESTAMP,
    confirmed_by VARCHAR(100),

    CONSTRAINT valid_resource CHECK (
        (resource_type = 'room' AND room_id IS NOT NULL) OR
        (resource_type IN ('doctor', 'therapist', 'nurse') AND staff_id IS NOT NULL)
    )
);

-- Additional columns for services table
ALTER TABLE services ADD COLUMN IF NOT EXISTS auto_approval_eligible BOOLEAN DEFAULT false;
ALTER TABLE services ADD COLUMN IF NOT EXISTS requires_room_allocation BOOLEAN DEFAULT false;
ALTER TABLE services ADD COLUMN IF NOT EXISTS requires_staff_allocation BOOLEAN DEFAULT true;

-- Additional columns for appointments table
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS room_id UUID REFERENCES rooms(room_id);
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS therapist_id UUID REFERENCES staff(staff_id);
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS resource_allocation_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN DEFAULT true;
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP;
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS approved_by VARCHAR(100);
```

#### 4.8.3 Resource Management API Endpoints

```
# Room Management
GET    /api/appointments/web/rooms/available
       ?date=&start_time=&end_time=&room_type=&service_id=
       Returns available rooms with conflict checking

# Staff/Therapist Management
GET    /api/appointments/web/therapists/available
       ?date=&start_time=&end_time=&staff_type=&service_id=
       Returns available therapists with conflict checking

# Service Requirements
GET    /api/appointments/web/service/<service_id>/requirements
       Returns resource requirements for a service

# Resource Allocation
POST   /api/appointments/web/appointment/<appointment_id>/allocate-resources
       Body: {room_id, therapist_id, approve}
       Allocates room and staff to appointment
```

#### 4.8.4 Service-Based Slot Duration

Slot duration is determined by service/package duration:
- When booking type is 'service', use `service.duration_minutes`
- When booking type is 'package', use `package_plan.duration_minutes` or total of services
- Combine consecutive base slots to create longer appointment slots
- Example: 60-min service on 30-min slot schedule = 2 consecutive slots combined

```python
# Slot duration logic
def get_slot_duration(booking_type, service_id, package_plan_id):
    if booking_type == 'service' and service_id:
        service = Service.query.get(service_id)
        return service.duration_minutes or 30
    elif booking_type == 'package' and package_plan_id:
        plan = PackagePaymentPlan.query.get(package_plan_id)
        return plan.duration_minutes or 60
    return 30  # Default
```

#### 4.8.5 Booking Workflow with Resource Allocation

```
┌─────────────────┐
│ Step 1: Patient │
│ Selection       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 2: Service/│
│ Package Select  │ ← Determines slot duration & resource requirements
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 3: Doctor  │
│ & Slot Select   │ ← Shows combined slots based on service duration
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Step 3b: Resource Allocation        │ ← NEW
│ - Room selection (if required)      │
│ - Therapist selection (if required) │
│ - Shows availability indicators     │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Step 4: Summary │ ← Shows room & therapist in summary
│ & Confirmation  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Submit Booking  │ → Allocates resources & creates appointment
└─────────────────┘
```

#### 4.8.6 SQLAlchemy Models Added

```python
# app/models/master.py

class Room(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Room master table for procedure rooms, OT, etc."""
    __tablename__ = 'rooms'
    room_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    room_code = Column(String(20), nullable=False)
    room_name = Column(String(100), nullable=False)
    room_type = Column(String(30), nullable=False)  # procedure, ot, consultation, etc.
    capacity = Column(Integer, default=1)
    features = Column(JSONB)
    default_slot_duration_minutes = Column(Integer, default=30)
    buffer_minutes = Column(Integer, default=10)
    # ... relationships

class RoomSlot(Base):
    """Room availability calendar"""
    __tablename__ = 'room_slots'
    # ... columns

class ServiceResourceRequirement(Base):
    """Defines resource requirements for each service/package"""
    __tablename__ = 'service_resource_requirements'
    requires_room = Column(Boolean, default=False)
    room_type = Column(String(30))
    requires_doctor = Column(Boolean, default=False)
    requires_therapist = Column(Boolean, default=False)
    # ... relationships

class AppointmentResource(Base):
    """Tracks allocated resources for each appointment"""
    __tablename__ = 'appointment_resources'
    resource_type = Column(String(20), nullable=False)  # room, doctor, therapist
    allocation_start = Column(DateTime, nullable=False)
    allocation_end = Column(DateTime, nullable=False)
    status = Column(String(20), default='reserved')
    # ... relationships
```

#### 4.8.7 Files Created/Modified

```
# New files
migrations/20251205_resource_management_system.sql

# Modified files
app/models/master.py          - Added Room, RoomSlot, ServiceResourceRequirement, AppointmentResource
app/models/appointment.py     - Added room_id, therapist_id, resource_allocation_status columns
app/api/routes/appointment_api.py - Added resource management endpoints
app/templates/appointment/book.html - Added resource allocation section in Step 3
```

---

## 5. Phase 2: Voice AI with Privacy-Preserving Architecture

### 5.1 Overview
Ambient clinical intelligence that captures doctor-patient conversations, anonymizes PII locally, processes via cloud AI, and stores encrypted recordings.

### 5.2 Tech Stack

| Component | Technology | Cost |
|-----------|------------|------|
| Speech-to-Text | Deepgram Nova-3 Medical | $0.0043/min |
| AI Processing | Claude 3.5 Sonnet | ~$0.003/consultation |
| Audio Capture | Web Audio API | Free |
| Local Encryption | AES-256-GCM | Free |
| Key Management | Local keystore | Free |

### 5.3 Database Schema

```sql
-- Voice session tokens for anonymization
CREATE TABLE voice_session_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_token VARCHAR(50) NOT NULL UNIQUE,
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    consultation_id UUID,
    staff_id UUID REFERENCES staff(staff_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true,
    CONSTRAINT token_format CHECK (session_token ~ '^PATIENT_[A-Z0-9]{6}$')
);

-- PII patterns for local redaction
CREATE TABLE pii_redaction_patterns (
    pattern_id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(50) NOT NULL,
    pattern_type VARCHAR(30) NOT NULL, -- aadhaar, phone, email, name, address
    regex_pattern TEXT NOT NULL,
    replacement_template VARCHAR(50) NOT NULL,
    priority INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default patterns
INSERT INTO pii_redaction_patterns (pattern_name, pattern_type, regex_pattern, replacement_template, priority) VALUES
('Aadhaar Number', 'aadhaar', '\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[AADHAAR_REDACTED]', 10),
('Phone Number', 'phone', '\b(?:\+91[\s-]?)?[6-9]\d{9}\b', '[PHONE_REDACTED]', 9),
('Email Address', 'email', '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', 8),
('PAN Number', 'pan', '\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN_REDACTED]', 7);

-- Consultation recordings (EMR-compliant)
CREATE TABLE consultation_recordings (
    recording_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID NOT NULL,
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    staff_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),

    -- Audio data (encrypted)
    audio_data BYTEA, -- AES-256-GCM encrypted
    audio_format VARCHAR(10) DEFAULT 'webm',
    audio_duration_seconds INT,
    audio_size_bytes INT,

    -- Encryption metadata
    encryption_algorithm VARCHAR(20) DEFAULT 'AES-256-GCM',
    encryption_key_id UUID NOT NULL,
    iv BYTEA NOT NULL, -- Initialization vector

    -- Consent tracking
    consent_given BOOLEAN NOT NULL DEFAULT false,
    consent_timestamp TIMESTAMP,
    consent_method VARCHAR(20), -- otp, signature, verbal_recorded
    consent_ip_address VARCHAR(45),

    -- Retention policy
    retention_days INT DEFAULT 365,
    auto_delete_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP,
    deletion_reason VARCHAR(100),

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id),

    CONSTRAINT valid_consent CHECK (
        (consent_given = true AND consent_timestamp IS NOT NULL) OR
        (consent_given = false)
    )
);

-- Consultation transcripts
CREATE TABLE consultation_transcripts (
    transcript_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID NOT NULL,
    recording_id UUID REFERENCES consultation_recordings(recording_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    -- Raw transcript (encrypted)
    raw_transcript_encrypted BYTEA,

    -- Structured notes (encrypted JSONB)
    structured_notes_encrypted BYTEA,
    -- When decrypted, contains:
    -- {
    --   "subjective": "...",
    --   "objective": "...",
    --   "assessment": "...",
    --   "plan": "...",
    --   "chief_complaint": "...",
    --   "history_of_present_illness": "...",
    --   "prescriptions": [...]
    -- }

    -- Processing metadata
    ai_model_used VARCHAR(50),
    deepgram_model_used VARCHAR(50),
    confidence_score DECIMAL(3,2),
    processing_time_ms INT,

    -- Verification
    doctor_verified BOOLEAN DEFAULT false,
    verified_at TIMESTAMP,
    verified_by UUID REFERENCES staff(staff_id),
    verification_notes TEXT,

    -- Encryption
    encryption_key_id UUID NOT NULL,
    iv BYTEA NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Encryption keys (stored securely)
CREATE TABLE encryption_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_type VARCHAR(20) NOT NULL, -- master, recording, transcript
    key_data BYTEA NOT NULL, -- Encrypted with master key
    algorithm VARCHAR(20) DEFAULT 'AES-256-GCM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    rotated_from UUID REFERENCES encryption_keys(key_id)
);

-- Voice AI usage log
CREATE TABLE voice_ai_usage_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID,
    patient_id UUID REFERENCES patients(patient_id),
    staff_id UUID REFERENCES staff(staff_id),

    -- Usage metrics
    audio_duration_seconds INT,
    transcript_word_count INT,
    deepgram_cost_usd DECIMAL(10,6),
    claude_tokens_used INT,
    claude_cost_usd DECIMAL(10,6),
    total_cost_usd DECIMAL(10,6),

    -- Processing info
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_status VARCHAR(20), -- processing, completed, failed
    error_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_recordings_consultation ON consultation_recordings(consultation_id);
CREATE INDEX idx_recordings_patient ON consultation_recordings(patient_id);
CREATE INDEX idx_recordings_date ON consultation_recordings(created_at);
CREATE INDEX idx_transcripts_consultation ON consultation_transcripts(consultation_id);
CREATE INDEX idx_voice_tokens_patient ON voice_session_tokens(patient_id);
CREATE INDEX idx_voice_tokens_active ON voice_session_tokens(is_active, expires_at);
```

### 5.4 Privacy Service Architecture

```python
# app/services/privacy_service.py

class PrivacyService:
    """
    Handles all privacy-related operations for Voice AI
    """

    def generate_session_token(self, patient_id: UUID) -> str:
        """Generate anonymized session token for patient"""
        # Returns: PATIENT_A7X9K2

    def anonymize_text(self, text: str, session_token: str) -> str:
        """Replace all PII with redaction tokens"""
        # Input: "I'm Ramesh Kumar, Aadhaar 1234-5678-9012"
        # Output: "I'm PATIENT_A7X9K2, [AADHAAR_REDACTED]"

    def detect_pii(self, text: str) -> List[PIIMatch]:
        """Detect PII patterns in text"""

    def store_token_mapping(self, token: str, patient_id: UUID) -> None:
        """Store encrypted token-to-patient mapping"""

    def restore_identity(self, token: str) -> UUID:
        """Lookup patient_id from session token"""

    def encrypt_data(self, data: bytes) -> Tuple[bytes, bytes, UUID]:
        """Encrypt data with AES-256-GCM, return (ciphertext, iv, key_id)"""

    def decrypt_data(self, ciphertext: bytes, iv: bytes, key_id: UUID) -> bytes:
        """Decrypt data using stored key"""
```

### 5.5 Voice AI Service Architecture

```python
# app/services/voice_ai_service.py

class VoiceAIService:
    """
    Main Voice AI service for clinical documentation
    """

    async def start_session(self, patient_id: UUID, doctor_id: UUID) -> VoiceSession:
        """Initialize voice recording session with consent verification"""

    async def process_audio_stream(self, audio_chunk: bytes, session: VoiceSession) -> None:
        """Process audio chunk - anonymize and send to Deepgram"""

    async def get_transcript(self, session: VoiceSession) -> str:
        """Get current anonymized transcript"""

    async def generate_clinical_notes(self, transcript: str) -> ClinicalNotes:
        """Use Claude to generate structured SOAP notes"""

    async def end_session(self, session: VoiceSession) -> ConsultationRecord:
        """Finalize session, store encrypted data, return record"""

    async def verify_and_save(self, consultation_id: UUID, notes: ClinicalNotes) -> None:
        """Doctor verification and final save"""
```

### 5.6 Deepgram Integration

```python
# Configuration for Deepgram Nova-3 Medical
DEEPGRAM_CONFIG = {
    "model": "nova-2-medical",
    "language": "en-IN",  # Indian English
    "punctuate": True,
    "diarize": True,  # Speaker identification
    "smart_format": True,
    "paragraphs": True,
    "utterances": True,
    "redact": ["pci", "ssn"],  # Additional redaction
    "keywords": [
        "paracetamol", "ibuprofen", "amoxicillin",
        # Add common medicines
    ]
}
```

### 5.7 Claude Prompt for Clinical Notes

```python
CLINICAL_NOTES_PROMPT = """
You are a medical documentation assistant. Given the following doctor-patient
consultation transcript, generate structured clinical notes in SOAP format.

IMPORTANT RULES:
1. Extract only medical information
2. Do not include any patient identifying information
3. Use standard medical terminology
4. Include all mentioned medications with dosage
5. Flag any drug allergies mentioned

Transcript:
{transcript}

Generate notes in this JSON format:
{
    "chief_complaint": "...",
    "history_of_present_illness": "...",
    "subjective": "...",
    "objective": "...",
    "assessment": "...",
    "plan": "...",
    "prescriptions": [
        {
            "medicine_name": "...",
            "dosage": "...",
            "frequency": "...",
            "duration": "...",
            "instructions": "..."
        }
    ],
    "allergies_mentioned": [],
    "follow_up_recommended": true/false,
    "follow_up_days": null or number
}
"""
```

### 5.8 Files to Create

```
app/services/voice_ai_service.py
app/services/privacy_service.py
app/services/deepgram_service.py
app/services/encryption_service.py
app/api/routes/voice_ai_api.py
app/models/voice_ai.py
app/templates/voice_ai/console.html
app/templates/voice_ai/consent_modal.html
app/static/js/components/voice_recorder.js
app/static/js/components/transcript_viewer.js
app/config/voice_ai_config.py
migrations/20251204_create_voice_ai_tables.sql
```

---

## 6. Phase 3: Consultation Module

### 6.1 Overview
Complete consultation workflow from appointment check-in to prescription generation.

### 6.2 Database Schema

```sql
-- Main consultation record
CREATE TABLE consultations (
    consultation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_number VARCHAR(20) NOT NULL UNIQUE,

    -- References
    appointment_id UUID REFERENCES appointments(appointment_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    doctor_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),

    -- Consultation info
    consultation_type VARCHAR(30) NOT NULL DEFAULT 'initial',
    -- initial, follow_up, procedure_review, emergency

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'started',
    -- started, vitals_captured, in_examination, prescription_done, completed, cancelled

    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_minutes INT,

    -- Voice AI
    voice_assisted BOOLEAN DEFAULT false,
    recording_id UUID REFERENCES consultation_recordings(recording_id),

    -- Billing reference
    invoice_id UUID,

    -- Notes
    summary TEXT,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id),
    updated_by UUID REFERENCES users(user_id)
);

-- Patient vitals
CREATE TABLE patient_vitals (
    vital_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID REFERENCES consultations(consultation_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    -- Vital signs
    blood_pressure_systolic INT,
    blood_pressure_diastolic INT,
    pulse_rate INT,
    respiratory_rate INT,
    temperature DECIMAL(4,1), -- Fahrenheit
    spo2 INT, -- Oxygen saturation %

    -- Body measurements
    weight DECIMAL(5,2), -- kg
    height DECIMAL(5,2), -- cm
    bmi DECIMAL(4,2),

    -- Additional
    blood_glucose DECIMAL(5,1),
    notes TEXT,

    -- Audit
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recorded_by UUID REFERENCES staff(staff_id)
);

-- SOAP Notes
CREATE TABLE consultation_notes (
    note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID NOT NULL REFERENCES consultations(consultation_id),

    -- Chief complaint
    chief_complaint TEXT,
    history_of_present_illness TEXT,

    -- SOAP format
    subjective TEXT,
    objective TEXT,
    assessment TEXT,
    plan TEXT,

    -- Additional sections
    review_of_systems TEXT,
    physical_examination TEXT,

    -- AI-generated flag
    is_voice_generated BOOLEAN DEFAULT false,
    ai_confidence_score DECIMAL(3,2),

    -- Verification
    doctor_verified BOOLEAN DEFAULT false,
    verified_at TIMESTAMP,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id),
    updated_by UUID REFERENCES users(user_id)
);

-- Diagnosis codes (ICD-10)
CREATE TABLE diagnosis_codes (
    code_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    icd_code VARCHAR(10) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category VARCHAR(100),
    chapter VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Consultation diagnoses
CREATE TABLE consultation_diagnoses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID NOT NULL REFERENCES consultations(consultation_id),
    diagnosis_code_id UUID NOT NULL REFERENCES diagnosis_codes(code_id),
    is_primary BOOLEAN DEFAULT false,
    diagnosis_notes TEXT,
    diagnosed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    diagnosed_by UUID REFERENCES staff(staff_id)
);

-- Prescriptions
CREATE TABLE prescriptions (
    prescription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_number VARCHAR(20) NOT NULL UNIQUE,
    consultation_id UUID NOT NULL REFERENCES consultations(consultation_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    doctor_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),

    -- Status
    status VARCHAR(20) DEFAULT 'draft',
    -- draft, finalized, dispensed, cancelled

    -- Dispensing
    dispense_from_clinic BOOLEAN DEFAULT false,
    is_dispensed BOOLEAN DEFAULT false,
    dispensed_at TIMESTAMP,
    dispensed_by UUID REFERENCES staff(staff_id),

    -- Billing
    invoice_id UUID,

    -- Notes
    general_instructions TEXT,
    dietary_advice TEXT,
    follow_up_instructions TEXT,

    -- Document
    pdf_document BYTEA,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finalized_at TIMESTAMP,
    created_by UUID REFERENCES users(user_id)
);

-- Prescription items
CREATE TABLE prescription_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id UUID NOT NULL REFERENCES prescriptions(prescription_id),
    medicine_id UUID REFERENCES medicines(medicine_id),

    -- Medicine details (for external medicines)
    medicine_name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200),
    dosage_form VARCHAR(50), -- tablet, syrup, injection, etc.

    -- Dosage
    dosage VARCHAR(50) NOT NULL, -- "500mg", "10ml"
    frequency VARCHAR(100) NOT NULL, -- "Twice daily", "Every 8 hours"
    duration VARCHAR(50) NOT NULL, -- "5 days", "1 week"
    quantity INT,

    -- Timing
    timing VARCHAR(100), -- "After food", "Before bed"
    route VARCHAR(50), -- oral, topical, IV

    -- Instructions
    special_instructions TEXT,

    -- Flags
    is_in_house BOOLEAN DEFAULT false, -- Dispense from clinic stock
    is_sos BOOLEAN DEFAULT false, -- As needed
    is_tapering BOOLEAN DEFAULT false,

    -- Display
    display_order INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_consultations_patient ON consultations(patient_id);
CREATE INDEX idx_consultations_doctor ON consultations(doctor_id);
CREATE INDEX idx_consultations_appointment ON consultations(appointment_id);
CREATE INDEX idx_consultations_date ON consultations(started_at);
CREATE INDEX idx_prescriptions_consultation ON prescriptions(consultation_id);
CREATE INDEX idx_prescription_items_prescription ON prescription_items(prescription_id);
CREATE INDEX idx_vitals_consultation ON patient_vitals(consultation_id);
```

### 6.3 Consultation Workflow

```
┌───────────────┐
│ APPOINTMENT   │
│ CHECKED IN    │
└───────┬───────┘
        │
        ▼
┌───────────────┐    ┌───────────────────────────────────────────────────┐
│   STARTED     │    │ Voice AI: "Start Recording"                       │
│               │───>│ - Consent verification                            │
└───────┬───────┘    │ - Begin audio capture                             │
        │            └───────────────────────────────────────────────────┘
        ▼
┌───────────────┐
│ VITALS        │ Nurse/assistant captures vitals
│ CAPTURED      │
└───────┬───────┘
        │
        ▼
┌───────────────┐    ┌───────────────────────────────────────────────────┐
│ IN EXAMINATION│    │ Voice AI: Continuous transcription                │
│               │───>│ - Real-time transcript display                    │
└───────┬───────┘    │ - PII anonymization active                        │
        │            └───────────────────────────────────────────────────┘
        ▼
┌───────────────┐    ┌───────────────────────────────────────────────────┐
│ PRESCRIPTION  │    │ Voice AI: "Generate Notes"                        │
│ DONE          │───>│ - AI generates SOAP notes                         │
└───────┬───────┘    │ - Prescription extracted                          │
        │            │ - Doctor reviews & confirms                       │
        ▼            └───────────────────────────────────────────────────┘
┌───────────────┐
│  COMPLETED    │ Auto-trigger: Billing, Follow-up scheduling
│               │
└───────────────┘
```

### 6.4 Features

1. **Consultation Start**
   - Start from appointment check-in
   - Voice AI consent modal
   - Previous visit summary

2. **Vitals Capture**
   - Quick entry form
   - Auto-calculate BMI
   - Alert for abnormal values

3. **Clinical Notes**
   - Voice AI transcription
   - SOAP format template
   - Manual entry option
   - ICD-10 diagnosis search

4. **Prescription Builder**
   - Medicine autocomplete (from inventory)
   - Frequency presets
   - Drug interaction warning
   - In-house dispensing toggle

5. **Completion**
   - Auto-generate billing for in-house medicines
   - Prescription PDF generation
   - Follow-up scheduling prompt
   - Patient feedback request

### 6.5 Files to Create

```
app/models/consultation.py
app/views/consultation.py
app/api/routes/consultation_api.py
app/services/consultation_service.py
app/services/prescription_service.py
app/forms/consultation_forms.py
app/config/modules/consultation_config.py
app/templates/consultations/start.html
app/templates/consultations/vitals.html
app/templates/consultations/notes.html
app/templates/consultations/prescription.html
app/templates/consultations/summary.html
app/templates/consultations/prescription_pdf.html
app/static/js/components/consultation_workflow.js
app/static/js/components/prescription_builder.js
app/static/js/components/icd_search.js
migrations/20251204_create_consultation_tables.sql
```

---

## 7. Phase 4: Procedure & Session Management

### 7.1 Overview
Multi-session procedure tracking with consent management and before/after documentation.

### 7.2 Database Schema

```sql
-- Procedure orders (from consultation)
CREATE TABLE procedure_orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number VARCHAR(20) NOT NULL UNIQUE,

    -- References
    consultation_id UUID REFERENCES consultations(consultation_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    doctor_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),

    -- Procedure/Package
    package_id UUID REFERENCES packages(package_id),
    service_id UUID REFERENCES services(service_id),

    -- Sessions
    total_sessions INT NOT NULL DEFAULT 1,
    completed_sessions INT DEFAULT 0,
    min_gap_days INT DEFAULT 14, -- Minimum gap between sessions

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'ordered',
    -- ordered, scheduled, in_progress, completed, cancelled, on_hold

    -- Billing
    is_prepaid BOOLEAN DEFAULT false,
    invoice_id UUID,

    -- Notes
    clinical_notes TEXT,
    special_instructions TEXT,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id)
);

-- Individual procedure sessions
CREATE TABLE procedure_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_number INT NOT NULL,

    -- References
    order_id UUID NOT NULL REFERENCES procedure_orders(order_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    appointment_id UUID REFERENCES appointments(appointment_id),

    -- Scheduling
    scheduled_date DATE,
    scheduled_time TIME,

    -- Execution
    performed_by UUID REFERENCES staff(staff_id),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_minutes INT,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    -- scheduled, consent_pending, ready, in_progress, completed, cancelled, no_show

    -- Consent
    consent_id UUID,

    -- Notes
    pre_procedure_notes TEXT,
    procedure_notes TEXT,
    post_procedure_notes TEXT,
    complications TEXT,

    -- Follow-up
    next_session_recommended_date DATE,
    follow_up_notes TEXT,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Digital consent forms
CREATE TABLE consent_forms (
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consent_number VARCHAR(20) NOT NULL UNIQUE,

    -- References
    session_id UUID REFERENCES procedure_sessions(session_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    -- Consent type
    consent_type VARCHAR(50) NOT NULL,
    -- procedure, recording, photography, treatment_plan

    -- Consent content
    consent_template_id UUID,
    consent_text TEXT NOT NULL,

    -- Signature
    signature_data TEXT, -- Base64 encoded signature image
    signature_type VARCHAR(20), -- drawn, typed, otp

    -- Verification
    signed_at TIMESTAMP,
    signer_name VARCHAR(100),
    signer_relationship VARCHAR(50), -- self, guardian, spouse

    -- Additional info
    witness_name VARCHAR(100),
    witness_signature TEXT,
    ip_address VARCHAR(45),
    device_info TEXT,

    -- Status
    is_valid BOOLEAN DEFAULT true,
    revoked_at TIMESTAMP,
    revocation_reason TEXT,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id)
);

-- Consent templates
CREATE TABLE consent_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(100) NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    template_content TEXT NOT NULL,
    service_id UUID REFERENCES services(service_id),
    package_id UUID REFERENCES packages(package_id),
    is_mandatory BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Before/After photos
CREATE TABLE procedure_photos (
    photo_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    session_id UUID NOT NULL REFERENCES procedure_sessions(session_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    -- Photo info
    photo_type VARCHAR(20) NOT NULL, -- before, during, after
    photo_category VARCHAR(50), -- front, left, right, closeup

    -- Storage (encrypted)
    photo_data BYTEA NOT NULL,
    thumbnail_data BYTEA,
    encryption_key_id UUID NOT NULL,

    -- Metadata
    file_name VARCHAR(255),
    mime_type VARCHAR(50),
    file_size INT,

    -- Capture info
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    captured_by UUID REFERENCES staff(staff_id),

    -- Notes
    notes TEXT,

    -- Consent
    patient_consent_given BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session consumables used
CREATE TABLE session_consumables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES procedure_sessions(session_id),
    medicine_id UUID NOT NULL REFERENCES medicines(medicine_id),
    batch_id UUID REFERENCES inventory(inventory_id),
    quantity_used DECIMAL(10,3),
    unit_of_measure VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id)
);

-- Indexes
CREATE INDEX idx_procedure_orders_patient ON procedure_orders(patient_id);
CREATE INDEX idx_procedure_orders_status ON procedure_orders(status);
CREATE INDEX idx_procedure_sessions_order ON procedure_sessions(order_id);
CREATE INDEX idx_procedure_sessions_date ON procedure_sessions(scheduled_date);
CREATE INDEX idx_consent_forms_session ON consent_forms(session_id);
CREATE INDEX idx_procedure_photos_session ON procedure_photos(session_id);
```

### 7.3 Files to Create

```
app/models/procedure.py
app/views/procedure.py
app/api/routes/procedure_api.py
app/services/procedure_service.py
app/services/consent_service.py
app/forms/procedure_forms.py
app/config/modules/procedure_config.py
app/templates/procedures/order.html
app/templates/procedures/schedule.html
app/templates/procedures/session.html
app/templates/procedures/consent.html
app/templates/procedures/photos.html
app/templates/procedures/progress.html
app/static/js/components/signature_pad.js
app/static/js/components/photo_capture.js
app/static/js/components/session_tracker.js
migrations/20251204_create_procedure_tables.sql
```

---

## 8. Phase 5: Patient Self-Service Portal

### 8.1 Overview
PWA for patient self-service with WhatsApp integration.

### 8.2 Features

1. **Authentication**
   - Phone OTP login
   - Remember device

2. **Appointments**
   - View upcoming appointments
   - Book new appointments
   - Reschedule/Cancel
   - Check-in via QR code

3. **Medical Records**
   - Prescription history
   - Consultation summaries
   - Treatment progress

4. **Documents**
   - Download invoices
   - Download prescriptions

5. **Feedback**
   - Post-visit survey
   - Rating & reviews

### 8.3 WhatsApp Integration

```
Appointment Reminder (24h before):
━━━━━━━━━━━━━━━━━━━━━━━━━
🏥 *Skinspire Clinic*

Hi {patient_name},

Your appointment is tomorrow:
📅 Date: {date}
⏰ Time: {time}
👨‍⚕️ Doctor: Dr. {doctor_name}

Reply:
1️⃣ Confirm
2️⃣ Reschedule
3️⃣ Cancel
━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 8.4 Files to Create

```
app/views/patient_portal.py
app/api/routes/patient_portal_api.py
app/services/notification_service.py
app/services/whatsapp_service.py
app/templates/patient_portal/login.html
app/templates/patient_portal/dashboard.html
app/templates/patient_portal/appointments.html
app/templates/patient_portal/records.html
app/templates/patient_portal/feedback.html
app/static/js/patient_portal/
app/static/manifest.json
app/static/service-worker.js
```

---

## 9. Phase 6: EMR Compliance & Patient History

### 9.1 Overview
ABDM-ready EMR structure with FHIR compatibility.

### 9.2 Database Schema

```sql
-- Patient medical history
CREATE TABLE patient_medical_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    condition_type VARCHAR(50) NOT NULL,
    -- chronic, allergy, surgery, family_history, social_history

    condition_name VARCHAR(200) NOT NULL,
    condition_code VARCHAR(20), -- ICD-10 code

    onset_date DATE,
    resolution_date DATE,
    is_current BOOLEAN DEFAULT true,

    severity VARCHAR(20), -- mild, moderate, severe
    notes TEXT,

    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recorded_by UUID REFERENCES staff(staff_id),
    source VARCHAR(50) -- self_reported, consultation, external
);

-- Patient allergies
CREATE TABLE patient_allergies (
    allergy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    allergen_type VARCHAR(50) NOT NULL,
    -- drug, food, environmental, latex, other

    allergen_name VARCHAR(200) NOT NULL,
    allergen_code VARCHAR(50), -- RxNorm for drugs

    reaction_type VARCHAR(100),
    reaction_severity VARCHAR(20), -- mild, moderate, severe, life_threatening

    onset_date DATE,
    is_active BOOLEAN DEFAULT true,

    notes TEXT,
    verified_by UUID REFERENCES staff(staff_id),
    verified_at TIMESTAMP,

    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recorded_by UUID REFERENCES staff(staff_id)
);

-- Health records (FHIR Bundle)
CREATE TABLE health_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    record_type VARCHAR(50) NOT NULL,
    -- prescription, diagnostic_report, consultation_note, discharge_summary

    -- FHIR structure
    fhir_resource_type VARCHAR(50),
    fhir_bundle JSONB,

    -- Source reference
    source_type VARCHAR(50), -- consultation, procedure, external
    source_id UUID,

    -- ABDM fields
    abha_id VARCHAR(20),
    hip_id VARCHAR(50), -- Health Information Provider ID
    is_linked_to_abdm BOOLEAN DEFAULT false,

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id)
);

-- Patient documents
CREATE TABLE patient_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    document_type VARCHAR(50) NOT NULL,
    -- lab_report, imaging, external_prescription, referral, other

    document_name VARCHAR(255) NOT NULL,
    document_data BYTEA NOT NULL, -- Encrypted
    encryption_key_id UUID NOT NULL,

    file_size INT,
    mime_type VARCHAR(50),

    -- Metadata
    document_date DATE,
    source VARCHAR(100), -- lab name, hospital name
    notes TEXT,

    -- Upload info
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by UUID REFERENCES users(user_id),

    -- Verification
    is_verified BOOLEAN DEFAULT false,
    verified_by UUID REFERENCES staff(staff_id),
    verified_at TIMESTAMP
);

-- Health record access log (compliance)
CREATE TABLE health_record_access_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    record_type VARCHAR(50) NOT NULL,
    record_id UUID NOT NULL,
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    accessed_by UUID REFERENCES users(user_id),
    access_type VARCHAR(20) NOT NULL, -- view, download, print, export, share

    access_reason TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,

    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add ABHA ID to patients table
ALTER TABLE patients ADD COLUMN IF NOT EXISTS abha_id VARCHAR(20);
ALTER TABLE patients ADD COLUMN IF NOT EXISTS abha_address VARCHAR(100);
CREATE INDEX IF NOT EXISTS idx_patients_abha ON patients(abha_id);
```

### 9.3 Files to Create

```
app/models/emr.py
app/views/emr.py
app/api/routes/emr_api.py
app/services/emr_service.py
app/services/fhir_service.py
app/templates/emr/patient_timeline.html
app/templates/emr/medical_history.html
app/templates/emr/allergies.html
app/templates/emr/documents.html
migrations/20251204_create_emr_tables.sql
```

---

## 10. Phase 7: Doctor Dashboard

### 10.1 Features

1. **Today's Queue**
   - Waiting patients count
   - Current patient
   - Quick actions

2. **Patient Lookup**
   - Search by name/phone
   - Quick history view

3. **Pending Actions**
   - Unsigned prescriptions
   - Unverified AI notes
   - Follow-up reminders

4. **Statistics**
   - Daily/weekly patients
   - Revenue generated
   - Procedure sessions

### 10.2 Files to Create

```
app/views/doctor_dashboard.py
app/api/routes/dashboard_api.py
app/templates/dashboards/doctor.html
app/static/js/components/doctor_dashboard.js
```

---

## 11. Privacy & Security Framework

### 11.1 Data Classification

| Data Type | Classification | Encryption | Retention |
|-----------|---------------|------------|-----------|
| Patient PII | Confidential | AES-256 | Permanent |
| Audio recordings | Sensitive | AES-256 | 1 year |
| Transcripts | Sensitive | AES-256 | 7 years |
| Medical history | Sensitive | AES-256 | Permanent |
| Consent forms | Legal | AES-256 | 10 years |
| Photos | Sensitive | AES-256 | 7 years |

### 11.2 Compliance Checklist

- [ ] DPDPA 2023 consent forms
- [ ] NMC recording consent
- [ ] Data retention policy
- [ ] Right to deletion implementation
- [ ] Access audit logging
- [ ] Encryption at rest
- [ ] Encryption in transit (TLS 1.3)
- [ ] ABDM-ready structure

### 11.3 Patient Rights

1. **Right to Access** - View all their data
2. **Right to Correction** - Request corrections
3. **Right to Deletion** - Request data deletion
4. **Right to Portability** - Export data in FHIR format
5. **Right to Withdraw Consent** - Opt-out of recordings

---

## 12. Database Schema

### 12.1 New Tables Summary

| Table | Phase | Purpose |
|-------|-------|---------|
| doctor_schedules | 1 | Doctor availability |
| appointment_slots | 1 | Generated time slots |
| appointment_types | 1 | Appointment categories |
| appointments | 1 | Booked appointments |
| appointment_status_history | 1 | Status audit trail |
| rooms | 1 | Room master (procedure, OT, etc.) |
| room_slots | 1 | Room availability calendar |
| service_resource_requirements | 1 | Resource requirements per service |
| appointment_resources | 1 | Allocated resources per appointment |
| voice_session_tokens | 2 | Anonymization tokens |
| pii_redaction_patterns | 2 | PII patterns |
| consultation_recordings | 2 | Encrypted audio |
| consultation_transcripts | 2 | AI transcripts |
| encryption_keys | 2 | Key management |
| voice_ai_usage_log | 2 | Cost tracking |
| consultations | 3 | Consultation records |
| patient_vitals | 3 | Vital signs |
| consultation_notes | 3 | SOAP notes |
| diagnosis_codes | 3 | ICD-10 codes |
| consultation_diagnoses | 3 | Patient diagnoses |
| prescriptions | 3 | Prescription headers |
| prescription_items | 3 | Prescription details |
| procedure_orders | 4 | Procedure orders |
| procedure_sessions | 4 | Session tracking |
| consent_forms | 4 | Digital consent |
| consent_templates | 4 | Consent templates |
| procedure_photos | 4 | Before/after photos |
| session_consumables | 4 | Consumables used |
| patient_medical_history | 6 | Medical history |
| patient_allergies | 6 | Allergy tracking |
| health_records | 6 | FHIR records |
| patient_documents | 6 | Document uploads |
| health_record_access_log | 6 | Access audit |

---

## 13. API Specifications

### 13.1 API Summary

| Module | Endpoints | Auth Required |
|--------|-----------|---------------|
| Appointments | 12 | Yes |
| Voice AI | 8 | Yes |
| Consultations | 15 | Yes |
| Procedures | 10 | Yes |
| Patient Portal | 12 | Yes (Patient) |
| EMR | 8 | Yes |
| Dashboard | 5 | Yes (Doctor) |

---

## 14. Cost Analysis

### 14.1 One-Time Costs

| Item | Cost (INR) |
|------|------------|
| Android Tablet (Samsung Tab A8) | 15,000 |
| Tablet Wall Mount | 1,500 |
| USB Conference Microphone | 3,000 |
| **Total** | **19,500** |

### 14.2 Monthly Running Costs

| Item | Cost (INR) | Notes |
|------|------------|-------|
| Deepgram API | 2,700 | 375 consultations × 20 min |
| Claude API | 300 | Note generation |
| WhatsApp Business | 1,000 | Notifications |
| **Total** | **4,000** | ~₹10/consultation |

### 14.3 Cost Comparison

| Solution | Monthly Cost |
|----------|-------------|
| Human Transcriptionist | ₹25,000-40,000 |
| Nuance DAX | ₹55,000+ |
| Suki AI | ₹35,000+ |
| **Intelli-Clinic** | **₹4,000** |

---

## 15. Timeline & Milestones

### 15.1 Phase Timeline

| Phase | Module | Duration | Start | End |
|-------|--------|----------|-------|-----|
| 1 | Appointments | 2 weeks | Week 1 | Week 2 |
| 2 | Voice AI | 2 weeks | Week 2 | Week 3 |
| 3 | Consultations | 2 weeks | Week 3 | Week 4 |
| 4 | Procedures | 2 weeks | Week 4 | Week 5 |
| 5 | Patient Portal | 1 week | Week 5 | Week 6 |
| 6 | EMR | 1 week | Week 6 | Week 7 |
| 7 | Dashboard | 1 week | Week 7 | Week 8 |

### 15.2 Milestones

- **M1 (Week 2)**: Appointment booking live
- **M2 (Week 3)**: Voice AI MVP working
- **M3 (Week 4)**: Full consultation workflow
- **M4 (Week 5)**: Procedure tracking complete
- **M5 (Week 6)**: Patient portal live
- **M6 (Week 7)**: EMR compliance ready
- **M7 (Week 8)**: Full system integration

---

## Appendix A: File Structure

```
app/
├── models/
│   ├── appointment.py       # Phase 1
│   ├── voice_ai.py          # Phase 2
│   ├── consultation.py      # Phase 3
│   ├── procedure.py         # Phase 4
│   └── emr.py               # Phase 6
├── views/
│   ├── appointment.py       # Phase 1
│   ├── consultation.py      # Phase 3
│   ├── procedure.py         # Phase 4
│   ├── patient_portal.py    # Phase 5
│   ├── emr.py               # Phase 6
│   └── doctor_dashboard.py  # Phase 7
├── api/routes/
│   ├── appointment_api.py   # Phase 1
│   ├── voice_ai_api.py      # Phase 2
│   ├── consultation_api.py  # Phase 3
│   ├── procedure_api.py     # Phase 4
│   ├── patient_portal_api.py# Phase 5
│   ├── emr_api.py           # Phase 6
│   └── dashboard_api.py     # Phase 7
├── services/
│   ├── appointment_service.py
│   ├── slot_generator_service.py
│   ├── voice_ai_service.py
│   ├── privacy_service.py
│   ├── deepgram_service.py
│   ├── encryption_service.py
│   ├── consultation_service.py
│   ├── prescription_service.py
│   ├── procedure_service.py
│   ├── consent_service.py
│   ├── notification_service.py
│   ├── whatsapp_service.py
│   ├── emr_service.py
│   └── fhir_service.py
├── templates/
│   ├── appointments/
│   ├── consultations/
│   ├── procedures/
│   ├── patient_portal/
│   ├── emr/
│   ├── dashboards/
│   └── voice_ai/
└── static/js/components/
    ├── appointment_calendar.js
    ├── slot_picker.js
    ├── voice_recorder.js
    ├── transcript_viewer.js
    ├── consultation_workflow.js
    ├── prescription_builder.js
    ├── signature_pad.js
    ├── photo_capture.js
    └── doctor_dashboard.js
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 4, 2025 | Dev Team | Initial document |
| 1.1 | Dec 5, 2025 | Dev Team | Added Resource Management System (Section 4.8): rooms, room_slots, service_resource_requirements, appointment_resources tables; resource allocation API endpoints; service-based slot duration; booking workflow with room/therapist selection; approval workflow design |

---

*End of Implementation Plan Document*
