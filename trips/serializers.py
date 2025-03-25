from rest_framework import serializers
from .models import Trip

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ['id', 'current_location', 'pickup_location', 'dropoff_location', 
                  'current_cycle_used', 'shipping_number', 'created_at']
        read_only_fields = ['id', 'created_at']

class HOSCalculationRequestSerializer(serializers.Serializer):
    """Serializer for Hours of Service calculation requests"""
    origin = serializers.CharField(help_text="Origin location")
    destination = serializers.CharField(help_text="Destination location")
    estimated_duration = serializers.FloatField(help_text="Estimated trip duration in hours")
    start_time = serializers.DateTimeField(help_text="Trip start time")
    current_cycle_used = serializers.IntegerField(
        default=0, 
        min_value=0, 
        max_value=70,
        help_text="Hours used in the current 70-hour/8-day cycle"
    )
    
    # Optional fields for previous drives in the current duty period
    previous_drives = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of previous driving periods with start/end times"
    )

class BreakSerializer(serializers.Serializer):
    """Serializer for break information"""
    break_type = serializers.CharField()
    reason = serializers.CharField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

class RestPeriodSerializer(serializers.Serializer):
    """Serializer for rest period information"""
    rest_type = serializers.CharField()
    reason = serializers.CharField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

class RemainingTimeSerializer(serializers.Serializer):
    """Serializer for remaining time information"""
    remaining_cycle_hours = serializers.FloatField()
    remaining_driving_hours = serializers.FloatField()
    remaining_duty_window_hours = serializers.FloatField()

class ScheduleSegmentSerializer(serializers.Serializer):
    """Serializer for schedule segments"""
    type = serializers.CharField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    duration_hours = serializers.FloatField()
    
    # Fields for drive segments
    start_location = serializers.CharField(required=False)
    end_location = serializers.CharField(required=False)
    
    # Fields for break/rest segments
    location = serializers.CharField(required=False)
    reason = serializers.CharField(required=False)

class HOSDataSerializer(serializers.Serializer):
    """Serializer for HOS compliance data"""
    trip_start_time = serializers.DateTimeField()
    trip_end_time = serializers.DateTimeField()
    trip_duration_hours = serializers.FloatField()
    cycle_compliant = serializers.BooleanField()
    driving_compliant = serializers.BooleanField()
    duty_window_compliant = serializers.BooleanField()
    required_breaks = BreakSerializer(many=True)
    required_rest_periods = RestPeriodSerializer(many=True)
    current_cycle_hours = serializers.FloatField()
    updated_cycle_hours = serializers.FloatField()
    remaining_before_trip = RemainingTimeSerializer()

class HOSCalculationResponseSerializer(serializers.Serializer):
    """Serializer for Hours of Service calculation responses"""
    origin = serializers.CharField()
    destination = serializers.CharField()
    total_duration_hours = serializers.FloatField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    schedule = ScheduleSegmentSerializer(many=True)
    hos_data = HOSDataSerializer() 