"""
Test Pydantic model validation for MCP servers.

This test suite verifies that our Pydantic models correctly handle:
1. String-to-float conversion for coordinates
2. Validation of coordinate ranges
3. Date format validation
4. Required vs optional fields
"""

import pytest
from pydantic import ValidationError
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_servers.models import LocationInput, ForecastRequest, HistoricalRequest, AgriculturalRequest


class TestLocationInput:
    """Test the base LocationInput model."""
    
    def test_string_coordinates_conversion(self):
        """Test that string coordinates are converted to floats."""
        # This is the key test - AWS Bedrock sends coordinates as strings
        data = {
            "latitude": "41.8781",
            "longitude": "-87.6298"
        }
        model = LocationInput(**data)
        assert model.latitude == 41.8781
        assert model.longitude == -87.6298
        assert isinstance(model.latitude, float)
        assert isinstance(model.longitude, float)
    
    def test_float_coordinates(self):
        """Test that float coordinates work directly."""
        data = {
            "latitude": 41.8781,
            "longitude": -87.6298
        }
        model = LocationInput(**data)
        assert model.latitude == 41.8781
        assert model.longitude == -87.6298
    
    def test_location_only(self):
        """Test that location name works without coordinates."""
        data = {"location": "Chicago, IL"}
        model = LocationInput(**data)
        assert model.location == "Chicago, IL"
        assert model.latitude is None
        assert model.longitude is None
    
    def test_latitude_range_validation(self):
        """Test latitude range validation (-90 to 90)."""
        # Valid edge cases
        LocationInput(latitude=90.0, longitude=0.0)
        LocationInput(latitude=-90.0, longitude=0.0)
        
        # Invalid cases
        with pytest.raises(ValidationError) as exc_info:
            LocationInput(latitude=91.0, longitude=0.0)
        assert "Latitude must be between -90 and 90" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            LocationInput(latitude=-91.0, longitude=0.0)
        assert "Latitude must be between -90 and 90" in str(exc_info.value)
    
    def test_longitude_range_validation(self):
        """Test longitude range validation (-180 to 180)."""
        # Valid edge cases
        LocationInput(latitude=0.0, longitude=180.0)
        LocationInput(latitude=0.0, longitude=-180.0)
        
        # Invalid cases
        with pytest.raises(ValidationError) as exc_info:
            LocationInput(latitude=0.0, longitude=181.0)
        assert "Longitude must be between -180 and 180" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            LocationInput(latitude=0.0, longitude=-181.0)
        assert "Longitude must be between -180 and 180" in str(exc_info.value)
    
    def test_at_least_one_location_required(self):
        """Test that at least one location method is required."""
        # Empty data should fail
        with pytest.raises(ValidationError) as exc_info:
            LocationInput()
        assert "Either location name or coordinates" in str(exc_info.value)
        
        # All None should fail
        with pytest.raises(ValidationError) as exc_info:
            LocationInput(location=None, latitude=None, longitude=None)
        assert "Either location name or coordinates" in str(exc_info.value)
    
    def test_partial_coordinates_allowed(self):
        """Test that partial coordinates with location name is allowed."""
        # Only latitude with location
        model = LocationInput(location="Chicago", latitude=41.8781)
        assert model.location == "Chicago"
        assert model.latitude == 41.8781
        assert model.longitude is None
    
    def test_numeric_string_edge_cases(self):
        """Test edge cases for numeric string conversion."""
        # Scientific notation
        model = LocationInput(latitude="4.18781e1", longitude="-8.76298e1")
        assert abs(model.latitude - 41.8781) < 0.0001
        assert abs(model.longitude - -87.6298) < 0.0001
        
        # Leading/trailing spaces
        model = LocationInput(latitude=" 41.8781 ", longitude=" -87.6298 ")
        assert model.latitude == 41.8781
        assert model.longitude == -87.6298


class TestForecastRequest:
    """Test the ForecastRequest model."""
    
    def test_default_days(self):
        """Test default days value."""
        model = ForecastRequest(location="Chicago")
        assert model.days == 7
    
    def test_days_validation(self):
        """Test days range validation (1-16)."""
        # Valid edge cases
        ForecastRequest(location="Chicago", days=1)
        ForecastRequest(location="Chicago", days=16)
        
        # Invalid cases
        with pytest.raises(ValidationError):
            ForecastRequest(location="Chicago", days=0)
        
        with pytest.raises(ValidationError):
            ForecastRequest(location="Chicago", days=17)
    
    def test_complete_request_with_string_coords(self):
        """Test a complete forecast request with string coordinates."""
        data = {
            "location": "Chicago, IL",
            "latitude": "41.8781",
            "longitude": "-87.6298",
            "days": 5
        }
        model = ForecastRequest(**data)
        assert model.location == "Chicago, IL"
        assert model.latitude == 41.8781
        assert model.longitude == -87.6298
        assert model.days == 5


