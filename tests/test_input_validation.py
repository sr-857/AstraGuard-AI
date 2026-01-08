"""
Unit tests for core/input_validation.py
Tests telemetry validation, policy decision validation, and mission phase validation
"""

import pytest
from core.input_validation import (
    TelemetryData,
    PolicyDecision,
    MissionPhaseValidator,
    ValidationError,
    SeverityLevel,
    AnomalyType
)


class TestTelemetryData:
    """Test TelemetryData validation"""

    def test_validate_method_valid_data(self):
        """Test successful validation of complete telemetry data"""
        data = {
            'voltage': 12.5,
            'temperature': 25.0,
            'gyro': 45.0,
            'current': 2.1,
            'wheel_speed': 1500.0
        }

        result = TelemetryData.validate(data)

        assert isinstance(result, TelemetryData)
        assert result.voltage == 12.5
        assert result.temperature == 25.0
        assert result.gyro == 45.0
        assert result.current == 2.1
        assert result.wheel_speed == 1500.0

    def test_validate_method_missing_fields(self):
        """Test validation fails with missing required fields"""
        data = {
            'voltage': 12.5,
            'temperature': 25.0
            # Missing gyro, current, wheel_speed
        }

        with pytest.raises(ValidationError) as exc_info:
            TelemetryData.validate(data)

        assert "missing (required)" in str(exc_info.value)

    def test_validate_method_invalid_types(self):
        """Test validation fails with invalid data types"""
        data = {
            'voltage': "12.5",  # Should be numeric
            'temperature': 25.0,
            'gyro': 45.0,
            'current': 2.1,
            'wheel_speed': 1500.0
        }

        with pytest.raises(ValidationError) as exc_info:
            TelemetryData.validate(data)

        assert "expected numeric" in str(exc_info.value)

    def test_validate_method_out_of_bounds(self):
        """Test validation fails with out-of-bounds values"""
        data = {
            'voltage': 20.0,  # Too high (>15.0)
            'temperature': 25.0,
            'gyro': 45.0,
            'current': 2.1,
            'wheel_speed': 1500.0
        }

        with pytest.raises(ValidationError) as exc_info:
            TelemetryData.validate(data)

        assert "out of range" in str(exc_info.value)

    def test_validate_method_invalid_input_type(self):
        """Test validation fails with non-dict input"""
        with pytest.raises(ValidationError) as exc_info:
            TelemetryData.validate("not a dict")

        assert "must be dict" in str(exc_info.value)

    def test_bounds_constants(self):
        """Test that bounds constants are properly defined"""
        bounds = TelemetryData.BOUNDS

        assert 'voltage' in bounds
        assert 'temperature' in bounds
        assert 'gyro' in bounds
        assert 'current' in bounds
        assert 'wheel_speed' in bounds

        # Check specific bounds
        assert bounds['voltage'] == (0.0, 15.0, 'Volts')
        assert bounds['temperature'] == (-50.0, 100.0, 'Celsius')
        assert bounds['gyro'] == (-360.0, 360.0, 'deg/s')
        assert bounds['current'] == (0.0, 5.0, 'Amperes')
        assert bounds['wheel_speed'] == (0.0, 10000.0, 'RPM')

    def test_edge_case_boundary_values(self):
        """Test validation with exact boundary values"""
        data = {
            'voltage': 0.0,  # Exact lower bound
            'temperature': 100.0,  # Exact upper bound
            'gyro': -360.0,  # Exact lower bound
            'current': 5.0,  # Exact upper bound
            'wheel_speed': 10000.0  # Exact upper bound
        }

        result = TelemetryData.validate(data)
        assert isinstance(result, TelemetryData)
        assert result.voltage == 0.0
        assert result.temperature == 100.0


