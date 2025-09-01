"""
Universal View Engine for Skinspire HMS
Core view engine that provides universal functionality for all entities
"""

# from .universal_view_engine import UniversalViewEngine
from .universal_components import UniversalListService, UniversalDetailService
from .data_assembler import EnhancedUniversalDataAssembler as DataAssembler

# Global view engine instance
universal_view_engine = UniversalViewEngine()

__all__ = ['universal_view_engine', 'UniversalViewEngine', 'UniversalListService', 'UniversalDetailService', 'DataAssembler']