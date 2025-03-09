# app/security/audit/audit_logger.py

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from ...models import Base
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
import uuid

class AuditLog(Base):
    """Audit log entry model"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    hospital_id = Column(String, nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(String)
    user_id = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    status = Column(String(20), default='success')
    error_details = Column(JSON)

class AuditLogger:
    """Handles audit logging and retrieval"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def log(self, hospital_id: str, action: str, user_id: str,
            details: Dict[str, Any], request_info: Optional[Dict] = None,
            entity_type: Optional[str] = None,
            entity_id: Optional[str] = None,
            status: str = 'success',
            error_details: Optional[Dict] = None) -> None:
        """Create an audit log entry"""
        try:
            log_entry = AuditLog(
                hospital_id=hospital_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                details=details,
                ip_address=request_info.get('ip_address') if request_info else None,
                user_agent=request_info.get('user_agent') if request_info else None,
                status=status,
                error_details=error_details
            )
            
            self.session.add(log_entry)
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            # Log the failure to a backup location
            self._log_failure(hospital_id, action, str(e))
            raise
    
    def _log_failure(self, hospital_id: str, action: str, error: str) -> None:
        """Backup logging when primary logging fails"""
        timestamp = datetime.now(timezone.utc).isoformat()
        failure_log = {
            'timestamp': timestamp,
            'hospital_id': hospital_id,
            'action': action,
            'error': error
        }
        
        try:
            # Write to a separate table or file
            with open('audit_failures.log', 'a') as f:
                f.write(json.dumps(failure_log) + '\n')
        except:
            pass  # Last resort - we tried our best
    
    def get_logs(self, hospital_id: str, filters: Dict = None,
                 page: int = 1, per_page: int = 50) -> Dict:
        """Retrieve audit logs with filtering and pagination"""
        try:
            query = self.session.query(AuditLog).filter(
                AuditLog.hospital_id == hospital_id
            )
            
            # Apply filters
            if filters:
                if filters.get('action'):
                    query = query.filter(AuditLog.action == filters['action'])
                if filters.get('user_id'):
                    query = query.filter(AuditLog.user_id == filters['user_id'])
                if filters.get('entity_type'):
                    query = query.filter(AuditLog.entity_type == filters['entity_type'])
                if filters.get('start_date'):
                    query = query.filter(AuditLog.timestamp >= filters['start_date'])
                if filters.get('end_date'):
                    query = query.filter(AuditLog.timestamp <= filters['end_date'])
                if filters.get('status'):
                    query = query.filter(AuditLog.status == filters['status'])
            
            # Count total results
            total = query.count()
            
            # Apply pagination
            logs = query.order_by(AuditLog.timestamp.desc())\
                       .offset((page - 1) * per_page)\
                       .limit(per_page)\
                       .all()
            
            return {
                'total': total,
                'page': page,
                'per_page': per_page,
                'logs': [{
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'action': log.action,
                    'user_id': log.user_id,
                    'entity_type': log.entity_type,
                    'entity_id': log.entity_id,
                    'details': log.details,
                    'status': log.status,
                    'error_details': log.error_details,
                    'ip_address': log.ip_address,
                    'user_agent': log.user_agent
                } for log in logs]
            }
            
        except Exception as e:
            raise ValueError(f"Failed to retrieve audit logs: {str(e)}")
    
    def get_audit_summary(self, hospital_id: str, 
                         start_date: datetime) -> Dict:
        """Get summary statistics of audit logs"""
        try:
            # Get action counts
            action_counts = self.session.query(
                AuditLog.action,
                text('count(*) as count')
            ).filter(
                AuditLog.hospital_id == hospital_id,
                AuditLog.timestamp >= start_date
            ).group_by(
                AuditLog.action
            ).all()
            
            # Get user activity
            user_activity = self.session.query(
                AuditLog.user_id,
                text('count(*) as count')
            ).filter(
                AuditLog.hospital_id == hospital_id,
                AuditLog.timestamp >= start_date
            ).group_by(
                AuditLog.user_id
            ).all()
            
            # Get error counts
            error_count = self.session.query(AuditLog).filter(
                AuditLog.hospital_id == hospital_id,
                AuditLog.timestamp >= start_date,
                AuditLog.status == 'error'
            ).count()
            
            return {
                'action_summary': {
                    action: count for action, count in action_counts
                },
                'user_activity': {
                    user_id: count for user_id, count in user_activity
                },
                'total_errors': error_count,
                'period_start': start_date.isoformat(),
                'period_end': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            raise ValueError(f"Failed to generate audit summary: {str(e)}")
    
    def cleanup_old_logs(self, hospital_id: str, 
                        retention_days: int) -> Dict:
        """Clean up audit logs older than retention period"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            # Count logs to be deleted
            count = self.session.query(AuditLog).filter(
                AuditLog.hospital_id == hospital_id,
                AuditLog.timestamp < cutoff_date
            ).count()
            
            # Delete logs
            self.session.query(AuditLog).filter(
                AuditLog.hospital_id == hospital_id,
                AuditLog.timestamp < cutoff_date
            ).delete()
            
            self.session.commit()
            
            return {
                'status': 'success',
                'deleted_count': count,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Failed to cleanup old logs: {str(e)}")
    
    def export_logs(self, hospital_id: str, 
                    filters: Dict = None) -> bytes:
        """Export audit logs to CSV format"""
        try:
            import csv
            from io import StringIO
            
            # Get filtered logs
            logs_data = self.get_logs(
                hospital_id,
                filters,
                page=1,
                per_page=1000000  # Large number to get all logs
            )
            
            output = StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    'timestamp', 'action', 'user_id', 
                    'entity_type', 'entity_id', 'details',
                    'status', 'ip_address', 'user_agent'
                ]
            )
            
            writer.writeheader()
            for log in logs_data['logs']:
                # Flatten details to string
                log['details'] = json.dumps(log['details'])
                writer.writerow(log)
            
            return output.getvalue().encode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Failed to export audit logs: {str(e)}")