class TestPolicyDecision:
    """Test PolicyDecision validation"""

    def test_validate_method_valid_decision(self):
        """Test successful validation of complete policy decision"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault',
            'severity': 'HIGH',
            'recommended_action': 'Reduce power consumption',
            'detection_confidence': 0.85,
            'timestamp': '2024-01-01T12:00:00Z',
            'reasoning': 'High current draw detected'
        }

        result = PolicyDecision.validate(decision)

        assert isinstance(result, PolicyDecision)
        assert result.mission_phase == 'NOMINAL_OPS'
        assert result.anomaly_type == 'power_fault'
        assert result.severity == 'HIGH'
        assert result.recommended_action == 'Reduce power consumption'
        assert result.detection_confidence == 0.85
        assert result.timestamp == '2024-01-01T12:00:00Z'
        assert result.reasoning == 'High current draw detected'

    def test_validate_method_missing_required_fields(self):
        """Test validation fails with missing required fields"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault'
            # Missing severity, recommended_action, detection_confidence
        }

        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate(decision)

        assert "Missing fields" in str(exc_info.value)

    def test_validate_method_invalid_anomaly_type(self):
        """Test validation fails with invalid anomaly type"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'invalid_fault',  # Invalid
            'severity': 'HIGH',
            'recommended_action': 'Reduce power consumption',
            'detection_confidence': 0.85
        }

        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate(decision)

        assert "anomaly_type" in str(exc_info.value)
        assert "not in" in str(exc_info.value)

    def test_validate_method_invalid_severity(self):
        """Test validation fails with invalid severity"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault',
            'severity': 'INVALID',  # Invalid
            'recommended_action': 'Reduce power consumption',
            'detection_confidence': 0.85
        }

        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate(decision)

        assert "severity" in str(exc_info.value)
        assert "not in" in str(exc_info.value)

    def test_validate_method_invalid_confidence_range(self):
        """Test validation fails with confidence out of range"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault',
            'severity': 'HIGH',
            'recommended_action': 'Reduce power consumption',
            'detection_confidence': 1.5  # Out of range [0.0, 1.0]
        }

        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate(decision)

        assert "out of range" in str(exc_info.value)

    def test_validate_method_invalid_input_type(self):
        """Test validation fails with non-dict input"""
        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate("not a dict")

        assert "must be dict" in str(exc_info.value)

    def test_required_fields_constant(self):
        """Test that REQUIRED_FIELDS constant is properly defined"""
        required = PolicyDecision.REQUIRED_FIELDS
        assert 'mission_phase' in required
        assert 'anomaly_type' in required
        assert 'severity' in required
        assert 'recommended_action' in required
        assert 'detection_confidence' in required

    def test_valid_sets_constants(self):
        """Test that valid sets constants are properly defined"""
        assert 'HIGH' in PolicyDecision.VALID_SEVERITIES
        assert 'power_fault' in PolicyDecision.VALID_ANOMALY_TYPES
        assert 'INVALID_SEVERITY' not in PolicyDecision.VALID_SEVERITIES


class TestMissionPhaseValidator:
    """Test MissionPhaseValidator functionality"""

    def test_validate_phase_valid_phase(self):
        """Test successful validation of valid phase"""
        result = MissionPhaseValidator.validate_phase('nominal_ops')
        assert result == 'NOMINAL_OPS'

    def test_validate_phase_invalid_phase(self):
        """Test validation fails with invalid phase"""
        with pytest.raises(ValidationError) as exc_info:
            MissionPhaseValidator.validate_phase('invalid_phase')

        assert "not in" in str(exc_info.value)

    def test_validate_phase_invalid_type(self):
        """Test validation fails with non-string input"""
        with pytest.raises(ValidationError) as exc_info:
            MissionPhaseValidator.validate_phase(123)

        assert "must be string" in str(exc_info.value)

    def test_validate_transition_valid_transition(self):
        """Test successful validation of valid transition"""
        current, next_phase = MissionPhaseValidator.validate_transition(
            'LAUNCH', 'DEPLOYMENT'
        )
        assert current == 'LAUNCH'
        assert next_phase == 'DEPLOYMENT'

    def test_validate_transition_invalid_transition(self):
        """Test validation fails with invalid transition"""
        with pytest.raises(ValidationError) as exc_info:
            MissionPhaseValidator.validate_transition('LAUNCH', 'NOMINAL_OPS')

        assert "Invalid transition" in str(exc_info.value)

    def test_validate_transition_same_phase(self):
        """Test validation fails when transitioning to same phase"""
        with pytest.raises(ValidationError) as exc_info:
            MissionPhaseValidator.validate_transition('LAUNCH', 'launch')

        assert "Cannot transition" in str(exc_info.value)
        assert "to itself" in str(exc_info.value)

    def test_valid_phases_constant(self):
        """Test that VALID_PHASES constant is properly defined"""
        phases = MissionPhaseValidator.VALID_PHASES
        assert 'LAUNCH' in phases
        assert 'NOMINAL_OPS' in phases
        assert 'INVALID_PHASE' not in phases

    def test_valid_transitions_constant(self):
        """Test that VALID_TRANSITIONS constant is properly defined"""
        transitions = MissionPhaseValidator.VALID_TRANSITIONS
        assert 'LAUNCH' in transitions
        assert 'DEPLOYMENT' in transitions['LAUNCH']


class TestEnums:
    """Test enum definitions"""

    def test_severity_level_enum(self):
        """Test SeverityLevel enum values"""
        assert SeverityLevel.LOW.value == "LOW"
        assert SeverityLevel.MEDIUM.value == "MEDIUM"
        assert SeverityLevel.HIGH.value == "HIGH"
        assert SeverityLevel.CRITICAL.value == "CRITICAL"

    def test_anomaly_type_enum(self):
        """Test AnomalyType enum values"""
        assert AnomalyType.POWER_FAULT.value == "power_fault"
        assert AnomalyType.THERMAL_FAULT.value == "thermal_fault"
        assert AnomalyType.ATTITUDE_FAULT.value == "attitude_fault"
        assert AnomalyType.UNKNOWN_FAULT.value == "unknown_fault"


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple validators"""

    def test_full_telemetry_validation_workflow(self):
        """Test complete telemetry validation workflow"""
        raw_data = {
            'voltage': 12.5,
            'temperature': 25.0,
            'gyro': 45.0,
            'current': 2.1,
            'wheel_speed': 1500.0
        }

        # Validate telemetry
        telemetry = TelemetryData.validate(raw_data)
        assert isinstance(telemetry, TelemetryData)

        # Create and validate policy decision based on telemetry
        decision_data = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault',
            'severity': 'MEDIUM',
            'recommended_action': 'Monitor power consumption',
            'detection_confidence': 0.75
        }

        decision = PolicyDecision.validate(decision_data)
        assert isinstance(decision, PolicyDecision)

        # Validate phase transition
        current, next_phase = MissionPhaseValidator.validate_transition(
            'DEPLOYMENT', 'NOMINAL_OPS'
        )
        assert current == 'DEPLOYMENT'
        assert next_phase == 'NOMINAL_OPS'

    def test_error_handling_integration(self):
        """Test error handling across validators"""
        # Test telemetry validation error
        with pytest.raises(ValidationError):
            TelemetryData.validate({'voltage': 'invalid'})

        # Test policy decision validation error
        with pytest.raises(ValidationError):
            PolicyDecision.validate({'invalid': 'data'})

        # Test phase validation error
        with pytest.raises(ValidationError):
            MissionPhaseValidator.validate_phase('INVALID_PHASE')


