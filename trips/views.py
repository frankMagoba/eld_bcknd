from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, schema
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse, JsonResponse
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Trip
from .serializers import (
    TripSerializer, 
    HOSCalculationRequestSerializer,
    HOSCalculationResponseSerializer
)
from .utils.hos_calculator import HOSCalculator
from .services.pdf_generator import PDFGenerator

# Create your views here.

class TripViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing Trip instances.
    Provides 'list', 'create', 'retrieve', 'update', and 'destroy' actions.
    """
    queryset = Trip.objects.all().order_by('-created_at')
    serializer_class = TripSerializer

class HOSCalculationView(APIView):
    """
    API view for calculating Hours of Service (HOS) information
    """
    @swagger_auto_schema(
        request_body=HOSCalculationRequestSerializer,
        responses={200: HOSCalculationResponseSerializer},
        operation_description="Calculate HOS information for a trip"
    )
    def post(self, request, format=None):
        """
        Calculate HOS information for a trip
        """
        serializer = HOSCalculationRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            # Extract validated data
            origin = serializer.validated_data.get('origin')
            destination = serializer.validated_data.get('destination')
            estimated_duration = serializer.validated_data.get('estimated_duration')
            start_time = serializer.validated_data.get('start_time')
            current_cycle_used = serializer.validated_data.get('current_cycle_used', 0)
            previous_drives = serializer.validated_data.get('previous_drives', [])
            
            # Validate previous_drives data if provided
            for drive in previous_drives:
                if 'start_time' not in drive or 'end_time' not in drive:
                    return Response(
                        {'error': 'Each previous drive must have start_time and end_time fields'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Call the HOSCalculator to get optimal schedule
            result = HOSCalculator.calculate_optimal_schedule(
                origin=origin,
                destination=destination,
                estimated_duration=estimated_duration,
                start_time=start_time,
                current_cycle_used=current_cycle_used
            )
            
            # Validate and return the response
            response_serializer = HOSCalculationResponseSerializer(data=result)
            if response_serializer.is_valid():
                return Response(response_serializer.validated_data)
            else:
                # This should not happen if calculate_optimal_schedule is implemented correctly
                return Response(
                    {'error': 'Internal error formatting response', 'details': response_serializer.errors},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_description="Generate a driver log PDF for a specific trip",
    manual_parameters=[
        openapi.Parameter(
            name='trip_id',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="ID of the trip to generate a log for",
            required=True
        ),
        openapi.Parameter(
            name='carrier_name',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Name of the carrier company",
            required=False
        ),
        openapi.Parameter(
            name='office_address',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Main office address",
            required=False
        ),
        openapi.Parameter(
            name='vehicle_number',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Truck or tractor and trailer number",
            required=False
        ),
        openapi.Parameter(
            name='co_driver_name',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Name of co-driver (if applicable)",
            required=False
        )
    ],
    responses={
        200: openapi.Response(
            description="Base64 encoded PDF data",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'pdf_data': openapi.Schema(type=openapi.TYPE_STRING),
                    'filename': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: "Bad request",
        404: "Trip not found"
    }
)
@api_view(['GET'])
def generate_log(request):
    """
    Generate a driver log PDF for a specific trip and return it as base64 encoded data.
    
    Query Parameters:
        trip_id: ID of the trip to generate a log for
        carrier_name: Name of the carrier company
        office_address: Main office address
        vehicle_number: Truck or tractor and trailer number
        co_driver_name: Name of co-driver (if applicable)
    
    Returns:
        JSON with base64 encoded PDF data
    """
    trip_id = request.query_params.get('trip_id')
    
    if not trip_id:
        return JsonResponse(
            {'error': 'trip_id parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        trip_id = int(trip_id)
    except ValueError:
        return JsonResponse(
            {'error': 'trip_id must be an integer'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get optional parameters with defaults
    carrier_name = request.query_params.get('carrier_name', 'Transport Company')
    office_address = request.query_params.get('office_address', '123 Trucking Lane, Anytown, USA')
    vehicle_number = request.query_params.get('vehicle_number', '')
    co_driver_name = request.query_params.get('co_driver_name', '')
    
    try:
        # Generate PDF using our service with additional parameters
        pdf_data = PDFGenerator.generate_trip_log(
            trip_id=trip_id,
            carrier_name=carrier_name,
            office_address=office_address,
            vehicle_number=vehicle_number,
            co_driver_name=co_driver_name
        )
        
        # Convert PDF to base64
        import base64
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        # Return JSON response with base64 data
        return JsonResponse({
            'pdf_data': pdf_base64,
            'filename': f'driver_log_trip_{trip_id}.pdf'
        })
    
    except Trip.DoesNotExist:
        return JsonResponse(
            {'error': f'Trip with ID {trip_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        # Handle the ValueError from PDFGenerator
        if str(e).startswith('Trip with ID'):
            return JsonResponse(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        # Print the error for debugging
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
