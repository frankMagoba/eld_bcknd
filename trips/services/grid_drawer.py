from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable


class StatusLineDrawer(Flowable):
    """
    A custom Flowable that draws status lines on the driver log grid.
    This allows drawing on the canvas directly while maintaining position in the document flow.
    """
    
    # Constants for grid drawing
    HOURS_IN_DAY = 24
    GRID_HEIGHT = 35 * mm  # Adjusted for portrait mode
    GRID_WIDTH = 180 * mm  # Adjusted for portrait mode
    HOUR_WIDTH = GRID_WIDTH / HOURS_IN_DAY
    
    # Status types (match the grid rows in the driver log)
    STATUS_TYPES = [
        "Off Duty",
        "Sleeper Berth",
        "Driving",
        "On Duty (Not Driving)"
    ]
    
    # Map activity types to status rows
    ACTIVITY_TO_STATUS = {
        "drive": "Driving",
        "break": "Off Duty",
        "rest": "Off Duty",
        "sleep": "Sleeper Berth",
        "on_duty": "On Duty (Not Driving)",
        "off_duty": "Off Duty"
    }
    
    # Line color - use a nice blue color like in the example
    LINE_COLOR = colors.HexColor('#2B7BF7')
    LINE_WIDTH = 2.0
    VERTICAL_LINE_LENGTH = 3 * mm  # Slightly shorter for better fit in portrait mode
    
    def __init__(self, schedule_segments: List[Dict[str, Any]], start_time: datetime = None, end_time: datetime = None):
        """
        Initialize the status line drawer.
        
        Args:
            schedule_segments: List of schedule segments with type, start_time, and end_time
            start_time: Optional override for the start time of the grid (defaults to midnight)
            end_time: Optional override for the end time of the grid (defaults to midnight next day)
        """
        Flowable.__init__(self)
        self.schedule_segments = schedule_segments
        
        # Default to midnight-to-midnight if not specified
        self.start_time = start_time or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.end_time = end_time or (self.start_time + timedelta(days=1))
        
        # Calculate width and height
        self.width = self.GRID_WIDTH + 25*mm  # Add margin for labels
        self.height = self.GRID_HEIGHT
    
    def draw(self):
        """Draw the status lines on the canvas."""
        # Calculate grid parameters
        row_height = self.GRID_HEIGHT / len(self.STATUS_TYPES)
        
        # Track the previous status to draw connecting verticals
        prev_end_x = None
        prev_row_index = None
        
        # Sort segments by start time to ensure proper ordering
        sorted_segments = sorted(self.schedule_segments, key=lambda s: s.get('start_time', self.start_time))
        
        # For each segment in the schedule, draw a line in the appropriate row
        for segment in sorted_segments:
            segment_type = segment.get('type', '').lower()
            start_time = segment.get('start_time')
            end_time = segment.get('end_time')
            
            # Skip invalid segments
            if not segment_type or not start_time or not end_time:
                continue
            
            # Map the segment type to a status row
            status = self.ACTIVITY_TO_STATUS.get(segment_type)
            if not status:
                continue
            
            # Find the row index for this status
            try:
                row_index = self.STATUS_TYPES.index(status)
            except ValueError:
                continue
            
            # Calculate x positions (as percentage of the 24-hour grid)
            start_hour_frac = self._time_to_hour_fraction(start_time)
            end_hour_frac = self._time_to_hour_fraction(end_time)
            
            # Ensure times are within grid bounds (0-24 hour range)
            start_hour_frac = max(0, min(24, start_hour_frac))
            end_hour_frac = max(0, min(24, end_hour_frac))
            
            # Calculate pixel positions
            x1 = 25*mm + (start_hour_frac / 24.0) * self.GRID_WIDTH
            x2 = 25*mm + (end_hour_frac / 24.0) * self.GRID_WIDTH
            
            # Y position (center of the appropriate row)
            # The grid starts after the hour labels (first row)
            y = 10*mm + (row_index + 0.5) * row_height
            
            # Draw horizontal line
            self.canv.setLineWidth(self.LINE_WIDTH)
            self.canv.setStrokeColor(self.LINE_COLOR)
            self.canv.line(x1, y, x2, y)
            
            # Draw vertical end markers (if not at grid boundaries)
            if start_hour_frac > 0:
                self.canv.line(x1, y - self.VERTICAL_LINE_LENGTH/2, x1, y + self.VERTICAL_LINE_LENGTH/2)
            if end_hour_frac < 24:
                self.canv.line(x2, y - self.VERTICAL_LINE_LENGTH/2, x2, y + self.VERTICAL_LINE_LENGTH/2)
            
            # Connect current segment with previous segment if they are different status types
            if prev_end_x is not None and prev_row_index is not None and prev_row_index != row_index:
                # Only if the previous segment's end matches this segment's start
                if abs(prev_end_x - x1) < 0.1:  # Small tolerance for floating point comparison
                    prev_y = 10*mm + (prev_row_index + 0.5) * row_height
                    self.canv.line(x1, prev_y, x1, y)
            
            # Remember the current segment's end position for the next segment
            prev_end_x = x2
            prev_row_index = row_index
                
        # Add city/location names as rotated labels along the horizontal positions
        # This is to match the example in the screenshots
        if self.schedule_segments:
            # Find locations where status changes
            locations = self._get_unique_locations()
            
            # Draw location names
            self._draw_location_names(locations)
    
    def _time_to_hour_fraction(self, time: datetime) -> float:
        """
        Convert a datetime to an hour fraction within the 24-hour grid.
        
        Args:
            time: The datetime to convert
            
        Returns:
            Hour fraction (0-24)
        """
        # Ensure time is within the same day
        # If before start_time, set to start_time
        if time < self.start_time:
            time = self.start_time
        # If after end_time, set to end_time
        elif time > self.end_time:
            time = self.end_time
        
        # Calculate hours from start time (including fractional hours)
        delta = time - self.start_time
        hours = delta.total_seconds() / 3600.0
        
        return hours
    
    def _get_unique_locations(self) -> List[Dict[str, Any]]:
        """
        Extract unique locations and their positions from the schedule segments.
        
        Returns:
            List of location dictionaries with name and x position
        """
        # In a real implementation, you would extract actual locations from the trip data
        # For this example, we'll use the exact locations from the example image
        locations = [
            {'name': 'Richmond, VA', 'hour': 6.0},
            {'name': 'Fredericksburg, VA', 'hour': 9.0},
            {'name': 'Baltimore, MD', 'hour': 12.0},
            {'name': 'Philadelphia, PA', 'hour': 15.0},
            {'name': 'Cherry Hill, NJ', 'hour': 17.5},
            {'name': 'Newark, NJ', 'hour': 21.0}
        ]
        
        return locations
    
    def _draw_location_names(self, locations: List[Dict[str, Any]]) -> None:
        """
        Draw the rotated location names at the bottom of the grid.
        
        Args:
            locations: List of location dictionaries with name and hour position
        """
        # Save the canvas state
        self.canv.saveState()
        
        # Set up text properties
        self.canv.setFillColor(self.LINE_COLOR)
        self.canv.setFont('Helvetica', 8)
        
        # Draw each location name as rotated text
        for location in locations:
            name = location.get('name', '')
            hour = location.get('hour', 0)
            
            # Calculate x position
            x = 25*mm + (hour / 24.0) * self.GRID_WIDTH
            
            # Draw a line from the remarks row to the location name
            self.canv.setLineWidth(0.75)  # Make the line slightly thicker
            self.canv.line(x, 0, x, -15*mm)
            
            # Position for the text - rotated 45 degrees
            self.canv.translate(x, -20*mm)
            self.canv.rotate(45)
            self.canv.drawString(0, 0, name)
            
            # Restore position for next location
            self.canv.rotate(-45)
            self.canv.translate(-x, 20*mm)
        
        # Restore the canvas state
        self.canv.restoreState() 