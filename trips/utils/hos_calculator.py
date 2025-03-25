from datetime import datetime, timedelta
from typing import List, Dict, Any

class HOSCalculator:
    """
    Hours of Service (HOS) Calculator based on FMCSA regulations
    - 11-hour driving limit
    - 14-hour on-duty window
    - 30-minute break required after 8 hours of driving
    - 70-hour limit in 8 days (for carriers operating 7 days a week)
    """
    # FMCSA HOS Constants
    MAX_DRIVING_HOURS = 11
    MAX_DUTY_WINDOW_HOURS = 14
    REQUIRED_BREAK_MINS = 30
    BREAK_AFTER_DRIVING_HOURS = 8
    CYCLE_HOURS_LIMIT = 70
    CYCLE_DAYS = 8

    def __init__(self, current_cycle_used: int = 0, previous_drives: List[Dict[str, Any]] = None):
        """
        Initialize the HOSCalculator
        
        Args:
            current_cycle_used: Hours used in the current 70-hour/8-day cycle
            previous_drives: List of previous driving periods with start/end times
        """
        self.current_cycle_used = current_cycle_used
        self.previous_drives = previous_drives or []
        
    def calculate_remaining_drive_time(self) -> Dict[str, Any]:
        """
        Calculate remaining drive time based on current cycle used
        
        Returns:
            Dictionary with remaining hours in different categories
        """
        remaining_cycle = max(0, self.CYCLE_HOURS_LIMIT - self.current_cycle_used)
        remaining_driving = self.MAX_DRIVING_HOURS  # Assuming a fresh day
        remaining_duty_window = self.MAX_DUTY_WINDOW_HOURS  # Assuming a fresh day
        
        # If we have previous drives in this duty period, adjust accordingly
        if self.previous_drives:
            # Sort by start time
            sorted_drives = sorted(self.previous_drives, key=lambda x: x.get('start_time'))
            
            # Calculate driving hours used in this duty period
            duty_period_start = sorted_drives[0]['start_time']
            duty_period_driving_hours = sum(
                (drive['end_time'] - drive['start_time']).total_seconds() / 3600 
                for drive in sorted_drives
            )
            
            # Calculate elapsed time in duty window
            last_drive_end = sorted_drives[-1]['end_time']
            duty_window_hours = (last_drive_end - duty_period_start).total_seconds() / 3600
            
            remaining_driving = max(0, self.MAX_DRIVING_HOURS - duty_period_driving_hours)
            remaining_duty_window = max(0, self.MAX_DUTY_WINDOW_HOURS - duty_window_hours)
        
        return {
            'remaining_cycle_hours': remaining_cycle,
            'remaining_driving_hours': remaining_driving,
            'remaining_duty_window_hours': remaining_duty_window
        }
    
    def calculate_required_breaks(self, start_time: datetime, trip_duration_hours: float) -> List[Dict[str, Any]]:
        """
        Calculate required breaks for a trip
        
        Args:
            start_time: Start time of the trip
            trip_duration_hours: Estimated duration of the trip in hours
            
        Returns:
            List of required breaks with start/end times
        """
        # Calculate how much driving time has occurred before this trip
        previous_driving_hours = 0
        if self.previous_drives:
            sorted_drives = sorted(self.previous_drives, key=lambda x: x.get('start_time'))
            for drive in sorted_drives:
                hours = (drive['end_time'] - drive['start_time']).total_seconds() / 3600
                previous_driving_hours += hours
        
        # Determine when the 8-hour driving limit will be reached
        hours_until_break = self.BREAK_AFTER_DRIVING_HOURS - (previous_driving_hours % self.BREAK_AFTER_DRIVING_HOURS)
        
        # If we'll exceed the 8-hour limit during this trip, schedule breaks
        breaks = []
        current_time = start_time
        remaining_trip_hours = trip_duration_hours
        
        while remaining_trip_hours > hours_until_break:
            # Schedule a break
            break_start = current_time + timedelta(hours=hours_until_break)
            break_end = break_start + timedelta(minutes=self.REQUIRED_BREAK_MINS)
            
            breaks.append({
                'break_type': '30-minute rest break',
                'reason': '8-hour driving limit reached',
                'start_time': break_start,
                'end_time': break_end
            })
            
            # Update current time and remaining trip hours
            current_time = break_end
            remaining_trip_hours -= hours_until_break
            
            # Reset hours until next break
            hours_until_break = self.BREAK_AFTER_DRIVING_HOURS
        
        return breaks
    
    def enforce_hos_limits(self, start_time: datetime, trip_duration_hours: float) -> Dict[str, Any]:
        """
        Enforce HOS limits for a trip and provide compliance information
        
        Args:
            start_time: Start time of the trip
            trip_duration_hours: Estimated duration of the trip in hours
            
        Returns:
            Dictionary with HOS compliance information
        """
        remaining = self.calculate_remaining_drive_time()
        
        # Check if trip exceeds 70-hour cycle limit
        cycle_compliant = trip_duration_hours <= remaining['remaining_cycle_hours']
        
        # Check if trip exceeds 11-hour driving limit
        driving_compliant = trip_duration_hours <= remaining['remaining_driving_hours']
        
        # Check if trip exceeds 14-hour duty window
        duty_window_compliant = trip_duration_hours <= remaining['remaining_duty_window_hours']
        
        # Calculate required breaks
        required_breaks = self.calculate_required_breaks(start_time, trip_duration_hours)
        
        # If any limits are exceeded, calculate required rest periods
        required_rest = []
        
        if not driving_compliant:
            # 10 consecutive hours off duty required after 11 hours of driving
            driving_complete_time = start_time + timedelta(hours=remaining['remaining_driving_hours'])
            rest_end_time = driving_complete_time + timedelta(hours=10)
            
            required_rest.append({
                'rest_type': '10-hour off-duty rest',
                'reason': '11-hour driving limit reached',
                'start_time': driving_complete_time,
                'end_time': rest_end_time
            })
        
        if not duty_window_compliant:
            # 10 consecutive hours off duty required after 14-hour window
            window_complete_time = start_time + timedelta(hours=remaining['remaining_duty_window_hours'])
            rest_end_time = window_complete_time + timedelta(hours=10)
            
            required_rest.append({
                'rest_type': '10-hour off-duty rest',
                'reason': '14-hour on-duty window limit reached',
                'start_time': window_complete_time,
                'end_time': rest_end_time
            })
        
        # Calculate total cycle hours that will be used after this trip
        updated_cycle_hours = self.current_cycle_used + trip_duration_hours
        
        return {
            'trip_start_time': start_time,
            'trip_end_time': start_time + timedelta(hours=trip_duration_hours),
            'trip_duration_hours': trip_duration_hours,
            'cycle_compliant': cycle_compliant,
            'driving_compliant': driving_compliant,
            'duty_window_compliant': duty_window_compliant,
            'required_breaks': required_breaks,
            'required_rest_periods': required_rest,
            'current_cycle_hours': self.current_cycle_used,
            'updated_cycle_hours': updated_cycle_hours,
            'remaining_before_trip': remaining
        }
    
    @classmethod
    def calculate_optimal_schedule(cls, origin: str, destination: str, 
                                  estimated_duration: float, start_time: datetime, 
                                  current_cycle_used: int = 0) -> Dict[str, Any]:
        """
        Calculate optimal driving schedule based on HOS regulations
        
        Args:
            origin: Starting location
            destination: Ending location
            estimated_duration: Estimated trip duration in hours
            start_time: Trip start time
            current_cycle_used: Hours used in the current 70-hour/8-day cycle
            
        Returns:
            Dictionary with optimal schedule information
        """
        calculator = cls(current_cycle_used)
        hos_data = calculator.enforce_hos_limits(start_time, estimated_duration)
        
        # Build an optimal schedule with segments and breaks
        schedule = []
        current_time = start_time
        remaining_hours = estimated_duration
        
        # Add trip segments and breaks
        while remaining_hours > 0:
            # Check if we need to stop for required rest
            rest_stop = False
            for rest in hos_data.get('required_rest_periods', []):
                if current_time >= rest['start_time'] and current_time < rest['end_time']:
                    # We're in a rest period, add it to schedule
                    schedule.append({
                        'type': 'rest',
                        'start_time': rest['start_time'],
                        'end_time': rest['end_time'],
                        'duration_hours': (rest['end_time'] - rest['start_time']).total_seconds() / 3600,
                        'location': 'Unknown rest location', # In real app, find nearest rest area
                        'reason': rest['reason']
                    })
                    current_time = rest['end_time']
                    rest_stop = True
                    break
            
            if rest_stop:
                continue
            
            # Check if we need a break
            break_needed = False
            for br in hos_data.get('required_breaks', []):
                if current_time < br['start_time'] and current_time + timedelta(hours=remaining_hours) > br['start_time']:
                    # We need to take a break during this segment
                    drive_hours = (br['start_time'] - current_time).total_seconds() / 3600
                    
                    # Add driving segment
                    schedule.append({
                        'type': 'drive',
                        'start_time': current_time,
                        'end_time': br['start_time'],
                        'duration_hours': drive_hours,
                        'start_location': origin if not schedule else 'En route',
                        'end_location': 'Break location'  # In real app, find nearest rest area
                    })
                    
                    # Add break
                    schedule.append({
                        'type': 'break',
                        'start_time': br['start_time'],
                        'end_time': br['end_time'],
                        'duration_hours': (br['end_time'] - br['start_time']).total_seconds() / 3600,
                        'location': 'Break location',  # In real app, find nearest rest area
                        'reason': br['reason']
                    })
                    
                    current_time = br['end_time']
                    remaining_hours -= drive_hours
                    break_needed = True
                    break
            
            if break_needed:
                continue
            
            # Add final driving segment
            end_time = current_time + timedelta(hours=remaining_hours)
            schedule.append({
                'type': 'drive',
                'start_time': current_time,
                'end_time': end_time,
                'duration_hours': remaining_hours,
                'start_location': origin if not schedule else 'En route',
                'end_location': destination
            })
            
            remaining_hours = 0
        
        return {
            'origin': origin,
            'destination': destination,
            'total_duration_hours': estimated_duration,
            'start_time': start_time,
            'end_time': start_time + timedelta(hours=estimated_duration + 
                                              sum([(s['duration_hours'] if s['type'] != 'drive' else 0) 
                                                   for s in schedule])),
            'schedule': schedule,
            'hos_data': hos_data
        } 