class TestTelemetryData:
    """Test TelemetryData validation"""

    def test_validate_method_valid_data(self):
        """Test successful validation of complete telemetry data"""
        data = {
            'voltage': 12.5,
            'temperature': 25.0,
            'gyro': 45.0,
            'current': 2.1,
            'wheel_speed': 1500.0
        }

        result = TelemetryData.validate(data)

        assert isinstance(result, TelemetryData)
        assert result.voltage == 12.5
        assert result.temperature == 25.0
        assert result.gyro == 45.0
        assert result.current == 2.1
        assert result.wheel_speed == 1500.0

    def test_validate_method_missing_fields(self):
        """Test validation fails with missing required fields"""
        data = {
            'voltage': 12.5,
            'temperature': 25.0
            # Missing gyro, current, wheel_speed
        }

        with pytest.raises(ValidationError) as exc_info:
            TelemetryData.validate(data)

        assert "missing (required)" in str(exc_info.value)

    def test_validate_method_invalid_types(self):
        """Test validation fails with invalid data types"""
        data = {
            'voltage': "12.5",  # Should be numeric
            'temperature': 25.0,
            'gyro': 45.0,
            'current': 2.1,
            'wheel_speed': 1500.0
        }

        with pytest.raises(ValidationError) as exc_info:
            TelemetryData.validate(data)

        assert "expected numeric" in str(exc_info.value)

    def test_validate_method_out_of_bounds(self):
        """Test validation fails with out-of-bounds values"""
        data = {
            'voltage': 20.0,  # Too high (>15.0)
            'temperature': 25.0,
            'gyro': 45.0,
            'current': 2.1,
            'wheel_speed': 1500.0
        }

        with pytest.raises(ValidationError) as exc_info:
            TelemetryData.validate(data)

        assert "out of range" in str(exc_info.value)

    def test_validate_method_invalid_input_type(self):
        """Test validation fails with non-dict input"""
        with pytest.raises(ValidationError) as exc_info:
            TelemetryData.validate("not a dict")

        assert "must be dict" in str(exc_info.value)

    def test_bounds_constants(self):
        """Test that bounds constants are properly defined"""
        bounds = TelemetryData.BOUNDS

        assert 'voltage' in bounds
        assert 'temperature' in bounds
        assert 'gyro' in bounds
        assert 'current' in bounds
        assert 'wheel_speed' in bounds

        # Check specific bounds
        assert bounds['voltage'] == (0.0, 15.0, 'Volts')
        assert bounds['temperature'] == (-50.0, 100.0, 'Celsius')
        assert bounds['gyro'] == (-360.0, 360.0, 'deg/s')
        assert bounds['current'] == (0.0, 5.0, 'Amperes')
        assert bounds['wheel_speed'] == (0.0, 10000.0, 'RPM')

    def test_edge_case_boundary_values(self):
        """Test validation with exact boundary values"""
        data = {
            'voltage': 0.0,  # Exact lower bound
            'temperature': 100.0,  # Exact upper bound
            'gyro': -360.0,  # Exact lower bound
            'current': 5.0,  # Exact upper bound
            'wheel_speed': 10000.0  # Exact upper bound
        }

        result = TelemetryData.validate(data)
        assert isinstance(result, TelemetryData)
        assert result.voltage == 0.0
        assert result.temperature == 100.0


