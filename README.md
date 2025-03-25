# ELD Trip Log API

A Django REST API for managing trip data in an Electronic Logging Device (ELD) system.

## Setup

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
3. Install dependencies: `pip install -r requirements.txt`
4. Create the PostgreSQL database:
   ```sql
   CREATE DATABASE idrive;
   ```
5. Run migrations: `python manage.py migrate`
6. Create a superuser: `python manage.py createsuperuser`
7. Run the server: `python manage.py runserver`

## Testing the API

A test script is included to help you test the API endpoints:

1. Start the Django server: `python manage.py runserver`
2. In a new terminal window, run: `./test_api.sh`

The script will:
- List all trips
- Create a new trip
- Get details of the created trip
- Update the trip with new data
- Partially update the trip
- List all trips again to show the changes

## Hours of Service (HOS) Features

This API includes Hours of Service (HOS) compliance features based on FMCSA regulations:

- **11-hour driving limit**: A driver may drive a maximum of 11 hours after 10 consecutive hours off duty.
- **14-hour on-duty limit**: A driver may not drive beyond the 14th consecutive hour after coming on duty.
- **30-minute break requirement**: A driver must take a 30-minute break after 8 cumulative hours of driving.
- **70-hour/8-day limit**: A driver may not drive after 70 hours on duty in 8 consecutive days.

### HOS Calculator

The `HOSCalculator` class provides the following functionality:

- Calculate remaining drive time (cycle hours, driving hours, duty window hours)
- Calculate required breaks based on trip duration
- Enforce HOS limits for a trip
- Generate an optimal driving schedule with breaks and rest periods

### HOS API Endpoint

The API provides an endpoint for calculating HOS information:

**POST /api/calculate_hos/**

Request body:
```json
{
  "origin": "New York",
  "destination": "Boston",
  "estimated_duration": 5.0,
  "start_time": "2023-03-25T12:00:00Z",
  "current_cycle_used": 20
}
```

Response:
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
    "updated_cycle_hours": 25,
    "remaining_before_trip": {
      "remaining_cycle_hours": 50,
      "remaining_driving_hours": 11,
      "remaining_duty_window_hours": 14
    }
  }
}
```

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

The API can generate FMCSA-compliant driver logs in PDF format based on trip data and HOS calculations.
The generated PDF contains:

- Driver and carrier information
- 24-hour grid showing duty status changes
- Visual representation of driving periods, breaks, and rest periods
- Space for remarks and shipping documents
- Certification section

The PDF is returned as an attachment with appropriate headers for download.

## Trip Model Fields

- `current_location`: Current location of the vehicle (string)
- `pickup_location`: Pickup location (string)
- `dropoff_location`: Dropoff location (string)
- `current_cycle_used`: Hours used in the current cycle (integer)
- `created_at`: Timestamp when the trip was created (auto-generated)

## API Documentation

Interactive API documentation is available at:

- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`

## Authentication

The API uses token-based authentication. To access protected endpoints, include an Authorization header:

```
Authorization: Token your_token_here
```

## CORS Configuration

CORS is configured to allow requests from all origins. In a production environment, this should be limited to specific origins. 