class TestHistoricalRequest:
    """Test the HistoricalRequest model."""
    
    def test_valid_dates(self):
        """Test valid date formats."""
        model = HistoricalRequest(
            location="Chicago",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        assert model.start_date == "2024-01-01"
        assert model.end_date == "2024-01-31"
    
    def test_invalid_date_format(self):
        """Test invalid date formats."""
        # Wrong format
        with pytest.raises(ValidationError) as exc_info:
            HistoricalRequest(
                location="Chicago",
                start_date="01/01/2024",
                end_date="01/31/2024"
            )
        assert "String should match pattern" in str(exc_info.value)
        
        # Invalid date
        with pytest.raises(ValidationError):
            HistoricalRequest(
                location="Chicago",
                start_date="2024-13-01",  # Invalid month
                end_date="2024-01-31"
            )
    
    def test_date_order_validation(self):
        """Test that end date must be after start date."""
        with pytest.raises(ValidationError) as exc_info:
            HistoricalRequest(
                location="Chicago",
                start_date="2024-01-31",
                end_date="2024-01-01"
            )
        assert "End date must be after start date" in str(exc_info.value)
    
    def test_complete_request_with_string_coords(self):
        """Test a complete historical request with string coordinates."""
        data = {
            "latitude": "41.8781",
            "longitude": "-87.6298",
            "start_date": "2024-01-01",
            "end_date": "2024-01-07"
        }
        model = HistoricalRequest(**data)
        assert model.latitude == 41.8781
        assert model.longitude == -87.6298
        assert model.start_date == "2024-01-01"
        assert model.end_date == "2024-01-07"


class TestAgriculturalRequest:
    """Test the AgriculturalRequest model."""
    
    def test_default_days(self):
        """Test default days value."""
        model = AgriculturalRequest(location="Iowa Farm")
        assert model.days == 7
    
    def test_days_validation(self):
        """Test days range validation (1-7)."""
        # Valid edge cases
        AgriculturalRequest(location="Iowa", days=1)
        AgriculturalRequest(location="Iowa", days=7)
        
        # Invalid cases
        with pytest.raises(ValidationError):
            AgriculturalRequest(location="Iowa", days=0)
        
        with pytest.raises(ValidationError):
            AgriculturalRequest(location="Iowa", days=8)
    
    def test_complete_request_with_string_coords(self):
        """Test a complete agricultural request with string coordinates."""
        data = {
            "location": "Iowa Farm",
            "latitude": "41.5868",
            "longitude": "-93.6250",
            "days": 3
        }
        model = AgriculturalRequest(**data)
        assert model.location == "Iowa Farm"
        assert model.latitude == 41.5868
        assert model.longitude == -93.625
        assert model.days == 3


class TestRealWorldScenarios:
    """Test real-world scenarios that match AWS Bedrock behavior."""
    
    def test_aws_bedrock_forecast_payload(self):
        """Test payload format as sent by AWS Bedrock."""
        # This matches the actual format from AWS Bedrock logs
        bedrock_payload = {
            "latitude": "41.8781",
            "longitude": "-87.6298"
        }
        model = ForecastRequest(**bedrock_payload)
        assert model.latitude == 41.8781
        assert model.longitude == -87.6298
        assert model.days == 7  # default
    
    def test_aws_bedrock_with_location_name(self):
        """Test AWS Bedrock payload with location name."""
        bedrock_payload = {
            "location": "Chicago, IL",
            "latitude": "41.8781",
            "longitude": "-87.6298",
            "days": 5
        }
        model = ForecastRequest(**bedrock_payload)
        assert model.location == "Chicago, IL"
        assert model.latitude == 41.8781
        assert model.longitude == -87.6298
        assert model.days == 5
    
    def test_mixed_types_from_bedrock(self):
        """Test mixed string and numeric types from Bedrock."""
        # Sometimes Bedrock might send mixed types
        bedrock_payload = {
            "latitude": "41.8781",  # string
            "longitude": -87.6298,   # float
            "days": 5               # int
        }
        model = ForecastRequest(**bedrock_payload)
        assert model.latitude == 41.8781
        assert model.longitude == -87.6298
        assert model.days == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])