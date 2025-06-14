#!/usr/bin/env python3
"""
Test Unicode logging with currency support
"""

def test_unicode_currency():
    from app.utils.unicode_logging import setup_unicode_logging, get_unicode_safe_logger, format_indian_currency
    
    # Setup Unicode logging
    setup_unicode_logging()
    
    # Test with safe logger
    logger = get_unicode_safe_logger('test')
    
    print("Testing Unicode logging with currency support...\n")
    
    # Test emoji symbols
    logger.info("🔍 Testing search emoji")
    logger.info("✅ Testing success emoji") 
    logger.error("❌ Testing error emoji")
    
    # Test currency symbols
    logger.info("💰 Currency Testing:")
    logger.info(f"₹ Invoice amount: {format_indian_currency(2478.00)}")
    logger.info("$ USD equivalent: $29.74")
    logger.info("€ EUR equivalent: €27.45")
    
    # Test medical symbols
    logger.info("🏥 Medical symbols:")
    logger.info("💊 Medicine: Paracetamol 500mg")
    logger.info("🩺 Checkup: Patient examination complete")
    logger.info("👨‍⚕️ Doctor: Dr. Smith consultation")
    
    print("Unicode and currency test completed!")

if __name__ == "__main__":
    test_unicode_currency()