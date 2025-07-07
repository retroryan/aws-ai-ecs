"""
Integration tests for MCP servers with Pydantic models.

This test suite verifies that the MCP servers correctly handle:
1. String coordinates from AWS Bedrock
2. Float coordinates from other sources
3. Location name resolution
4. Error handling for invalid inputs
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_servers.models import ForecastRequest, HistoricalRequest, AgriculturalRequest


class TestForecastServer:
    """Test the forecast server with Pydantic models."""
    
    @pytest.mark.asyncio
    async def test_forecast_with_string_coordinates(self):
        """Test forecast server handles string coordinates from AWS Bedrock."""
        # Import here to avoid circular imports
        from mcp_servers import forecast_server
        
        # Mock the OpenMeteoClient
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "current": {"temperature_2m": 22.5},
            "daily": {"temperature_2m_max": [25.0]},
            "hourly": {"temperature_2m": [22.0, 23.0]}
        }
        
        # Replace the client
        original_client = forecast_server.client
        forecast_server.client = mock_client
        
        try:
            # Create request with string coordinates (as AWS Bedrock sends)
            request = ForecastRequest(
                latitude="41.8781",
                longitude="-87.6298",
                days=5
            )
            
            # Call the tool function
            result = await forecast_server.get_weather_forecast(request)
            
            # Verify the result
            assert "location_info" in result
            assert result["location_info"]["coordinates"]["latitude"] == 41.8781
            assert result["location_info"]["coordinates"]["longitude"] == -87.6298
            assert "41.8781,-87.6298" in result["location_info"]["name"]
            assert "5 days" in result["summary"]
            
            # Verify the API was called with float values
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args[0][1]
            assert call_args["latitude"] == 41.8781
            assert call_args["longitude"] == -87.6298
            assert call_args["forecast_days"] == 5
            
        finally:
            # Restore original client
            forecast_server.client = original_client
    
    @pytest.mark.asyncio
    async def test_forecast_with_location_name(self):
        """Test forecast server handles location name resolution."""
        from mcp_servers import forecast_server
        
        # Mock get_coordinates
        with patch('mcp_servers.forecast_server.get_coordinates') as mock_get_coords:
            mock_get_coords.return_value = {
                "latitude": 41.8781,
                "longitude": -87.6298,
                "name": "Chicago"
            }
            
            # Mock the OpenMeteoClient
            mock_client = AsyncMock()
            mock_client.get.return_value = {
                "current": {"temperature_2m": 22.5},
                "daily": {},
                "hourly": {}
            }
            
            original_client = forecast_server.client
            forecast_server.client = mock_client
            
            try:
                # Create request with location name only
                request = ForecastRequest(location="Chicago, IL")
                
                # Call the tool function
                result = await forecast_server.get_weather_forecast(request)
                
                # Verify the result
                assert "location_info" in result
                assert result["location_info"]["name"] == "Chicago"
                assert result["location_info"]["coordinates"]["latitude"] == 41.8781
                
                # Verify get_coordinates was called
                mock_get_coords.assert_called_once_with("Chicago, IL")
                
            finally:
                forecast_server.client = original_client
    
    @pytest.mark.asyncio
    async def test_forecast_with_invalid_coordinates(self):
        """Test forecast server validation with invalid coordinates."""
        from mcp_servers import forecast_server
        
        # This should raise ValidationError at the Pydantic level
        with pytest.raises(Exception) as exc_info:
            request = ForecastRequest(
                latitude="91.0",  # Invalid: > 90
                longitude="-87.6298"
            )
            await forecast_server.get_weather_forecast(request)
        
        assert "Latitude must be between -90 and 90" in str(exc_info.value)


class TestHistoricalServer:
    """Test the historical server with Pydantic models."""
    
    @pytest.mark.asyncio
    async def test_historical_with_string_coordinates(self):
        """Test historical server handles string coordinates."""
        from mcp_servers import historical_server
        
        # Mock the OpenMeteoClient
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "daily": {
                "temperature_2m_max": [25.0, 26.0],
                "temperature_2m_min": [18.0, 19.0]
            }
        }
        
        original_client = historical_server.client
        historical_server.client = mock_client
        
        try:
            # Create request with string coordinates
            request = HistoricalRequest(
                latitude="41.8781",
                longitude="-87.6298",
                start_date="2024-01-01",
                end_date="2024-01-07"
            )
            
            # Call the tool function
            result = await historical_server.get_historical_weather(request)
            
            # Verify the result
            assert "location_info" in result
            assert result["location_info"]["coordinates"]["latitude"] == 41.8781
            assert result["location_info"]["coordinates"]["longitude"] == -87.6298
            assert "2024-01-01 to 2024-01-07" in result["summary"]
            
            # Verify the API was called with correct values
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args[0][1]
            assert call_args["latitude"] == 41.8781
            assert call_args["longitude"] == -87.6298
            
        finally:
            historical_server.client = original_client
    
    @pytest.mark.asyncio
    async def test_historical_date_validation(self):
        """Test historical server date validation."""
        from mcp_servers import historical_server
        
        # Test invalid date order (handled by Pydantic)
        with pytest.raises(Exception) as exc_info:
            request = HistoricalRequest(
                location="Chicago",
                start_date="2024-01-07",
                end_date="2024-01-01"  # Before start date
            )
        
        assert "End date must be after start date" in str(exc_info.value)


class TestAgriculturalServer:
    """Test the agricultural server with Pydantic models."""
    
    @pytest.mark.asyncio
    async def test_agricultural_with_string_coordinates(self):
        """Test agricultural server handles string coordinates."""
        from mcp_servers import agricultural_server
        
        # Mock the OpenMeteoClient
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "current": {"temperature_2m": 22.5},
            "daily": {"et0_fao_evapotranspiration": [3.5]},
            "hourly": {"soil_moisture_0_to_1cm": [0.25]}
        }
        
        original_client = agricultural_server.client
        agricultural_server.client = mock_client
        
        try:
            # Create request with string coordinates
            request = AgriculturalRequest(
                latitude="41.5868",
                longitude="-93.6250",
                days=3
            )
            
            # Call the tool function
            result = await agricultural_server.get_agricultural_conditions(request)
            
            # Verify the result
            assert "location_info" in result
            assert result["location_info"]["coordinates"]["latitude"] == 41.5868
            assert result["location_info"]["coordinates"]["longitude"] == -93.625
            assert "(3 days)" in result["summary"]
            assert "Soil moisture" in result["summary"]
            
            # Verify the API was called with correct values
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args[0][1]
            assert call_args["latitude"] == 41.5868
            assert call_args["longitude"] == -93.625
            assert call_args["forecast_days"] == 3
            
        finally:
            agricultural_server.client = original_client
    
    @pytest.mark.asyncio
    async def test_agricultural_days_validation(self):
        """Test agricultural server days validation."""
        from mcp_servers import agricultural_server
        
        # Days > 7 should fail at Pydantic level
        with pytest.raises(Exception):
            request = AgriculturalRequest(
                location="Iowa",
                days=8  # Invalid: > 7
            )


class TestEndToEndScenarios:
    """Test end-to-end scenarios matching real usage."""
    
    @pytest.mark.asyncio
    async def test_aws_bedrock_style_request(self):
        """Test handling of AWS Bedrock style requests with string coordinates."""
        from mcp_servers import forecast_server
        
        # Mock the client
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "current": {"temperature_2m": 15.5, "weather_code": 3},
            "daily": {"temperature_2m_max": [18.0]},
            "hourly": {"temperature_2m": [15.0, 16.0]},
            "location_info": {}
        }
        
        original_client = forecast_server.client
        forecast_server.client = mock_client
        
        try:
            # Simulate AWS Bedrock request format
            bedrock_style_data = {
                "latitude": "51.5074",  # London coordinates as strings
                "longitude": "-0.1278"
            }
            
            # Create request from Bedrock-style data
            request = ForecastRequest(**bedrock_style_data)
            
            # Verify Pydantic converted strings to floats
            assert isinstance(request.latitude, float)
            assert isinstance(request.longitude, float)
            assert request.latitude == 51.5074
            assert request.longitude == -0.1278
            
            # Call the server
            result = await forecast_server.get_weather_forecast(request)
            
            # Verify success
            assert "error" not in result
            assert "location_info" in result
            assert result["location_info"]["coordinates"]["latitude"] == 51.5074
            
        finally:
            forecast_server.client = original_client
    
    @pytest.mark.asyncio 
    async def test_mixed_input_types(self):
        """Test handling of mixed string and numeric inputs."""
        from mcp_servers import forecast_server
        
        # Mock the client
        mock_client = AsyncMock()
        mock_client.get.return_value = {"current": {}, "daily": {}, "hourly": {}}
        
        original_client = forecast_server.client
        forecast_server.client = mock_client
        
        try:
            # Mixed types as might come from different sources
            mixed_data = {
                "location": "Tokyo",
                "latitude": "35.6762",  # string
                "longitude": 139.6503,   # float
                "days": "10"            # string that should convert to int
            }
            
            # Create request
            request = ForecastRequest(**mixed_data)
            
            # Verify all conversions worked
            assert request.location == "Tokyo"
            assert request.latitude == 35.6762
            assert request.longitude == 139.6503
            assert request.days == 10
            assert isinstance(request.latitude, float)
            assert isinstance(request.longitude, float)
            assert isinstance(request.days, int)
            
        finally:
            forecast_server.client = original_client


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])