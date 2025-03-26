# ELD Route Planner Backend API

A Django REST API for handling route planning, Hours of Service (HOS) calculations, and driver log generation in an Electronic Logging Device (ELD) system.

## Key Features

- **Trip Management**: Create, read, update, and delete trip records
- **Hours of Service Calculation**: Calculate required breaks and rest periods based on FMCSA regulations
- **Route Planning**: Process location data for route optimization
- **Driver Log Generation**: Create FMCSA-compliant electronic driver logs
- **RESTful API**: Well-documented endpoints with Swagger/ReDoc integration

## FMCSA Compliance

The API implements the following FMCSA Hours of Service regulations:

- **11-hour driving limit**: A driver may drive a maximum of 11 hours after 10 consecutive hours off duty
- **14-hour on-duty limit**: A driver may not drive beyond the 14th consecutive hour after coming on duty
- **30-minute break requirement**: A driver must take a 30-minute break after 8 cumulative hours of driving
- **70-hour/8-day limit**: A driver may not drive after 70 hours on duty in 8 consecutive days

## API Endpoints

### Trip Management

- **List all trips**: `GET /api/trips/`
- **Create a new trip**: `POST /api/trips/`
- **Retrieve a trip**: `GET /api/trips/{id}/`
- **Update a trip**: `PUT /api/trips/{id}/`
- **Partially update a trip**: `PATCH /api/trips/{id}/`
- **Delete a trip**: `DELETE /api/trips/{id}/`

### Hours of Service (HOS)

- **Calculate HOS**: `POST /api/calculate_hos/`

### Driver Log Generation

- **Generate PDF log**: `GET /api/generate_log/?trip_id={id}`

## Setup and Installation

1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate on macOS/Linux
   source venv/bin/activate
   
   # Activate on Windows
   venv\Scripts\activate
   ```
3. Install dependencies: 
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   ```bash
   # Copy example env file
   cp .env.example .env
   
   # Edit with your database credentials
   nano .env
   ```
5. Run migrations: 
   ```bash
   python manage.py migrate
   ```
6. Start the development server: 
   ```bash
   python manage.py runserver
   ```

## HOS Calculation Example

The `HOSCalculator` generates optimal driving schedules with required breaks:

```json
{
  "origin": "New York",
  "destination": "Boston",
  "total_duration_hours": 5.0,
  "start_time": "2023-03-25T12:00:00Z",
  "end_time": "2023-03-25T17:00:00Z",
  "schedule": [
    {
      "type": "drive",
      "start_time": "2023-03-25T12:00:00Z",
      "end_time": "2023-03-25T17:00:00Z",
      "duration_hours": 5.0,
      "start_location": "New York",
      "end_location": "Boston"
    }
  ],
  "hos_data": {
    "trip_start_time": "2023-03-25T12:00:00Z",
    "trip_end_time": "2023-03-25T17:00:00Z",
    "trip_duration_hours": 5.0,
    "cycle_compliant": true,
    "driving_compliant": true,
    "duty_window_compliant": true,
    "required_breaks": [],
    "required_rest_periods": [],
    "current_cycle_hours": 20,
    "updated_cycle_hours": 25
  }
}
```

## Driver Log Generation

The API generates FMCSA-compliant driver logs in PDF format with:

- Driver and carrier information
- 24-hour grid showing duty status changes
- Visual representation of driving periods, breaks, and rest periods
- Space for remarks and shipping documents
- Certification section

## API Documentation

Interactive API documentation is available at:

- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`

## Technologies Used

- Django and Django REST Framework
- PostgreSQL database
- PDF generation for driver logs
- Swagger/ReDoc for API documentation
- Authentication with token-based system
- Docker and Docker Compose for containerization

## Security

- Token-based authentication
- Environment variable configuration
- CORS protection

## Further Resources

- [FMCSA ELD Regulations](https://www.fmcsa.dot.gov/hours-service/elds/electronic-logging-devices)
- [Hours of Service Rules](https://www.fmcsa.dot.gov/regulations/hours-of-service)
- [Django REST Framework Documentation](https://www.django-rest-framework.org/) 