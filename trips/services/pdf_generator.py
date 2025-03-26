import io
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Flowable
from reportlab.pdfgen import canvas
from PyPDF2 import PdfMerger

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
    
    def __init__(self, trip: Trip, schedule_data: Optional[Dict[str, Any]] = None, 
                 carrier_name: str = "Transport Company", 
                 office_address: str = "123 Trucking Lane, Anytown, USA",
                 vehicle_number: str = "",
                 co_driver_name: str = ""):
        """
        Initialize the PDF Generator.
        
        Args:
            trip: The Trip model instance
            schedule_data: Optional precomputed schedule data (if None, will be calculated)
            carrier_name: Name of the carrier company
            office_address: Main office address
            vehicle_number: Truck or tractor number
            co_driver_name: Name of co-driver, if applicable
        """
        self.trip = trip
        self.schedule_data = schedule_data
        self.carrier_name = carrier_name
        self.office_address = office_address
        self.vehicle_number = vehicle_number
        self.co_driver_name = co_driver_name
        
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
        For trips spanning multiple days, generates multiple log sheets.
        
        Returns:
            PDF file as bytes
        """
        # Determine if we need multiple log sheets
        segments = self._get_schedule_segments()
        days_covered = self._get_days_covered(segments)
        
        if len(days_covered) <= 1:
            # Just one day - generate a single log sheet
            return self._generate_single_day_log(days_covered[0] if days_covered else datetime.now().date())
        else:
            # Multiple days - generate multiple log sheets and combine them
            return self._generate_multi_day_logs(days_covered)
    
    def _get_schedule_segments(self) -> List[Dict[str, Any]]:
        """
        Extract schedule segments from the schedule data.
        
        Returns:
            List of schedule segments (drive, rest, break periods)
        """
        if not self.schedule_data or 'schedule' not in self.schedule_data:
            return []
            
        return self.schedule_data.get('schedule', [])
    
    def _get_days_covered(self, segments: List[Dict[str, Any]]) -> List[datetime.date]:
        """
        Determine which days are covered by the schedule segments.
        
        Args:
            segments: Schedule segments to analyze
            
        Returns:
            List of dates (sorted) that the segments cover
        """
        if not segments:
            return [datetime.now().date()]
            
        # Get all unique days from segment start and end times
        days_set = set()
        
        for segment in segments:
            start_time = segment.get('start_time')
            end_time = segment.get('end_time')
            
            if start_time:
                days_set.add(start_time.date())
            if end_time:
                days_set.add(end_time.date())
                
        # Sort days chronologically
        return sorted(list(days_set))
    
    def _generate_multi_day_logs(self, days: List[datetime.date]) -> bytes:
        """
        Generate multiple log sheets, one for each day, and combine them.
        
        Args:
            days: List of days to generate logs for
            
        Returns:
            Combined PDF as bytes
        """
        # Use PyPDF2 to merge multiple PDFs
        merger = PdfMerger()
        
        for day in days:
            # Generate log for this day
            day_log = self._generate_single_day_log(day)
            
            # Add to the merger
            merger.append(io.BytesIO(day_log))
        
        # Get the combined PDF
        output = io.BytesIO()
        merger.write(output)
        merger.close()
        
        # Return the bytes
        output.seek(0)
        return output.getvalue()
    
    def _generate_single_day_log(self, day: datetime.date) -> bytes:
        """
        Generate a single day's log sheet.
        
        Args:
            day: The date to generate the log for
            
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
        
        # Content elements
        elements = []
        
        # Add header section matching the exact design
        self._add_header(elements, day)
        
        # Add driver log grid
        self._add_driver_log_grid(elements, day)
        
        # Add remarks section
        self._add_remarks_section(elements, day)
        
        # Build the PDF
        doc.build(elements)
        
        # Get the PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data

    def _add_header(self, elements: List, day: datetime.date) -> None:
        """
        Add the header section to the PDF, matching the FMCSA log form.
        
        Args:
            elements: List of elements to add to
            day: The date for this log sheet
        """
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # Format date fields
        month = day.strftime("%m")
        day_num = day.strftime("%d")
        year = day.strftime("%Y")
        
        # Calculate miles driven for this day
        miles_driven = self._calculate_miles_for_day(day)
        
        # Create date field
        date_label = Paragraph("Date", normal_style)
        date_field = Table(
            [
                [month, day_num, year],
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
            [[self.carrier_name]],
            colWidths=[60*mm],
            style=TableStyle([
                ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
            ])
        )
        carrier_subtext = Paragraph("(NAME OF CARRIER OR CARRIERS)", ParagraphStyle('CarrierSubtext', parent=normal_style, fontSize=6, alignment=1))
        
        # Create main office address field
        address_label = Paragraph("Main office address", normal_style)
        address_field = Table(
            [[self.office_address]],
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
            [[f"{miles_driven:.1f}"]],
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
            [[self.vehicle_number]],
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
            [[self.co_driver_name]],
            colWidths=[60*mm],
            style=TableStyle([
                ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
            ])
        )
        codriver_subtext = Paragraph("(NAME OF CO. DRIVER)", ParagraphStyle('CodriverSubtext', parent=normal_style, fontSize=6, alignment=1))
        
        # Calculate total hours for this day
        total_hours = self._calculate_total_hours_for_day(day)
        
        # Total hours field
        total_hours_label = Paragraph(f"TOTAL HOURS: {total_hours:.1f}", ParagraphStyle('TotalHoursLabel', parent=normal_style, fontSize=8, alignment=1))
        
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

    def _calculate_miles_for_day(self, day: datetime.date) -> float:
        """
        Calculate the miles driven for a specific day.
        
        Args:
            day: The day to calculate for
            
        Returns:
            Miles driven on that day
        """
        # Get segments for this day only
        day_segments = self._get_segments_for_day(day)
        
        # Sum up miles for driving segments
        total_miles = 0.0
        for segment in day_segments:
            if segment.get('type', '').lower() == 'drive':
                # Estimate miles based on segment duration (assuming average speed of 55 mph)
                start_time = segment.get('start_time')
                end_time = segment.get('end_time')
                
                if start_time and end_time:
                    duration_hours = (end_time - start_time).total_seconds() / 3600.0
                    # Assume average speed of 55 mph
                    miles = duration_hours * 55.0
                    total_miles += miles
        
        return total_miles
    
    def _calculate_total_hours_for_day(self, day: datetime.date) -> float:
        """
        Calculate the total hours for all activities on a specific day.
        
        Args:
            day: The day to calculate for
            
        Returns:
            Total hours on that day
        """
        # Get segments for this day only
        day_segments = self._get_segments_for_day(day)
        
        # Sum up hours for all segments
        total_hours = 0.0
        for segment in day_segments:
            start_time = segment.get('start_time')
            end_time = segment.get('end_time')
            
            if start_time and end_time:
                # Adjust times to be within this day only
                day_start = datetime.combine(day, datetime.min.time())
                day_end = datetime.combine(day, datetime.max.time())
                
                # If segment starts before this day, use day start
                if start_time.date() < day:
                    start_time = day_start
                    
                # If segment ends after this day, use day end
                if end_time.date() > day:
                    end_time = day_end
                
                duration_hours = (end_time - start_time).total_seconds() / 3600.0
                total_hours += duration_hours
        
        return total_hours

    def _get_segments_for_day(self, day: datetime.date) -> List[Dict[str, Any]]:
        """
        Filter segments to include only those on a specific day.
        
        Args:
            day: The day to filter segments for
            
        Returns:
            List of segments on that day
        """
        all_segments = self._get_schedule_segments()
        day_segments = []
        
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        for segment in all_segments:
            start_time = segment.get('start_time')
            end_time = segment.get('end_time')
            
            if not start_time or not end_time:
                continue
            
            # Check if segment overlaps with this day
            if (start_time <= day_end and end_time >= day_start):
                # Create a copy of the segment
                day_segment = segment.copy()
                
                # Adjust segment to be within day boundaries
                if start_time < day_start:
                    day_segment['start_time'] = day_start
                if end_time > day_end:
                    day_segment['end_time'] = day_end
                    
                day_segments.append(day_segment)
                
        return day_segments

    def _add_driver_log_grid(self, elements: List, day: datetime.date) -> None:
        """
        Add the driver log grid section to match FMCSA format.
        
        Args:
            elements: List of elements to add to
            day: The date for this log sheet
        """
        # Get schedule segments for this day
        segments = self._get_segments_for_day(day)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        # Create a custom flowable to draw both grid and status lines
        class DriverLogGrid(Flowable):
            def __init__(self, pdf_generator, segments, day_start, day_end):
                Flowable.__init__(self)
                self.pdf_generator = pdf_generator
                self.segments = segments
                self.day_start = day_start
                self.day_end = day_end
                
                # Dimensions for the complete grid with labels
                self.width = pdf_generator.GRID_WIDTH + 25*mm
                self.height = pdf_generator.GRID_HEIGHT + 10*mm + 15*mm  # Include hours row and remarks
                
                # Status rows (excluding REMARKS)
                self.status_rows = [
                    "Off Duty",
                    "Sleeper Berth",
                    "Driving",
                    "On Duty (Not Driving)"
                ]
                
            def draw(self):
                canvas = self.canv
                hour_labels_height = 10*mm
                remarks_height = 15*mm
                
                # Draw hour labels
                canvas.setFont('Helvetica', 8)
                canvas.setFillColor(colors.black)
                
                # Draw column for status labels
                label_width = 25*mm
                
                # Calculate grid dimensions
                grid_width = self.pdf_generator.GRID_WIDTH
                grid_height = self.pdf_generator.GRID_HEIGHT
                hour_width = grid_width / 24
                row_height = grid_height / 4  # 4 status rows
                
                # Draw hour markers
                for hour in range(25):  # 0-24 hours
                    x = label_width + hour * hour_width
                    
                    # Draw vertical line
                    canvas.setLineWidth(0.5)
                    if hour % 4 == 0:
                        canvas.setLineWidth(1.0)  # Stronger line every 4 hours
                    
                    # Draw vertical grid line
                    canvas.line(x, hour_labels_height, x, hour_labels_height + grid_height)
                    
                    # Draw hour label
                    if hour == 0:
                        label = "Midnight"
                    elif hour == 12:
                        label = "Noon"
                    elif hour == 24:
                        label = "Midnight"
                    else:
                        label = str(hour)
                    
                    canvas.drawCentredString(x, hour_labels_height - 8, label)
                
                # Draw status rows and horizontal grid lines
                for i, status in enumerate(self.status_rows):
                    y = hour_labels_height + grid_height - (i + 1) * row_height
                    
                    # Draw label
                    canvas.setFont('Helvetica-Bold', 8)
                    canvas.drawString(2, y + row_height/2 - 4, status)
                    
                    # Draw horizontal grid line
                    canvas.setLineWidth(0.5)
                    canvas.line(label_width, y, label_width + grid_width, y)
                
                # Draw remarks row
                canvas.setFont('Helvetica-Bold', 8)
                canvas.drawString(2, hour_labels_height - remarks_height + 5, "REMARKS")
                
                # Draw top horizontal line
                canvas.setLineWidth(0.5)
                canvas.line(label_width, hour_labels_height + grid_height, 
                           label_width + grid_width, hour_labels_height + grid_height)
                
                # Draw status lines
                drawer = StatusLineDrawer(
                    schedule_segments=self.segments,
                    start_time=self.day_start,
                    end_time=self.day_end,
                    canvas=canvas,
                    x_offset=label_width,
                    y_offset=hour_labels_height,
                    grid_width=grid_width,
                    grid_height=grid_height
                )
                drawer.draw()
        
        # Add the driver log grid flowable to elements
        elements.append(DriverLogGrid(self, segments, day_start, day_end))
        elements.append(Spacer(1, 5*mm))

    def _add_remarks_section(self, elements: List, day: datetime.date) -> None:
        """
        Add remarks and shipping documents section.
        
        Args:
            elements: List of elements to add to
            day: The date for this log sheet
        """
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        
        # Create remarks section
        remarks_label = Paragraph("REMARKS", normal_style)
        
        # Generate remarks based on this day's activities
        remarks = self._generate_remarks_for_day(day)
        
        # Pro or Shipping Number - use trip data if available
        shipping_no = ""
        if hasattr(self.trip, 'shipping_number') and self.trip.shipping_number:
            shipping_no = self.trip.shipping_number
        
        pro_label = Paragraph("Pro or Shipping No. " + shipping_no, ParagraphStyle('ProLabel', parent=normal_style, fontSize=8))
        
        # Add locations/cities for this day
        locations_text = Paragraph(remarks, ParagraphStyle('LocationsText', parent=normal_style, fontSize=8, leading=10))
        
        remarks_data = [
            [remarks_label, locations_text],
            ["", pro_label]
        ]
        
        remarks_table = Table(
            remarks_data,
            colWidths=[25*mm, 155*mm],
            rowHeights=[30*mm, 10*mm],
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
    
    def _generate_remarks_for_day(self, day: datetime.date) -> str:
        """
        Generate remarks text for a specific day.
        
        Args:
            day: The day to generate remarks for
            
        Returns:
            Formatted remarks string
        """
        remarks = []
        
        # Add shipping information
        if self.trip.id:
            remarks.append(f"Trip #{self.trip.id}")
        
        # Add origin/destination
        remarks.append(f"From: {self.trip.current_location} To: {self.trip.dropoff_location}")
        
        # Get segments for this day
        segments = self._get_segments_for_day(day)
        
        # Add location changes based on segments
        for segment in segments:
            segment_type = segment.get('type', '').lower()
            start_time = segment.get('start_time')
            
            # Only add location remarks for driving segments
            if segment_type == 'drive' and start_time:
                time_str = start_time.strftime("%H:%M")
                remarks.append(f"{time_str} - Started driving")
                
        return "\n".join(remarks)
        
    @classmethod
    def generate_trip_log(cls, trip_id: int, 
                         carrier_name: str = "Transport Company", 
                         office_address: str = "123 Trucking Lane, Anytown, USA",
                         vehicle_number: str = "",
                         co_driver_name: str = "") -> bytes:
        """
        Generate a driver log PDF for a specific trip.
        
        Args:
            trip_id: The Trip ID to generate a log for
            carrier_name: Name of the carrier company
            office_address: Main office address
            vehicle_number: Truck or tractor number
            co_driver_name: Name of co-driver, if applicable
            
        Returns:
            PDF file as bytes
        """
        try:
            trip = Trip.objects.get(id=trip_id)
        except Trip.DoesNotExist:
            raise ValueError(f"Trip with ID {trip_id} not found")
            
        generator = cls(
            trip=trip,
            carrier_name=carrier_name,
            office_address=office_address,
            vehicle_number=vehicle_number,
            co_driver_name=co_driver_name
        )
        return generator.generate_pdf() 