import pytest
import time
import requests
from typing import Generator

@pytest.fixture(scope="session")
def wait_for_services() -> Generator[None, None, None]:
    client_url = "http://localhost:8080/health"
    server_url = "http://localhost:8081/health"
    max_retries = 30
    retry_delay = 1
    
    for i in range(max_retries):
        try:
            client_response = requests.get(client_url, timeout=5)
            server_response = requests.get(server_url, timeout=5)
            
            if client_response.status_code == 200 and server_response.status_code == 200:
                print("\nServices are ready!")
                break
        except requests.exceptions.RequestException:
            pass
        
        if i < max_retries - 1:
            print(f"\rWaiting for services to start... ({i+1}/{max_retries})", end="", flush=True)
            time.sleep(retry_delay)
    else:
        pytest.fail("Services failed to start within timeout period")
    
    yield
    
@pytest.fixture
def base_url():
    return "http://localhost:8080"

@pytest.fixture
def server_url():
    return "http://localhost:8081"