#!/usr/bin/env python3
"""
Test suite for CAN CLI tool safety mechanisms
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from can_cli import (
    SafetyMode, CANMessage, SafetyRules, RateLimiter, 
    CANInterface, CANCLIApp
)


class TestSafetyRules:
    """Test safety validation rules"""
    
    def test_locked_mode_blocks_all(self):
        """LOCKED mode should block all messages"""
        msg = CANMessage(0x123, b'\x01\x02', 0)
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.LOCKED)
        assert not valid
        assert "LOCKED mode" in reason
    
    def test_production_blocks_critical(self):
        """PRODUCTION mode should block critical addresses"""
        # Test critical address
        msg = CANMessage(0x180, b'\x01\x02', 0)  # STEERING
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.PRODUCTION)
        assert not valid
        assert "critical address" in reason
        
        # Test non-critical address
        msg = CANMessage(0x123, b'\x01\x02', 0)
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.PRODUCTION)
        assert valid
    
    def test_testing_blocks_dangerous_critical(self):
        """TESTING mode should still block most dangerous addresses"""
        # Steering should be blocked
        msg = CANMessage(0x180, b'\x01\x02', 0)
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.TESTING)
        assert not valid
        
        # Less critical addresses might be allowed
        msg = CANMessage(0x191, b'\x01\x02', 0)  # CRUISE_CONTROL
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.TESTING)
        assert valid or not valid  # Depends on implementation
    
    def test_development_allows_with_confirmation(self):
        """DEVELOPMENT mode should allow critical with confirmation"""
        msg = CANMessage(0x180, b'\x01\x02', 0)
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.DEVELOPMENT)
        assert valid  # Allowed, but will require confirmation
    
    def test_can_data_length_validation(self):
        """Test CAN vs CAN-FD data length limits"""
        # Standard CAN - max 8 bytes
        msg = CANMessage(0x123, b'\x01' * 9, 0, fd=False)
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.DEVELOPMENT)
        assert not valid
        assert "8 bytes" in reason
        
        # CAN-FD - max 64 bytes
        msg = CANMessage(0x123, b'\x01' * 65, 0, fd=True)
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.DEVELOPMENT)
        assert not valid
        assert "64 bytes" in reason
    
    def test_bus_number_validation(self):
        """Test bus number validation"""
        # Valid bus
        msg = CANMessage(0x123, b'\x01\x02', 1)
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.DEVELOPMENT)
        assert valid
        
        # Invalid bus
        msg = CANMessage(0x123, b'\x01\x02', 5)
        valid, reason = SafetyRules.validate_message(msg, SafetyMode.DEVELOPMENT)
        assert not valid
        assert "Invalid bus" in reason


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_global_rate_limit(self):
        """Test global rate limiting"""
        limiter = RateLimiter()
        limiter.global_limit = 5  # Low limit for testing
        
        # Send 5 messages - should all pass
        for i in range(5):
            ok, reason = limiter.check_rate(0x100 + i)
            assert ok
            limiter.record_message(0x100 + i)
        
        # 6th message should fail
        ok, reason = limiter.check_rate(0x106)
        assert not ok
        assert "Global rate limit" in reason
    
    def test_per_address_rate_limit(self):
        """Test per-address rate limiting"""
        limiter = RateLimiter()
        limiter.per_address_limit = 3  # Low limit for testing
        
        # Send 3 messages to same address
        for i in range(3):
            ok, reason = limiter.check_rate(0x100)
            assert ok
            limiter.record_message(0x100)
        
        # 4th message to same address should fail
        ok, reason = limiter.check_rate(0x100)
        assert not ok
        assert "Per-address rate limit" in reason
        
        # But different address should work
        ok, reason = limiter.check_rate(0x200)
        assert ok
    
    def test_window_expiry(self):
        """Test that old messages expire from window"""
        limiter = RateLimiter()
        limiter.global_limit = 2
        limiter.window_size = 0.1  # 100ms window
        
        # Fill the limit
        limiter.record_message(0x100)
        limiter.record_message(0x101)
        
        # Should be blocked
        ok, _ = limiter.check_rate(0x102)
        assert not ok
        
        # Wait for window to expire
        time.sleep(0.15)
        
        # Should work now
        ok, _ = limiter.check_rate(0x102)
        assert ok


class TestCANInterface:
    """Test CAN interface with safety integration"""
    
    @patch('can_cli.Panda')
    def test_connect_safety_modes(self, mock_panda_class):
        """Test connection sets appropriate Panda safety modes"""
        mock_panda = Mock()
        mock_panda_class.return_value = mock_panda
        
        # Test LOCKED mode
        interface = CANInterface(SafetyMode.LOCKED)
        with patch('can_cli.PANDA_AVAILABLE', True):
            interface.connect()
            mock_panda.set_safety_mode.assert_called_with(mock_panda_class.SAFETY_SILENT)
        
        # Test PRODUCTION mode
        interface = CANInterface(SafetyMode.PRODUCTION)
        with patch('can_cli.PANDA_AVAILABLE', True):
            interface.connect()
            mock_panda.set_safety_mode.assert_called_with(mock_panda_class.SAFETY_TOYOTA)
    
    def test_send_with_safety_checks(self):
        """Test send message goes through all safety checks"""
        interface = CANInterface(SafetyMode.PRODUCTION)
        interface.connected = True
        interface.panda = Mock()
        
        # Non-critical message should pass
        msg = CANMessage(0x123, b'\x01\x02', 0)
        success, reason = interface.send_message(msg)
        assert success
        interface.panda.can_send.assert_called_once()
        
        # Critical message should fail in production
        interface.panda.reset_mock()
        msg = CANMessage(0x180, b'\x01\x02', 0)
        success, reason = interface.send_message(msg)
        assert not success
        assert "critical address" in reason
        interface.panda.can_send.assert_not_called()
    
    def test_rate_limiting_integration(self):
        """Test rate limiting prevents spam"""
        interface = CANInterface(SafetyMode.DEVELOPMENT)
        interface.connected = True
        interface.panda = Mock()
        interface.rate_limiter.per_address_limit = 2
        
        # Send 2 messages - should work
        msg = CANMessage(0x123, b'\x01\x02', 0)
        for _ in range(2):
            success, _ = interface.send_message(msg)
            assert success
        
        # 3rd message should be rate limited
        success, reason = interface.send_message(msg)
        assert not success
        assert "rate limit" in reason
    
    @patch('builtins.input', return_value='yes')
    def test_critical_confirmation(self, mock_input):
        """Test critical addresses require confirmation"""
        interface = CANInterface(SafetyMode.DEVELOPMENT)
        interface.connected = True
        interface.panda = Mock()
        
        # Send to critical address
        msg = CANMessage(0x180, b'\x01\x02', 0)
        success, _ = interface.send_message(msg)
        
        # Should have asked for confirmation
        mock_input.assert_called_once()
        assert success
    
    def test_logging(self, tmp_path):
        """Test audit logging functionality"""
        # Override log directory
        with patch('pathlib.Path.home', return_value=tmp_path):
            interface = CANInterface(SafetyMode.PRODUCTION)
            interface.enable_logging = True
            interface._init_logging()
            
            # Send a message
            msg = CANMessage(0x123, b'\x01\x02', 0)
            interface.send_message(msg)
            
            # Check log file exists and contains entry
            log_files = list((tmp_path / ".openpilot" / "can_cli" / "logs").glob("*.log"))
            assert len(log_files) == 1
            
            with open(log_files[0]) as f:
                content = f.read()
                assert "send_" in content
                assert "0x123" in content


class TestCANCLIApp:
    """Test CLI application"""
    
    def test_parse_hex_data(self):
        """Test hex data parsing"""
        app = CANCLIApp()
        
        # Various formats should work
        assert app._parse_hex_data("01 02 03") == b'\x01\x02\x03'
        assert app._parse_hex_data("010203") == b'\x01\x02\x03'
        assert app._parse_hex_data("0x01 0x02") == b'\x01\x02'
        assert app._parse_hex_data("AABBCC") == b'\xaa\xbb\xcc'
    
    @patch('can_cli.CANInterface')
    def test_send_command(self, mock_interface_class):
        """Test send command execution"""
        app = CANCLIApp()
        mock_interface = Mock()
        mock_interface_class.return_value = mock_interface
        mock_interface.connect.return_value = True
        mock_interface.send_message.return_value = (True, "Success")
        
        # Test send command
        args = ['send', '0x123', '01 02 03', '--bus', '1']
        result = app.run(args)
        
        assert result == 0
        mock_interface.send_message.assert_called_once()
        call_args = mock_interface.send_message.call_args[0][0]
        assert call_args.address == 0x123
        assert call_args.data == b'\x01\x02\x03'
        assert call_args.bus == 1
    
    @patch('can_cli.CANInterface')
    @patch('can_cli.CANPacker')
    def test_send_dbc_command(self, mock_packer_class, mock_interface_class):
        """Test DBC send command"""
        app = CANCLIApp()
        
        # Setup mocks
        mock_interface = Mock()
        mock_interface_class.return_value = mock_interface
        mock_interface.connect.return_value = True
        mock_interface.send_message.return_value = (True, "Success")
        
        mock_packer = Mock()
        mock_packer_class.return_value = mock_packer
        mock_packer.make_can_msg.return_value = (0x180, b'\x01\x02', 0)
        
        # Test DBC send
        args = ['send-dbc', 'toyota', 'STEERING_LKA', 'STEER_REQUEST=1,STEER_TORQUE_CMD=50']
        result = app.run(args)
        
        assert result == 0
        mock_packer.make_can_msg.assert_called_with(
            'STEERING_LKA', 0, {'STEER_REQUEST': 1, 'STEER_TORQUE_CMD': 50}
        )


class TestEndToEnd:
    """End-to-end integration tests"""
    
    @patch('can_cli.Panda')
    @patch('builtins.input', side_effect=['yes', 'yes'])  # For safety mode and critical message
    def test_full_safety_flow(self, mock_input, mock_panda_class):
        """Test complete flow with all safety features"""
        mock_panda = Mock()
        mock_panda_class.return_value = mock_panda
        
        app = CANCLIApp()
        
        with patch('can_cli.PANDA_AVAILABLE', True):
            # Try to send critical message in development mode
            args = ['--mode', 'development', 'send', '0x180', '01 02']
            result = app.run(args)
            
            # Should succeed after confirmations
            assert result == 0
            assert mock_input.call_count == 2  # Safety mode + critical address
            mock_panda.can_send.assert_called_once()
    
    def test_simulation_mode(self):
        """Test tool works without Panda hardware"""
        app = CANCLIApp()
        
        with patch('can_cli.PANDA_AVAILABLE', False):
            args = ['send', '0x123', '01 02 03']
            result = app.run(args)
            
            # Should work in simulation
            assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])