from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, timedelta
from .utils.hos_calculator import HOSCalculator
from .models import Trip

class HOSCalculatorTestCase(TestCase):
    """Test case for the HOSCalculator class"""
    
    def setUp(self):
        self.calculator = HOSCalculator(current_cycle_used=0)
        self.current_time = datetime.now()
    
    def test_remaining_drive_time_fresh_cycle(self):
        """Test remaining drive time calculation for a fresh cycle"""
        result = self.calculator.calculate_remaining_drive_time()
        
        self.assertEqual(result['remaining_cycle_hours'], 70)
        self.assertEqual(result['remaining_driving_hours'], 11)
        self.assertEqual(result['remaining_duty_window_hours'], 14)
    
    def test_remaining_drive_time_used_cycle(self):
        """Test remaining drive time calculation for a partially used cycle"""
        calculator = HOSCalculator(current_cycle_used=40)
        result = calculator.calculate_remaining_drive_time()
        
        self.assertEqual(result['remaining_cycle_hours'], 30)
        self.assertEqual(result['remaining_driving_hours'], 11)
        self.assertEqual(result['remaining_duty_window_hours'], 14)
    
    def test_required_breaks(self):
        """Test calculation of required breaks for a long trip"""
        start_time = self.current_time
        trip_duration = 10  # 10-hour trip
        
        breaks = self.calculator.calculate_required_breaks(start_time, trip_duration)
        
        # Should have at least 1 break (after 8 hours of driving)
        self.assertGreaterEqual(len(breaks), 1)
        
        # The first break should be scheduled after 8 hours
        first_break = breaks[0]
        expected_break_start = start_time + timedelta(hours=8)
        self.assertEqual(first_break['start_time'].hour, expected_break_start.hour)
        self.assertEqual(first_break['start_time'].minute, expected_break_start.minute)
    
    def test_enforce_hos_limits_compliant(self):
        """Test enforcement of HOS limits for a compliant trip"""
        start_time = self.current_time
        trip_duration = 5  # 5-hour trip
        
        result = self.calculator.enforce_hos_limits(start_time, trip_duration)
        
        self.assertTrue(result['cycle_compliant'])
        self.assertTrue(result['driving_compliant'])
        self.assertTrue(result['duty_window_compliant'])
        self.assertEqual(len(result['required_breaks']), 0)  # No breaks needed for 5-hour trip
        self.assertEqual(len(result['required_rest_periods']), 0)  # No rest needed
    
    def test_enforce_hos_limits_exceeds_driving(self):
        """Test enforcement of HOS limits for a trip exceeding driving hours"""
        start_time = self.current_time
        trip_duration = 12  # 12-hour trip
        
        result = self.calculator.enforce_hos_limits(start_time, trip_duration)
        
        self.assertTrue(result['cycle_compliant'])
        self.assertFalse(result['driving_compliant'])  # Exceeds 11-hour driving limit
        self.assertTrue(result['duty_window_compliant'])
        self.assertGreaterEqual(len(result['required_breaks']), 1)  # Break needed
        self.assertGreaterEqual(len(result['required_rest_periods']), 1)  # Rest needed
    
    def test_optimal_schedule(self):
        """Test calculation of optimal schedule"""
        start_time = self.current_time
        
        result = HOSCalculator.calculate_optimal_schedule(
            origin="New York",
            destination="Boston",
            estimated_duration=5,
            start_time=start_time,
            current_cycle_used=0
        )
        
        # Check structure of the result
        self.assertIn('origin', result)
        self.assertIn('destination', result)
        self.assertIn('total_duration_hours', result)
        self.assertIn('schedule', result)
        self.assertIn('hos_data', result)
        
        # For a 5-hour trip, schedule should have at least 1 segment (the drive)
        self.assertGreaterEqual(len(result['schedule']), 1)

class HOSAPITestCase(TestCase):
    """Test case for the HOS calculation API"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('calculate-hos')
        self.current_time = datetime.now().isoformat()
    
    def test_calculate_hos_valid_data(self):
        """Test the API with valid data"""
        data = {
            'origin': 'New York',
            'destination': 'Boston',
            'estimated_duration': 5.0,
            'start_time': self.current_time,
            'current_cycle_used': 0
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('origin', response.data)
        self.assertIn('destination', response.data)
        self.assertIn('schedule', response.data)
        self.assertIn('hos_data', response.data)
    
    def test_calculate_hos_invalid_data(self):
        """Test the API with invalid data"""
        data = {
            'origin': 'New York',
            'destination': 'Boston',
            # Missing estimated_duration
            'start_time': self.current_time,
            'current_cycle_used': 0
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_calculate_hos_invalid_cycle(self):
        """Test the API with invalid cycle hours"""
        data = {
            'origin': 'New York',
            'destination': 'Boston',
            'estimated_duration': 5.0,
            'start_time': self.current_time,
            'current_cycle_used': 80  # Exceeds 70-hour limit
        }
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_cycle_used', response.data)

    def test_generate_log_endpoint(self):
        """Test the PDF log generation endpoint works correctly."""
        # Create a test trip
        trip = Trip.objects.create(
            current_location="Test Current Location",
            pickup_location="Test Pickup Location",
            dropoff_location="Test Dropoff Location",
            current_cycle_used=12
        )
        
        # Request the PDF
        response = self.client.get(f'/api/generate_log/?trip_id={trip.id}')
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(f'attachment; filename="driver_log_trip_{trip.id}.pdf"', response['Content-Disposition'])
        
        # Verify there is content in the response
        self.assertTrue(len(response.content) > 0)
        
        # Test with invalid trip ID
        response_invalid = self.client.get('/api/generate_log/?trip_id=999999')
        self.assertEqual(response_invalid.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test with missing trip ID
        response_missing = self.client.get('/api/generate_log/')
        self.assertEqual(response_missing.status_code, status.HTTP_400_BAD_REQUEST)
