# app/services/medicine_service.py
# Business logic for medicine pricing, MRP updates, and validation

from typing import Dict, Any, Optional, List
from datetime import date, datetime
from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.models.master import Medicine
from app.utils.filters import currencyformat
import logging

logger = logging.getLogger(__name__)


class MedicineService:
    """Service class for medicine business logic"""
    
    @staticmethod
    def format_medicine_price(medicine: Medicine, price_type: str = 'mrp') -> str:
        """
        Format medicine price using existing currency formatter
        
        Args:
            medicine: Medicine object
            price_type: 'mrp', 'selling_price', 'last_purchase_price', 'cost_price'
        """
        price_value = getattr(medicine, price_type, 0)
        if not price_value:
            return "N/A"
        
        # Use existing currencyformat from filters.py
        return currencyformat(price_value, medicine.currency_code or 'INR')
    
    @staticmethod
    def get_currency_symbol(currency_code: str = 'INR') -> str:
        """Get currency symbol for a currency code"""
        symbols = {
            'INR': '₹',
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'AED': 'د.إ',
            'SAR': '﷼',
            'SGD': 'S$',
            'MYR': 'RM',
            'AUD': 'A$',
            'CAD': 'C$'
        }
        return symbols.get(currency_code, '')
    
    @staticmethod
    def update_medicine_mrp(
        session: Session,
        medicine_id: uuid.UUID,
        new_mrp: Decimal,
        effective_date: Optional[date] = None,
        source: str = 'MANUAL',
        reference_id: Optional[uuid.UUID] = None,
        update_selling_price: bool = False
    ) -> Dict[str, Any]:
        """
        Update medicine MRP with proper tracking
        
        Args:
            session: Database session
            medicine_id: Medicine UUID
            new_mrp: New MRP value
            effective_date: Date when MRP becomes effective
            source: Source of update (INVOICE, MANUAL, IMPORT, PO)
            reference_id: Reference document ID
            update_selling_price: Whether to update selling price too
            
        Returns:
            Dict with update status and details
        """
        try:
            medicine = session.query(Medicine).filter_by(
                medicine_id=medicine_id
            ).first()
            
            if not medicine:
                return {
                    'success': False,
                    'error': 'Medicine not found'
                }
            
            old_mrp = medicine.mrp
            
            # Check if MRP is actually changing
            if old_mrp and float(new_mrp) == float(old_mrp):
                return {
                    'success': True,
                    'message': 'MRP unchanged',
                    'mrp': float(old_mrp)
                }
            
            # Update MRP
            medicine.previous_mrp = old_mrp
            medicine.mrp = new_mrp
            medicine.mrp_effective_date = effective_date or date.today()
            
            # Update selling price if requested or if it was same as old MRP
            if update_selling_price or (medicine.selling_price == old_mrp):
                medicine.selling_price = new_mrp
            
            session.flush()
            
            logger.info(f"MRP updated for {medicine.medicine_name}: "
                       f"{old_mrp} -> {new_mrp} (Source: {source})")
            
            return {
                'success': True,
                'medicine_id': str(medicine_id),
                'medicine_name': medicine.medicine_name,
                'old_mrp': float(old_mrp) if old_mrp else 0,
                'new_mrp': float(new_mrp),
                'effective_date': medicine.mrp_effective_date.isoformat(),
                'source': source
            }
            
        except Exception as e:
            logger.error(f"Error updating medicine MRP: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def update_purchase_price(
        session: Session,
        medicine_id: uuid.UUID,
        new_price: Decimal,
        update_cost_price: bool = True
    ) -> bool:
        """Update last purchase price for a medicine"""
        try:
            medicine = session.query(Medicine).filter_by(
                medicine_id=medicine_id
            ).first()
            
            if not medicine:
                return False
            
            if new_price and float(new_price) > 0:
                medicine.last_purchase_price = new_price
                
                # Update cost price if requested
                if update_cost_price:
                    if not medicine.cost_price:
                        medicine.cost_price = new_price
                    else:
                        # Simple average
                        medicine.cost_price = (float(medicine.cost_price) + float(new_price)) / 2
                
                session.flush()
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error updating purchase price: {str(e)}")
            return False
    
    @staticmethod
    def validate_purchase_price(
        medicine: Medicine,
        purchase_price: Decimal,
        gst_rate: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Validate purchase price against MRP
        
        Returns:
            Dict with validation results
        """
        result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'margin_percentage': 0
        }
        
        if not medicine.mrp:
            result['warnings'].append("No MRP set for validation")
            return result
        
        gst_rate = gst_rate or medicine.gst_rate or 0
        landed_cost = float(purchase_price) * (1 + float(gst_rate) / 100)
        
        # Check if landed cost exceeds MRP
        if landed_cost > float(medicine.mrp):
            result['valid'] = False
            result['errors'].append(
                f"Purchase price + GST ({currencyformat(landed_cost, medicine.currency_code)}) "
                f"exceeds MRP ({currencyformat(medicine.mrp, medicine.currency_code)})"
            )
        
        # Calculate margin
        if float(medicine.mrp) > 0:
            margin_percent = ((float(medicine.mrp) - landed_cost) / float(medicine.mrp)) * 100
            result['margin_percentage'] = round(margin_percent, 2)
            
            if margin_percent < 10 and margin_percent >= 0:
                result['warnings'].append(f"Low margin: {margin_percent:.1f}%")
            elif margin_percent < 0:
                result['errors'].append("Negative margin - selling at loss")
                result['valid'] = False
        
        return result
    
    @staticmethod
    def calculate_margin(medicine: Medicine) -> Dict[str, float]:
        """Calculate various margin metrics for a medicine"""
        result = {
            'margin_amount': 0,
            'margin_percentage': 0,
            'markup_percentage': 0
        }
        
        if not medicine.mrp or not medicine.last_purchase_price:
            return result
        
        mrp = float(medicine.mrp)
        purchase_price = float(medicine.last_purchase_price)
        
        # Margin amount
        result['margin_amount'] = mrp - purchase_price
        
        # Margin percentage (on MRP)
        if mrp > 0:
            result['margin_percentage'] = ((mrp - purchase_price) / mrp) * 100
        
        # Markup percentage (on cost)
        if purchase_price > 0:
            result['markup_percentage'] = ((mrp - purchase_price) / purchase_price) * 100
        
        return result
    
    @staticmethod
    def get_medicine_with_prices(
        session: Session,
        medicine_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get medicine with all formatted prices
        
        Returns:
            Dict with medicine data and formatted prices
        """
        medicine = session.query(Medicine).filter_by(
            medicine_id=medicine_id
        ).first()
        
        if not medicine:
            return None
        
        # Get margin calculations
        margins = MedicineService.calculate_margin(medicine)
        
        return {
            'medicine_id': str(medicine.medicine_id),
            'medicine_name': medicine.medicine_name,
            'generic_name': medicine.generic_name,
            'currency_code': medicine.currency_code or 'INR',
            'currency_symbol': MedicineService.get_currency_symbol(medicine.currency_code),
            
            # Raw values
            'mrp': float(medicine.mrp or 0),
            'selling_price': float(medicine.selling_price or 0),
            'cost_price': float(medicine.cost_price or 0),
            'last_purchase_price': float(medicine.last_purchase_price or 0),
            
            # Formatted values
            'formatted_mrp': MedicineService.format_medicine_price(medicine, 'mrp'),
            'formatted_selling_price': MedicineService.format_medicine_price(medicine, 'selling_price'),
            'formatted_cost_price': MedicineService.format_medicine_price(medicine, 'cost_price'),
            'formatted_last_purchase_price': MedicineService.format_medicine_price(medicine, 'last_purchase_price'),
            
            # Margins
            'margin_amount': margins['margin_amount'],
            'margin_percentage': round(margins['margin_percentage'], 2),
            'markup_percentage': round(margins['markup_percentage'], 2),
            
            # Dates
            'mrp_effective_date': medicine.mrp_effective_date.isoformat() if medicine.mrp_effective_date else None,
            
            # Other info
            'gst_rate': float(medicine.gst_rate or 0),
            'hsn_code': medicine.hsn_code
        }
    
    @staticmethod
    def bulk_update_mrp(
        session: Session,
        updates: List[Dict[str, Any]],
        source: str = 'BULK_IMPORT'
    ) -> Dict[str, Any]:
        """
        Bulk update MRP for multiple medicines
        
        Args:
            updates: List of dicts with medicine_id and new_mrp
            source: Source of update
            
        Returns:
            Summary of updates
        """
        success_count = 0
        error_count = 0
        errors = []
        
        for update in updates:
            try:
                result = MedicineService.update_medicine_mrp(
                    session=session,
                    medicine_id=update['medicine_id'],
                    new_mrp=update['new_mrp'],
                    effective_date=update.get('effective_date'),
                    source=source
                )
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(result.get('error', 'Unknown error'))
                    
            except Exception as e:
                error_count += 1
                errors.append(str(e))
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors,
            'total': len(updates)
        }