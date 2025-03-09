# app/models/master.py

from sqlalchemy import Column, String, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from .base import Base, TimestampMixin, TenantMixin, SoftDeleteMixin, generate_uuid

class Hospital(Base, TimestampMixin, SoftDeleteMixin):
    """Hospital (Tenant) level configuration"""
    __tablename__ = 'hospitals'

    hospital_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    license_no = Column(String(50), unique=True)
    address = Column(JSONB)
    contact_details = Column(JSONB)
    settings = Column(JSONB)
    encryption_enabled = Column(Boolean, default=False)
    encryption_key = Column(String(255))
    encryption_config = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)

    # Relationships
    branches = relationship("Branch", back_populates="hospital", cascade="all, delete-orphan")
    staff = relationship("Staff", back_populates="hospital")
    patients = relationship("Patient", back_populates="hospital")
    users = relationship("User", back_populates="hospital")
    roles = relationship("RoleMaster", back_populates="hospital")

class Branch(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Branch level configuration"""
    __tablename__ = 'branches'

    branch_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(JSONB)
    contact_details = Column(JSONB)
    settings = Column(JSONB)
    is_active = Column(Boolean, default=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="branches")
    staff = relationship("Staff", back_populates="branch")
    patients = relationship("Patient", back_populates="branch")

class Staff(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Staff member information"""
    __tablename__ = 'staff'

    staff_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    employee_code = Column(String(20), unique=True)
    title = Column(String(10))
    specialization = Column(String(100))
    personal_info = Column(JSONB, nullable=False)  # name, dob, gender, etc.
    contact_info = Column(JSONB, nullable=False)   # email, phone, address
    professional_info = Column(JSONB)  # qualifications, certifications
    employment_info = Column(JSONB)    # join date, designation, etc.
    documents = Column(JSONB)          # ID proofs, certificates
    is_active = Column(Boolean, default=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="staff")
    branch = relationship("Branch", back_populates="staff")

    @hybrid_property
    def full_name(self):
        return f"{self.personal_info.get('first_name', '')} {self.personal_info.get('last_name', '')}"

class Patient(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Patient information"""
    __tablename__ = 'patients'

    patient_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    mrn = Column(String(20), unique=True)
    title = Column(String(10))
    blood_group = Column(String(5))
    personal_info = Column(JSONB, nullable=False)  # name, dob, gender, marital status
    contact_info = Column(JSONB, nullable=False)   # email, phone, address
    medical_info = Column(Text)                    # Encrypted medical history
    emergency_contact = Column(JSONB)              # name, relation, contact
    documents = Column(JSONB)                      # ID proofs, previous records
    preferences = Column(JSONB)                    # language, communication preferences
    is_active = Column(Boolean, default=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="patients")
    branch = relationship("Branch", back_populates="patients")

    @hybrid_property
    def full_name(self):
        return f"{self.personal_info.get('first_name', '')} {self.personal_info.get('last_name', '')}"