# tests/test_frontend/test_responsive.py
# pytest tests/test_frontend/test_responsive.py -v

import pytest
import socket
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture
def selenium(request):
    """Selenium webdriver fixture with Chrome"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    yield driver
    driver.quit()

@pytest.fixture
def live_server(app):
    """Live server fixture"""
    from threading import Thread
    import socket
    
    port = get_free_port()
    server = Thread(target=app.run, kwargs={'port': port, 'debug': False})
    server.daemon = True
    server.start()
    yield f"http://localhost:{port}"
    
def get_free_port():
    """Get a free port on localhost"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def test_login_responsive(selenium, live_server):
    """Test login page responsive design"""
    # Desktop view
    selenium.set_window_size(1200, 800)
    selenium.get(f"{live_server}/login")
    
    # Check elements in desktop view
    assert selenium.find_element(By.TAG_NAME, "form").is_displayed()
    
    # Mobile view
    selenium.set_window_size(375, 667)
    selenium.get(f"{live_server}/login")
    
    # Verify form still displays properly
    assert selenium.find_element(By.TAG_NAME, "form").is_displayed()