class TestPolicyDecision:
    """Test PolicyDecision validation"""

    def test_validate_method_valid_decision(self):
        """Test successful validation of complete policy decision"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault',
            'severity': 'HIGH',
            'recommended_action': 'Reduce power consumption',
            'detection_confidence': 0.85,
            'timestamp': '2024-01-01T12:00:00Z',
            'reasoning': 'High current draw detected'
        }

        result = PolicyDecision.validate(decision)

        assert isinstance(result, PolicyDecision)
        assert result.mission_phase == 'NOMINAL_OPS'
        assert result.anomaly_type == 'power_fault'
        assert result.severity == 'HIGH'
        assert result.recommended_action == 'Reduce power consumption'
        assert result.detection_confidence == 0.85
        assert result.timestamp == '2024-01-01T12:00:00Z'
        assert result.reasoning == 'High current draw detected'

    def test_validate_method_missing_required_fields(self):
        """Test validation fails with missing required fields"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault'
            # Missing severity, recommended_action, detection_confidence
        }

        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate(decision)

        assert "Missing fields" in str(exc_info.value)

    def test_validate_method_invalid_anomaly_type(self):
        """Test validation fails with invalid anomaly type"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'invalid_fault',  # Invalid
            'severity': 'HIGH',
            'recommended_action': 'Reduce power consumption',
            'detection_confidence': 0.85
        }

        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate(decision)

        assert "anomaly_type" in str(exc_info.value)
        assert "not in" in str(exc_info.value)

    def test_validate_method_invalid_severity(self):
        """Test validation fails with invalid severity"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault',
            'severity': 'INVALID',  # Invalid
            'recommended_action': 'Reduce power consumption',
            'detection_confidence': 0.85
        }

        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate(decision)

        assert "severity" in str(exc_info.value)
        assert "not in" in str(exc_info.value)

    def test_validate_method_invalid_confidence_range(self):
        """Test validation fails with confidence out of range"""
        decision = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault',
            'severity': 'HIGH',
            'recommended_action': 'Reduce power consumption',
            'detection_confidence': 1.5  # Out of range [0.0, 1.0]
        }

        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate(decision)

        assert "out of range" in str(exc_info.value)

    def test_validate_method_invalid_input_type(self):
        """Test validation fails with non-dict input"""
        with pytest.raises(ValidationError) as exc_info:
            PolicyDecision.validate("not a dict")

        assert "must be dict" in str(exc_info.value)

    def test_required_fields_constant(self):
        """Test that REQUIRED_FIELDS constant is properly defined"""
        required = PolicyDecision.REQUIRED_FIELDS
        assert 'mission_phase' in required
        assert 'anomaly_type' in required
        assert 'severity' in required
        assert 'recommended_action' in required
        assert 'detection_confidence' in required

    def test_valid_sets_constants(self):
        """Test that valid sets constants are properly defined"""
        assert 'HIGH' in PolicyDecision.VALID_SEVERITIES
        assert 'power_fault' in PolicyDecision.VALID_ANOMALY_TYPES
        assert 'INVALID_SEVERITY' not in PolicyDecision.VALID_SEVERITIES


