"""
Package Service
Minimal service for package autocomplete in filters

Handles:
- Package search/autocomplete for dropdown filters
- Basic package queries

Version: 1.0
Created: 2025-11-13
"""

import logging
import uuid
from typing import Dict, List, Optional, Any

from sqlalchemy import and_, or_, cast, String
from app.engine.universal_entity_service import UniversalEntityService
from app.models.master import Package
from app.services.database_service import get_db_session

logger = logging.getLogger(__name__)


class PackageService(UniversalEntityService):
    """
    Service for Package entity operations
    Extends Universal Entity Service for consistent autocomplete behavior
    """

    def __init__(self):
        super().__init__('packages', Package)
        self.entity_name = 'packages'
        self.model = Package

    def autocomplete_search(
        self,
        search_term: str,
        hospital_id: uuid.UUID,
        branch_id: Optional[uuid.UUID] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search packages for autocomplete dropdown

        Args:
            search_term: Search query string
            hospital_id: Hospital context
            branch_id: Optional branch filter
            limit: Maximum results to return

        Returns:
            List of package dictionaries with id, label, and package_name
        """
        try:
            with get_db_session() as session:
                # Base query - active packages for this hospital
                query = session.query(Package).filter(
                    and_(
                        Package.hospital_id == hospital_id,
                        Package.is_deleted == False,
                        Package.status == 'active'
                    )
                )

                # Apply search filter if provided
                if search_term:
                    query = query.filter(
                        Package.package_name.ilike(f'%{search_term}%')
                    )

                # Order by name and limit results
                query = query.order_by(Package.package_name).limit(limit)

                # Execute query
                packages = query.all()

                # Format results for autocomplete
                results = []
                for package in packages:
                    results.append({
                        'value': str(package.package_id),  # UUID for filtering
                        'label': package.package_name,  # Display name
                        'package_name': package.package_name,  # For filtering
                        'package_id': str(package.package_id),  # For reference
                        'price': float(package.price) if package.price else 0,
                        'status': package.status
                    })

                logger.info(f"Package autocomplete search: '{search_term}' returned {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Error in package autocomplete search: {str(e)}")
            return []
