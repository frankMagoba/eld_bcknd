import io
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas

from ..models import Trip
from ..utils.hos_calculator import HOSCalculator
from .grid_drawer import StatusLineDrawer


class PDFGenerator:
    """Service to generate FMCSA-compliant driver log PDFs using reportlab."""
    
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
        "On Duty (Not Driving)",
        "REMARKS"
    ]
    
    def __init__(self, trip: Trip, schedule_data: Optional[Dict[str, Any]] = None):
        """
        Initialize the PDF Generator.
        
        Args:
            trip: The Trip model instance
            schedule_data: Optional precomputed schedule data (if None, will be calculated)
        """
        self.trip = trip
        self.schedule_data = schedule_data
        
        # If schedule data not provided, calculate it using the HOS calculator
        if not self.schedule_data:
            # Set up a reasonable start time (8 AM today)
            start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
            
            # Use current trip data to calculate schedule
            estimated_duration = 8.0  # Default to 8 hours if no better estimate
            
            # Create calculator and get schedule
            self.calculator = HOSCalculator(current_cycle_used=trip.current_cycle_used)
            self.schedule_data = self.calculator.calculate_optimal_schedule(
                origin=trip.pickup_location,
                destination=trip.dropoff_location,
                estimated_duration=estimated_duration,
                start_time=start_time,
                current_cycle_used=trip.current_cycle_used
            )
    
    def generate_pdf(self) -> bytes:
        """
        Generate a driver log PDF with FMCSA-compliant log grid.
        
        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        
        # Create the PDF document with letter portrait
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        # Get current date
        today = datetime.now()
        date_str = today.strftime("%m/%d/%Y")
        
        # Content elements
        elements = []
        
        # Add header section matching the exact design
        self._add_header(elements)
        
        # Add driver log grid
        self._add_driver_log_grid(elements)
        
        # Add remarks section
        self._add_remarks_section(elements)
        
        # Build the PDF
        doc.build(elements)
        
        # Get the PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data
    
    def _add_header(self, elements: List) -> None:
        """Add the header section to the PDF, matching the FMCSA log form."""
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # Create date field
        date_label = Paragraph("Date", normal_style)
        date_field = Table(
            [
                ["", "", ""],
                ["(MONTH)", "(DAY)", "(YEAR)"]
            ],
            colWidths=[20*mm, 20*mm, 20*mm],
            style=TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONT', (0, 1), (-1, 1), 'Helvetica', 6),
                ('LINEBELOW', (0, 0), (2, 0), 1, colors.black),
            ])
        )
        
        # Create name of carrier field
        carrier_label = Paragraph("Name of carrier", normal_style)
        carrier_field = Table(
            [[""]],
            colWidths=[60*mm],
            style=TableStyle([
                ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
            ])
        )
        carrier_subtext = Paragraph("(NAME OF CARRIER OR CARRIERS)", ParagraphStyle('CarrierSubtext', parent=normal_style, fontSize=6, alignment=1))
        
        # Create main office address field
        address_label = Paragraph("Main office address", normal_style)
        address_field = Table(
            [[""]],
            colWidths=[60*mm],
            style=TableStyle([
                ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
            ])
        )
        address_subtext = Paragraph("(MAIN OFFICE ADDRESS)", ParagraphStyle('AddressSubtext', parent=normal_style, fontSize=6, alignment=1))
        
        # Create 24-hour period starting time field
        starting_time_label = Paragraph("24-hour period starting time", normal_style)
        
        # Total miles driving today field
        miles_label = Paragraph("Total miles driving today", normal_style)
        miles_field = Table(
            [[""]],
            colWidths=[40*mm],
            style=TableStyle([
                ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
            ])
        )
        miles_subtext = Paragraph("(TOTAL MILES DRIVING TODAY)", ParagraphStyle('MilesSubtext', parent=normal_style, fontSize=6, alignment=1))
        
        # Driver's Daily Log title
        log_title = Paragraph("<b>DRIVER'S DAILY LOG</b>", ParagraphStyle('LogTitle', parent=normal_style, fontSize=12, alignment=1))
        log_subtitle = Paragraph("(ONE CALENDAR DAY — 24 HOURS)", ParagraphStyle('LogSubtitle', parent=normal_style, fontSize=8, alignment=1))
        
        # Original/Duplicate instructions
        original_text = Paragraph("<b>ORIGINAL</b> — Submit to carrier within 13 days", ParagraphStyle('OriginalText', parent=normal_style, fontSize=8))
        duplicate_text = Paragraph("<b>DUPLICATE</b> — Driver retains possession for eight days", ParagraphStyle('DuplicateText', parent=normal_style, fontSize=8))
        
        # Truck/tractor number field
        vehicle_label = Paragraph("Truck or tractor and trailer number", normal_style)
        vehicle_field = Table(
            [[""]],
            colWidths=[60*mm],
            style=TableStyle([
                ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
            ])
        )
        vehicle_subtext = Paragraph("VEHICLE NUMBERS—(SHOW EACH UNIT)", ParagraphStyle('VehicleSubtext', parent=normal_style, fontSize=6, alignment=1))
        
        # Certification section
        certification_text = Paragraph("I certify that these entries are true and correct", ParagraphStyle('CertText', parent=normal_style, fontSize=8))
        signature_field = Table(
            [[""]],
            colWidths=[60*mm],
            style=TableStyle([
                ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
            ])
        )
        signature_subtext = Paragraph("(DRIVER'S SIGNATURE IN FULL)", ParagraphStyle('SignatureSubtext', parent=normal_style, fontSize=6, alignment=1))
        
        # Driver's certification label
        cert_label = Paragraph("Driver's signature/ certification", normal_style)
        
        # Co-driver field
        codriver_label = Paragraph("Name of co-driver", normal_style)
        codriver_field = Table(
            [[""]],
            colWidths=[60*mm],
            style=TableStyle([
                ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
            ])
        )
        codriver_subtext = Paragraph("(NAME OF CO. DRIVER)", ParagraphStyle('CodriverSubtext', parent=normal_style, fontSize=6, alignment=1))
        
        # Total hours field
        total_hours_label = Paragraph("TOTAL HOURS", ParagraphStyle('TotalHoursLabel', parent=normal_style, fontSize=8, alignment=1))
        
        # Create the header layout to match the image exactly
        header_data = [
            # Row 1: Top labels
            [
                [date_label], 
                [miles_label], 
                [vehicle_label]
            ],
            # Row 2: Title row
            [
                # Date fields
                [
                    date_field
                ],
                # Center column - Title
                [
                    log_title,
                    log_subtitle,
                    Spacer(1, 2*mm),
                    miles_field,
                    miles_subtext
                ],
                # Right column - Original/Duplicate text
                [
                    original_text,
                    duplicate_text,
                    Spacer(1, 2*mm),
                    vehicle_field,
                    vehicle_subtext
                ]
            ],
            # Row 3: Carrier/Certification
            [
                # Left column - Carrier info
                [
                    carrier_label,
                    carrier_field,
                    carrier_subtext
                ],
                # Center column - Certification
                [
                    certification_text,
                    signature_field,
                    signature_subtext
                ],
                # Right column - Driver's certification
                [
                    cert_label
                ]
            ],
            # Row 4: Address/Co-driver
            [
                # Left column - Address
                [
                    address_label,
                    address_field,
                    address_subtext
                ],
                # Center column - Co-driver
                [
                    codriver_field,
                    codriver_subtext
                ],
                # Right column - Name of co-driver/Total hours
                [
                    codriver_label,
                    total_hours_label
                ]
            ]
        ]
        
        header_table = Table(
            header_data,
            colWidths=[60*mm, 70*mm, 60*mm],
            style=TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ])
        )
        
        elements.append(header_table)
        elements.append(Spacer(1, 5*mm))  # Add space after header
    
    def _calculate_status_hours(self, segments: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate the total hours spent in each status based on schedule segments.
        
        Args:
            segments: The schedule segments to analyze
            
        Returns:
            Dictionary mapping status types to total hours
        """
        status_hours = {status: 0.0 for status in self.STATUS_TYPES}
        
        for segment in segments:
            segment_type = segment.get('type', '').lower()
            start_time = segment.get('start_time')
            end_time = segment.get('end_time')
            
            if not segment_type or not start_time or not end_time:
                continue
                
            # Map the segment type to a status
            status_mapping = {
                'drive': 'Driving',
                'break': 'Off Duty',
                'rest': 'Off Duty',
                'sleep': 'Sleeper Berth',
                'on_duty': 'On Duty (Not Driving)',
                'off_duty': 'Off Duty'
            }
            
            status = status_mapping.get(segment_type)
            if not status:
                continue
                
            # Calculate hours spent in this segment
            duration = end_time - start_time
            hours = duration.total_seconds() / 3600.0
            
            # Add to the status hours
            status_hours[status] += hours
            
        return status_hours

    def _add_driver_log_grid(self, elements: List) -> None:
        """Add the driver log grid section to match FMCSA format."""
        # Create the grid table
        grid_data = []
        
        # Add midnight/noon markers
        hour_row = [""]  # First cell is empty
        for hour in range(self.HOURS_IN_DAY + 1):
            if hour == 0:
                hour_marker = "Midnight"
            elif hour == 12:
                hour_marker = "Noon"
            else:
                hour_marker = str(hour)
            hour_row.append(hour_marker)
            
        grid_data.append(hour_row)
            
        # Add status rows with grid
        for status in self.STATUS_TYPES:
            status_row = [status]
            # Add empty cells for the grid
            for _ in range(self.HOURS_IN_DAY + 1):
                status_row.append("")
            grid_data.append(status_row)
            
        # Define column widths - first column wider for labels
        first_col_width = 25*mm
        hour_col_width = self.GRID_WIDTH / self.HOURS_IN_DAY
        col_widths = [first_col_width] + [hour_col_width] * (self.HOURS_IN_DAY + 1)
        
        # Define row heights - first row shorter for hour labels
        first_row_height = 10*mm
        status_row_height = self.GRID_HEIGHT / len(self.STATUS_TYPES)
        remarks_row_height = 15*mm  # Make remarks row taller
        
        row_heights = [first_row_height]
        for i in range(len(self.STATUS_TYPES)):
            if self.STATUS_TYPES[i] == "REMARKS":
                row_heights.append(remarks_row_height)
            else:
                row_heights.append(status_row_height)
        
        # Create grid table style with vertical and horizontal lines
        grid_style = TableStyle([
            # Align hour labels
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Format first column status labels
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONT', (0, 1), (0, -1), 'Helvetica-Bold', 8),
            
            # Add grid lines
            ('GRID', (1, 1), (-1, -2), 0.5, colors.black),
            
            # Add stronger vertical lines for 4-hour intervals
            ('LINEAFTER', (4, 1), (4, -2), 1.0, colors.black),  # 4 AM
            ('LINEAFTER', (8, 1), (8, -2), 1.0, colors.black),  # 8 AM
            ('LINEAFTER', (12, 1), (12, -2), 1.0, colors.black),  # 12 PM
            ('LINEAFTER', (16, 1), (16, -2), 1.0, colors.black),  # 4 PM
            ('LINEAFTER', (20, 1), (20, -2), 1.0, colors.black),  # 8 PM
            
            # Add bottom border for REMARKS row
            ('LINEBELOW', (0, -1), (-1, -1), 1.0, colors.black),
        ])
        
        # Create the grid table
        grid_table = Table(
            grid_data,
            colWidths=col_widths,
            rowHeights=row_heights,
            style=grid_style
        )
        
        elements.append(grid_table)
        
        # Get schedule segments to draw status lines
        segments = self._get_schedule_segments()
        
        # If we have segments, add the StatusLineDrawer flowable
        if segments:
            try:
                # Create a StatusLineDrawer to draw the status lines on the grid
                today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow_midnight = today_midnight + timedelta(days=1)
                
                status_drawer = StatusLineDrawer(
                    schedule_segments=segments,
                    start_time=today_midnight,
                    end_time=tomorrow_midnight
                )
                
                # Important: Position the drawer correctly
                # The drawer will be added at the exact position where it's inserted in the elements list
                elements.append(status_drawer)
            except Exception as e:
                # If there's an error drawing status lines, continue without them
                print(f"Error drawing status lines: {e}")
                
        # Add space for the remarks section
        elements.append(Spacer(1, 5*mm))
    
    def _get_schedule_segments(self) -> List[Dict[str, Any]]:
        """
        Get a list of schedule segments from the schedule data.
        
        Returns:
            List of schedule segments with type, start_time, and end_time
        """
        if not self.schedule_data:
            return []
            
        segments = self.schedule_data.get('segments', [])
        
        # Normalize the segments to ensure they have the required fields
        normalized_segments = []
        for segment in segments:
            normalized_segment = {}
            
            # Get the activity type
            activity_type = segment.get('type', '').lower()
            normalized_segment['type'] = activity_type
            
            # Get start and end times
            start_str = segment.get('start')
            end_str = segment.get('end')
            
            if not start_str or not end_str:
                continue
                
            try:
                # Parse the ISO format strings to datetime objects
                start_time = datetime.fromisoformat(start_str)
                end_time = datetime.fromisoformat(end_str)
                
                normalized_segment['start_time'] = start_time
                normalized_segment['end_time'] = end_time
                
                normalized_segments.append(normalized_segment)
            except (ValueError, TypeError):
                # Skip segments with invalid datetime formats
                continue
                
        return normalized_segments
        
    def _add_remarks_section(self, elements: List) -> None:
        """Add remarks and shipping documents section."""
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # Create remarks section
        remarks_label = Paragraph("REMARKS", normal_style)
        
        # Pro or Shipping Number - use trip data if available
        shipping_no = ""
        if hasattr(self.trip, 'shipping_number') and self.trip.shipping_number:
            shipping_no = self.trip.shipping_number
        
        pro_label = Paragraph("Pro or Shipping No. " + shipping_no, ParagraphStyle('ProLabel', parent=normal_style, fontSize=8))
        
        remarks_data = [
            [remarks_label, ""],
            ["", pro_label]
        ]
        
        remarks_table = Table(
            remarks_data,
            colWidths=[25*mm, 155*mm],
            rowHeights=[10*mm, 30*mm],
            style=TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('VALIGN', (1, 1), (1, 1), 'BOTTOM'),
                ('ALIGN', (1, 1), (1, 1), 'LEFT'),
                ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 8),
                ('BOX', (0, 0), (-1, -1), 1.0, colors.black),
                ('LINEAFTER', (0, 0), (0, -1), 1.0, colors.black),
            ])
        )
        
        elements.append(remarks_table)
    
    @classmethod
    def generate_trip_log(cls, trip_id: int) -> bytes:
        """
        Generate a driver log PDF for a specific trip.
        
        Args:
            trip_id: The Trip ID to generate a log for
            
        Returns:
            PDF file as bytes
        """
        try:
            trip = Trip.objects.get(id=trip_id)
        except Trip.DoesNotExist:
            raise ValueError(f"Trip with ID {trip_id} not found")
            
        generator = cls(trip)
        return generator.generate_pdf() 