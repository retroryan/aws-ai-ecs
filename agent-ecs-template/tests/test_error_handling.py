import pytest
import requests
import json

class TestErrorHandling:
    def test_client_server_connection_error(self, wait_for_services, base_url):
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        initial_data = response.json()
        assert initial_data["status"] == "healthy"
        assert initial_data["server_status"]["status"] == "healthy"
    
    def test_malformed_json_request(self, wait_for_services, base_url):
        response = requests.post(
            f"{base_url}/ask/1",
            data="{'invalid': json}",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
    
    def test_empty_request_body(self, wait_for_services, base_url):
        response = requests.post(
            f"{base_url}/ask/1",
            data="",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
    
    def test_invalid_employee_id_type(self, wait_for_services, base_url):
        response = requests.get(f"{base_url}/employees/abc")
        assert response.status_code == 404
        
        response = requests.post(
            f"{base_url}/ask/abc",
            json={"question": "test"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 404
    
    def test_very_long_question(self, wait_for_services, base_url):
        long_question = "What is AI? " * 1000
        payload = {"question": long_question}
        
        response = requests.post(
            f"{base_url}/ask/1",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
    
    def test_special_characters_in_question(self, wait_for_services, base_url):
        special_questions = [
            "What about <script>alert('test')</script>?",
            "Can you explain SQL injection'; DROP TABLE users; --",
            "Tell me about 🚀 rockets and 🌟 stars",
            "What is the meaning of \n\r\t special characters?"
        ]
        
        for question in special_questions:
            payload = {"question": question}
            response = requests.post(
                f"{base_url}/ask/1",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["question"] == question
            assert "answer" in data
            assert len(data["answer"]) > 0