import pytest
import requests
import json
from typing import Dict, Any

class TestHealthEndpoints:
    def test_client_health(self, wait_for_services, base_url):
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "server_status" in data
        assert data["server_status"]["status"] == "healthy"
    
    def test_server_health(self, wait_for_services, server_url):
        response = requests.get(f"{server_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "bedrock_available" in data
        assert isinstance(data["bedrock_available"], bool)

class TestEmployeeEndpoints:
    def test_get_all_employees(self, wait_for_services, base_url):
        response = requests.get(f"{base_url}/employees")
        assert response.status_code == 200
        
        employees = response.json()
        assert isinstance(employees, list)
        assert len(employees) == 8
        
        for employee in employees:
            assert "id" in employee
            assert "name" in employee
            assert "position" in employee
            assert isinstance(employee["id"], int)
            assert isinstance(employee["name"], str)
            assert isinstance(employee["position"], str)
    
    def test_get_employee_by_id(self, wait_for_services, base_url):
        for employee_id in range(1, 9):
            response = requests.get(f"{base_url}/employees/{employee_id}")
            assert response.status_code == 200
            
            employee = response.json()
            assert employee["id"] == employee_id
            assert "name" in employee
            assert "position" in employee
    
    def test_get_nonexistent_employee(self, wait_for_services, base_url):
        response = requests.get(f"{base_url}/employees/999")
        assert response.status_code == 404
        
        error = response.json()
        assert "error" in error
        assert "Employee not found" in error["error"]

class TestAskEndpoint:
    @pytest.mark.parametrize("employee_id,question,expected_keywords", [
        (1, "What is machine learning?", ["machine learning", "algorithm", "data"]),
        (2, "What is React?", ["React", "JavaScript", "component"]),
        (3, "What is cryptography?", ["cryptography", "security", "encryption"]),
    ])
    def test_ask_specialist_question(self, wait_for_services, base_url, employee_id: int, question: str, expected_keywords: list):
        payload = {"question": question}
        response = requests.post(
            f"{base_url}/ask/{employee_id}",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "employee" in data
        assert "question" in data
        assert "answer" in data
        
        assert data["employee"]["id"] == employee_id
        assert data["question"] == question
        
        answer_lower = data["answer"].lower()
        assert any(keyword.lower() in answer_lower for keyword in expected_keywords), \
            f"Expected at least one of {expected_keywords} in answer, but got: {data['answer'][:200]}..."
    
    def test_ask_missing_question(self, wait_for_services, base_url):
        response = requests.post(
            f"{base_url}/ask/1",
            json={},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
        error = response.json()
        assert "error" in error
        assert "Question is required" in error["error"]
    
    def test_ask_invalid_employee(self, wait_for_services, base_url):
        payload = {"question": "Test question"}
        response = requests.post(
            f"{base_url}/ask/999",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 404
        error = response.json()
        assert "error" in error
        assert "Employee not found" in error["error"]
    
    def test_ask_invalid_content_type(self, wait_for_services, base_url):
        response = requests.post(
            f"{base_url}/ask/1",
            data="question=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 400

class TestServerEndpoints:
    def test_server_employees_endpoint(self, wait_for_services, server_url):
        response = requests.get(f"{server_url}/employees")
        assert response.status_code == 200
        
        employees = response.json()
        assert len(employees) == 8
    
    def test_server_ask_endpoint(self, wait_for_services, server_url):
        payload = {"employee_id": 1, "question": "What is AI?"}
        response = requests.post(
            f"{server_url}/ask",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "employee" in data
        assert "question" in data
        assert "answer" in data