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
    VERTICAL_LINE_LENGTH = 3 * mm
    
    def __init__(self, schedule_segments: List[Dict[str, Any]], start_time: datetime = None, end_time: datetime = None,
                 canvas: Canvas = None, x_offset: float = 0, y_offset: float = 0, 
                 grid_width: float = None, grid_height: float = None):
        """
        Initialize the status line drawer.
        
        Args:
            schedule_segments: List of schedule segments with type, start_time, and end_time
            start_time: Optional override for the start time of the grid (defaults to midnight)
            end_time: Optional override for the end time of the grid (defaults to midnight next day)
            canvas: Canvas to draw on directly (if None, uses the flowable's canvas)
            x_offset: X position offset for drawing on an existing canvas
            y_offset: Y position offset for drawing on an existing canvas
            grid_width: Override for grid width (if None, uses default)
            grid_height: Override for grid height (if None, uses default)
        """
        Flowable.__init__(self)
        self.schedule_segments = schedule_segments
        
        # Default to midnight-to-midnight if not specified
        self.start_time = start_time or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.end_time = end_time or (self.start_time + timedelta(days=1))
        
        # Canvas and position parameters
        self.external_canvas = canvas
        self.x_offset = x_offset
        self.y_offset = y_offset
        
        # Grid dimensions
        self.grid_width = grid_width or self.GRID_WIDTH
        self.grid_height = grid_height or self.GRID_HEIGHT
        
        # Calculate width and height for flowable
        self.width = self.grid_width + 25*mm  # Add margin for labels
        self.height = self.grid_height
    
    def draw(self):
        """Draw the status lines on the canvas."""
        # Use provided canvas if available, otherwise use flowable's canvas
        canvas = self.external_canvas or self.canv
        
        # Calculate grid parameters
        row_height = self.grid_height / len(self.STATUS_TYPES)
        
        # Track the previous status to draw connecting verticals
        prev_end_x = None
        prev_row_index = None
        
        # Sort segments by start time to ensure proper ordering
        sorted_segments = sorted(self.schedule_segments, key=lambda s: s.get('start_time', self.start_time))
        
        # Check if we need to add implied "Off Duty" at the beginning
        self._add_implied_segments(sorted_segments)
        
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
            
            # Calculate pixel positions with offsets
            x1 = self.x_offset + (start_hour_frac / 24.0) * self.grid_width
            x2 = self.x_offset + (end_hour_frac / 24.0) * self.grid_width
            
            # Y position - top row is Off Duty (row 0), bottom is On Duty (Not Driving) (row 3)
            # We need to invert the row index because the grid is drawn from top to bottom
            # but our STATUS_TYPES are ordered from top to bottom
            y = self.y_offset + (self.grid_height - (row_index + 0.5) * row_height)
            
            # Draw horizontal line
            canvas.setLineWidth(self.LINE_WIDTH)
            canvas.setStrokeColor(self.LINE_COLOR)
            canvas.line(x1, y, x2, y)
            
            # Draw vertical end markers (if not at grid boundaries)
            if start_hour_frac > 0:
                canvas.line(x1, y - self.VERTICAL_LINE_LENGTH/2, x1, y + self.VERTICAL_LINE_LENGTH/2)
            if end_hour_frac < 24:
                canvas.line(x2, y - self.VERTICAL_LINE_LENGTH/2, x2, y + self.VERTICAL_LINE_LENGTH/2)
            
            # Connect current segment with previous segment if they are different status types
            if prev_end_x is not None and prev_row_index is not None and prev_row_index != row_index:
                # Only if the previous segment's end matches this segment's start
                if abs(prev_end_x - x1) < 0.1:  # Small tolerance for floating point comparison
                    prev_y = self.y_offset + (self.grid_height - (prev_row_index + 0.5) * row_height)
                    canvas.line(x1, prev_y, x1, y)
            
            # Remember the current segment's end position for the next segment
            prev_end_x = x2
            prev_row_index = row_index
                
        # Add location markers at the bottom
        locations = self._get_unique_locations()
        self._draw_location_marks(locations, canvas)
    
    def _add_implied_segments(self, segments: List[Dict[str, Any]]) -> None:
        """
        Add implied "Off Duty" segments at the beginning and between non-contiguous segments.
        
        Args:
            segments: List of schedule segments (will be modified in place)
        """
        if not segments:
            # If no segments, add a full-day Off Duty segment
            segments.append({
                'type': 'off_duty',
                'start_time': self.start_time,
                'end_time': self.end_time
            })
            return
            
        # Check if first segment starts after the grid start time
        first_segment = segments[0]
        first_start = first_segment.get('start_time')
        
        if first_start and first_start > self.start_time:
            # Add implied Off Duty from grid start to first segment
            segments.insert(0, {
                'type': 'off_duty',
                'start_time': self.start_time,
                'end_time': first_start
            })
            
        # Check for gaps between segments
        for i in range(1, len(segments)):
            prev_end = segments[i-1].get('end_time')
            curr_start = segments[i].get('start_time')
            
            if prev_end and curr_start and curr_start > prev_end:
                # Add implied Off Duty for the gap
                segments.insert(i, {
                    'type': 'off_duty',
                    'start_time': prev_end,
                    'end_time': curr_start
                })
                
        # Check if last segment ends before grid end time
        last_segment = segments[-1]
        last_end = last_segment.get('end_time')
        
        if last_end and last_end < self.end_time:
            # Add implied Off Duty from last segment to grid end
            segments.append({
                'type': 'off_duty',
                'start_time': last_end,
                'end_time': self.end_time
            })
    
    def _time_to_hour_fraction(self, time: datetime) -> float:
        """
        Convert a datetime to a fraction of hours since the start of the grid.
        
        Args:
            time: The datetime to convert
            
        Returns:
            Hour position as a fraction (0-24)
        """
        # Calculate seconds from start_time to time
        delta_seconds = (time - self.start_time).total_seconds()
        
        # Convert to hours
        hours = delta_seconds / 3600.0
        
        return hours
    
    def _get_unique_locations(self) -> List[Dict[str, Any]]:
        """
        Get a list of unique locations where status changes.
        
        Returns:
            List of location dictionaries with name and hour position
        """
        locations = []
        
        # Extract locations from segments
        for segment in self.schedule_segments:
            start_time = segment.get('start_time')
            
            # Only add locations for significant status changes
            if segment.get('type') == 'drive':
                # Calculate hour fraction
                if start_time:
                    hour = self._time_to_hour_fraction(start_time)
                    
                    # Create a location name based on the time
                    time_str = start_time.strftime("%H:%M")
                    name = f"Start Drive {time_str}"
                    
                    # Only add if within grid bounds
                    if 0 <= hour <= 24:
                        locations.append({'name': name, 'hour': hour})
            
            # Add locations for rest periods too
            elif segment.get('type') in ['rest', 'break']:
                if start_time:
                    hour = self._time_to_hour_fraction(start_time)
                    time_str = start_time.strftime("%H:%M")
                    name = f"Rest {time_str}"
                    
                    if 0 <= hour <= 24:
                        locations.append({'name': name, 'hour': hour})
        
        return locations
    
    def _draw_location_marks(self, locations: List[Dict[str, Any]], canvas=None) -> None:
        """
        Draw location markers at the bottom of the grid.
        
        Args:
            locations: List of location dictionaries with name and time
            canvas: Canvas to draw on
        """
        if not locations:
            return
        
        # Use provided canvas if available, otherwise use flowable's canvas
        canvas = canvas or self.canv
        
        # Save the canvas state
        canvas.saveState()
        
        # Set up line properties
        canvas.setStrokeColor(self.LINE_COLOR)
        canvas.setLineWidth(0.75)
        
        # Draw location marks
        for location in locations:
            hour = location.get('hour', 0)
            
            # Calculate x position
            x = self.x_offset + (hour / 24.0) * self.grid_width
            
            # Draw a small mark at the bottom of the grid
            bottom_y = self.y_offset
            mark_height = 5*mm
            
            # Draw location mark (triangle)
            canvas.line(x, bottom_y, x - 2*mm, bottom_y - mark_height)
            canvas.line(x, bottom_y, x + 2*mm, bottom_y - mark_height)
            canvas.line(x - 2*mm, bottom_y - mark_height, x + 2*mm, bottom_y - mark_height)
        
        # Restore canvas state
        canvas.restoreState() 