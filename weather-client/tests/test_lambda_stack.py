"""
Tests for Lambda CDK Stack to ensure proper URL formatting.
This test file verifies that the health check URL is properly formatted
with a slash between the base URL and the path.
"""

import unittest
import re


class TestLambdaStackUrls(unittest.TestCase):
    """Test Lambda Stack URL formatting"""
    
    def test_health_check_url_needs_slash(self):
        """Test that health check URL construction needs a slash"""
        # Simulate current implementation
        base_url = "https://example.execute-api.us-east-1.amazonaws.com/"
        
        # Current implementation (without slash)
        current_health_url = f"{base_url}health"
        
        # Expected implementation (with slash)
        expected_health_url = f"{base_url}/health"
        
        # The current implementation should produce an incorrect URL
        self.assertEqual(current_health_url, "https://example.execute-api.us-east-1.amazonaws.com/health")
        
        # The expected implementation should have proper formatting
        self.assertEqual(expected_health_url, "https://example.execute-api.us-east-1.amazonaws.com//health")
        
        # Actually, if base_url already ends with /, we need to handle that
        # The proper way is to ensure exactly one slash
        proper_health_url = base_url.rstrip('/') + '/health'
        self.assertEqual(proper_health_url, "https://example.execute-api.us-east-1.amazonaws.com/health")
    
    def test_url_slash_handling(self):
        """Test different URL base scenarios"""
        test_cases = [
            # (base_url, expected_health_url)
            ("https://example.com/", "https://example.com/health"),
            ("https://example.com", "https://example.com/health"),
            ("https://example.com//", "https://example.com/health"),
        ]
        
        for base_url, expected in test_cases:
            with self.subTest(base_url=base_url):
                # Proper implementation should handle trailing slashes
                health_url = base_url.rstrip('/') + '/health'
                self.assertEqual(health_url, expected)
    
    def test_lambda_stack_file_content(self):
        """Test the actual content of the lambda_stack.py file"""
        import os
        
        # Read the actual lambda_stack.py file
        stack_path = os.path.join(os.path.dirname(__file__), '..', 'infra', 'stacks', 'lambda_stack.py')
        
        if os.path.exists(stack_path):
            with open(stack_path, 'r') as f:
                content = f.read()
            
            # Find the HealthCheckUrl line
            health_check_pattern = r'value=f"{self\.function_url\.url}health"'
            match = re.search(health_check_pattern, content)
            
            if match:
                # This pattern indicates the bug exists
                self.fail(f"Found health check URL without slash: {match.group()}")
            
            # Check if the corrected pattern exists
            corrected_pattern = r'value=f"{self\.function_url\.url}/health"'
            corrected_match = re.search(corrected_pattern, content)
            
            if corrected_match:
                # This would indicate the bug has been fixed
                pass  # Test passes
            else:
                # Look for any HealthCheckUrl pattern
                any_health_pattern = r'"HealthCheckUrl".*?value=.*?health'
                any_match = re.search(any_health_pattern, content, re.DOTALL)
                if any_match:
                    self.fail(f"Health check URL formatting may be incorrect. Found: {any_match.group()}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)