class TestMissionPhaseValidator:
    """Test MissionPhaseValidator functionality"""

    def test_validate_phase_valid_phase(self):
        """Test successful validation of valid phase"""
        result = MissionPhaseValidator.validate_phase('nominal_ops')
        assert result == 'NOMINAL_OPS'

    def test_validate_phase_invalid_phase(self):
        """Test validation fails with invalid phase"""
        with pytest.raises(ValidationError) as exc_info:
            MissionPhaseValidator.validate_phase('invalid_phase')

        assert "not in" in str(exc_info.value)

    def test_validate_phase_invalid_type(self):
        """Test validation fails with non-string input"""
        with pytest.raises(ValidationError) as exc_info:
            MissionPhaseValidator.validate_phase(123)

        assert "must be string" in str(exc_info.value)

    def test_validate_transition_valid_transition(self):
        """Test successful validation of valid transition"""
        current, next_phase = MissionPhaseValidator.validate_transition(
            'LAUNCH', 'DEPLOYMENT'
        )
        assert current == 'LAUNCH'
        assert next_phase == 'DEPLOYMENT'

    def test_validate_transition_invalid_transition(self):
        """Test validation fails with invalid transition"""
        with pytest.raises(ValidationError) as exc_info:
            MissionPhaseValidator.validate_transition('LAUNCH', 'NOMINAL_OPS')

        assert "Invalid transition" in str(exc_info.value)

    def test_validate_transition_same_phase(self):
        """Test validation fails when transitioning to same phase"""
        with pytest.raises(ValidationError) as exc_info:
            MissionPhaseValidator.validate_transition('LAUNCH', 'launch')

        assert "Cannot transition" in str(exc_info.value)
        assert "to itself" in str(exc_info.value)

    def test_valid_phases_constant(self):
        """Test that VALID_PHASES constant is properly defined"""
        phases = MissionPhaseValidator.VALID_PHASES
        assert 'LAUNCH' in phases
        assert 'NOMINAL_OPS' in phases
        assert 'INVALID_PHASE' not in phases

    def test_valid_transitions_constant(self):
        """Test that VALID_TRANSITIONS constant is properly defined"""
        transitions = MissionPhaseValidator.VALID_TRANSITIONS
        assert 'LAUNCH' in transitions
        assert 'DEPLOYMENT' in transitions['LAUNCH']


class TestEnums:
    """Test enum definitions"""

    def test_severity_level_enum(self):
        """Test SeverityLevel enum values"""
        assert SeverityLevel.LOW.value == "LOW"
        assert SeverityLevel.MEDIUM.value == "MEDIUM"
        assert SeverityLevel.HIGH.value == "HIGH"
        assert SeverityLevel.CRITICAL.value == "CRITICAL"

    def test_anomaly_type_enum(self):
        """Test AnomalyType enum values"""
        assert AnomalyType.POWER_FAULT.value == "power_fault"
        assert AnomalyType.THERMAL_FAULT.value == "thermal_fault"
        assert AnomalyType.ATTITUDE_FAULT.value == "attitude_fault"
        assert AnomalyType.UNKNOWN_FAULT.value == "unknown_fault"


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple validators"""

    def test_full_telemetry_validation_workflow(self):
        """Test complete telemetry validation workflow"""
        raw_data = {
            'voltage': 12.5,
            'temperature': 25.0,
            'gyro': 45.0,
            'current': 2.1,
            'wheel_speed': 1500.0
        }

        # Validate telemetry
        telemetry = TelemetryData.validate(raw_data)
        assert isinstance(telemetry, TelemetryData)

        # Create and validate policy decision based on telemetry
        decision_data = {
            'mission_phase': 'NOMINAL_OPS',
            'anomaly_type': 'power_fault',
            'severity': 'MEDIUM',
            'recommended_action': 'Monitor power consumption',
            'detection_confidence': 0.75
        }

        decision = PolicyDecision.validate(decision_data)
        assert isinstance(decision, PolicyDecision)

        # Validate phase transition
        current, next_phase = MissionPhaseValidator.validate_transition(
            'DEPLOYMENT', 'NOMINAL_OPS'
        )
        assert current == 'DEPLOYMENT'
        assert next_phase == 'NOMINAL_OPS'

    def test_error_handling_integration(self):
        """Test error handling across validators"""
        # Test telemetry validation error
        with pytest.raises(ValidationError):
            TelemetryData.validate({'voltage': 'invalid'})

        # Test policy decision validation error
        with pytest.raises(ValidationError):
            PolicyDecision.validate({'invalid': 'data'})

        # Test phase validation error
        with pytest.raises(ValidationError):
            MissionPhaseValidator.validate_phase('INVALID_PHASE')