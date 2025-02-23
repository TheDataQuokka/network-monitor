"""
Network Uptime Monitor Version 1
-------------------------

A robust network connectivity monitoring tool that performs continuous ping tests
and logs detailed network performance metrics. This tool is designed for network
administrators, researchers, and anyone needing to monitor network reliability
and performance over time.

Key Features:
- Configurable ping targets and parameters
- Cross-platform compatibility (Windows/Unix)
- Detailed logging of all connection attempts
- Separate logging for connection failures
- Automatic log rotation to manage disk space
- Performance metrics including packet loss, latency, and jitter
- Configurable test duration (unlimited or time-limited)
- Error handling and detailed error logging

Usage:
1. Configure settings in ping_config.ini (created automatically if not present)
2. Run the script: python NetworkuptimeMonitorV2.py
3. Select test duration when prompted
4. Monitor results in real-time and in log files

Author: TheDataQuokka
License: GNU General Public License v3.0
Copyright (C) 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import os
import time
import subprocess
import re
import traceback
from datetime import datetime
import configparser
from dataclasses import dataclass
import sys
from typing import List, Optional

# Configuration file path
CONFIG_FILE = 'ping_config.ini'

# Pre-compile regex patterns for performance optimization
# These patterns match the output format of ping commands across different platforms
REPLY_TIME_PATTERN = re.compile(r"time[=<]\s*(\d+)ms")
PACKET_COUNT_PATTERN = re.compile(r"Sent = (\d+), Received = (\d+), Lost = (\d+)")
RTT_STATS_PATTERN = re.compile(r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms")

@dataclass
class PingResult:
    """
    Data class that encapsulates all results from a ping test.
    This provides a more structured and type-safe way to handle test results
    compared to using tuples.

    Attributes:
        connected (bool): True if at least one ping reply was received
        loss_percent (float): Percentage of packets lost during the test
        sent (int): Number of packets sent
        received (int): Number of packets received
        lost (int): Number of packets lost
        min_time (Optional[int]): Minimum round-trip time in milliseconds
        max_time (Optional[int]): Maximum round-trip time in milliseconds
        avg_time (Optional[int]): Average round-trip time in milliseconds
        jitter (float): Average variation in ping times (ms)
        test_duration (float): Total duration of the test in seconds
        ping_results (List[Optional[int]]): Individual ping times (None for timeouts)
        error (str): Any error messages encountered during the test
    """
    connected: bool
    loss_percent: float
    sent: int
    received: int
    lost: int
    min_time: Optional[int]
    max_time: Optional[int]
    avg_time: Optional[int]
    jitter: float
    test_duration: float
    ping_results: List[Optional[int]]
    error: str

class LogManager:
    """
    Handles log file management with automatic rotation to prevent excessive disk usage.
    
    Features:
    - Automatic log rotation when file size exceeds MAX_LOG_SIZE
    - Maintains one backup file (.1 extension) when rotating
    - Ensures proper file handling and cleanup
    
    Attributes:
        MAX_LOG_SIZE (int): Maximum size of log file before rotation (10MB)
        filename (str): Path to the log file
        file: File handle for the current log file
    """
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self, filename):
        """
        Initialize the log manager with a specific log file.
        
        Args:
            filename (str): Path to the log file
        """
        self.filename = filename
        self.file = None
        self._open_log()

    def _open_log(self):
        """Opens or reopens the log file for appending."""
        if self.file:
            self.file.close()
        self.file = open(self.filename, "a")

    def _check_rotation(self):
        """
        Checks if log rotation is needed and performs rotation if necessary.
        Rotation occurs when the file size exceeds MAX_LOG_SIZE.
        """
        if os.path.getsize(self.filename) > self.MAX_LOG_SIZE:
            self.file.close()
            backup = f"{self.filename}.1"
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(self.filename, backup)
            self._open_log()

    def write(self, entry):
        """
        Writes an entry to the log file, handling rotation if needed.
        
        Args:
            entry (str): The log entry to write
        """
        self._check_rotation()
        self.file.write(entry)
        self.file.flush()

    def close(self):
        """Closes the log file handle properly."""
        if self.file:
            self.file.close()

def validate_config(config):
    """
    Validates configuration values to ensure they are within acceptable ranges.
    
    Checks:
    - IP address format
    - Ping count range (1-100)
    - Timeout range (100ms-60000ms)
    - Interval range (0.1s-60s)
    
    Args:
        config (configparser.SectionProxy): Configuration section to validate
        
    Raises:
        ValueError: If any configuration value is invalid
        SystemExit: If validation fails
    """
    try:
        # Basic IP address format validation
        if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', config['target']):
            raise ValueError("Invalid IP address format")
        
        count = int(config['count'])
        if not (1 <= count <= 100):
            raise ValueError("Count must be between 1 and 100")
        
        timeout = int(config['timeout'])
        if not (100 <= timeout <= 60000):
            raise ValueError("Timeout must be between 100ms and 60000ms")
        
        interval = float(config['desired_interval'])
        if not (0.1 <= interval <= 60):
            raise ValueError("Interval must be between 0.1 and 60 seconds")
            
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

def load_config():
    """
    Loads or creates configuration from CONFIG_FILE.
    
    Creates a new configuration file with default settings if none exists.
    Validates all configuration values before returning.
    
    Default settings:
      - target: The IP address to ping (default: 8.8.8.8)
      - count: Number of ping packets to send (default: 10)
      - timeout: Ping timeout in milliseconds (default: 1000)
      - desired_interval: Time in seconds between ping tests (default: 0.1)
      - all_attempts_log: Filename for the full log
      - lost_connection_log: Filename for logging failed connectivity attempts
      - error_log: Filename for logging error tracebacks
    
    Returns:
        configparser.SectionProxy: Validated configuration settings
    """
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        config['DEFAULT'] = {
            'target': '8.8.8.8',
            'count': '10',
            'timeout': '1000',
            'desired_interval': '0.1',
            'all_attempts_log': 'all_attempts.log',
            'lost_connection_log': 'lost_connection.log',
            'error_log': 'error.log'
        }
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE)
    
    validate_config(config['DEFAULT'])
    return config['DEFAULT']

def get_ping_command(target: str, count: int, timeout: str) -> List[str]:
    """
    Constructs the appropriate ping command for the current operating system.
    
    Args:
        target (str): IP address or hostname to ping
        count (int): Number of ping packets to send
        timeout (str): Timeout value in milliseconds
    
    Returns:
        List[str]: Command list ready for subprocess.run()
    """
    if os.name == 'nt':  # Windows
        return ["ping", "-n", str(count), "-w", timeout, target]
    else:  # Unix-like systems
        return ["ping", "-c", str(count), "-W", str(int(timeout)/1000), target]

# Load configuration and assign global variables.
config = load_config()
TARGET = config.get('target', '8.8.8.8')
COUNT = config.getint('count', 10)
TIMEOUT = config.get('timeout', '1000')  # as string for subprocess
DESIRED_INTERVAL = config.getfloat('desired_interval', 0.1)
ALL_ATTEMPTS_LOG = config.get('all_attempts_log', 'all_attempts.log')
LOST_CONNECTION_LOG = config.get('lost_connection_log', 'lost_connection.log')
ERROR_LOG = config.get('error_log', 'error.log')

def get_test_duration():
    """
    Prompts the user to select a test duration preference.
    
    Options:
    0 - Run indefinitely until interrupted
    1 - Run for 30 minutes
    2 - Run for a custom duration
    
    Returns:
        Optional[float]: Test duration in minutes (None for unlimited)
    """
    while True:
        print("\nSelect test duration:")
        print("0 - Unlimited")
        print("1 - 30 minutes (Recommended)")
        print("2 - Custom duration")
        
        try:
            choice = int(input("Enter your choice (0-2): "))
            if choice == 0:
                return None  # Unlimited
            elif choice == 1:
                return 30  # 30 minutes
            elif choice == 2:
                while True:
                    try:
                        minutes = float(input("Enter custom duration in minutes: "))
                        if minutes > 0:
                            return minutes
                        print("Please enter a positive number.")
                    except ValueError:
                        print("Please enter a valid number.")
            else:
                print("Please enter 0, 1, or 2.")
        except ValueError:
            print("Please enter a valid number.")

def ping_test() -> PingResult:
    """
    Performs a complete ping test using platform-specific commands.
    
    This function:
    1. Executes the ping command appropriate for the OS
    2. Captures and parses the command output
    3. Calculates various network metrics:
       - Connectivity status
       - Packet loss statistics
       - Round-trip time statistics
       - Jitter (variation in ping times)
    4. Handles and logs any errors encountered
    
    Returns:
        PingResult: Complete results of the ping test
    """
    start_time = time.time()
    try:
        # Build the ping command using configured parameters.
        cmd = get_ping_command(TARGET, COUNT, TIMEOUT)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        end_time = time.time()
        test_duration = end_time - start_time

        output = result.stdout
        error = result.stderr if result.stderr else ""

        # Parse individual ping results.
        ping_results = []
        for line in output.splitlines():
            if "Reply from" in line:
                # Look for "time=9ms" or "time<1ms"
                match_time = REPLY_TIME_PATTERN.search(line)
                if match_time:
                    ping_results.append(int(match_time.group(1)))
                else:
                    ping_results.append(None)
            elif "Request timed out" in line:
                ping_results.append(None)
        valid_times = [pt for pt in ping_results if pt is not None]
        
        # Calculate jitter from consecutive valid ping times.
        if len(valid_times) > 1:
            jitter = sum(abs(valid_times[i+1] - valid_times[i]) for i in range(len(valid_times) - 1)) / (len(valid_times) - 1)
        else:
            jitter = 0

        # Extract summary packet counts.
        match_counts = PACKET_COUNT_PATTERN.search(output)
        if match_counts:
            sent = int(match_counts.group(1))
            received = int(match_counts.group(2))
            lost = int(match_counts.group(3))
            loss_percent = (lost / sent) * 100 if sent else 100.0
        else:
            sent = COUNT
            received = len(valid_times)
            lost = COUNT - len(valid_times)
            loss_percent = (lost / COUNT) * 100

        # Extract round-trip time statistics.
        match_times = RTT_STATS_PATTERN.search(output)
        if match_times:
            min_time = int(match_times.group(1))
            max_time = int(match_times.group(2))
            avg_time = int(match_times.group(3))
        else:
            if valid_times:
                min_time = min(valid_times)
                max_time = max(valid_times)
                avg_time = sum(valid_times) // len(valid_times)
            else:
                min_time = max_time = avg_time = None

        connected = received > 0

        return PingResult(
            connected=connected,
            loss_percent=loss_percent,
            sent=sent,
            received=received,
            lost=lost,
            min_time=min_time,
            max_time=max_time,
            avg_time=avg_time,
            jitter=jitter,
            test_duration=test_duration,
            ping_results=ping_results,
            error=error
        )
    except Exception as e:
        end_time = time.time()
        test_duration = end_time - start_time
        # Capture full traceback for debugging.
        error_message = traceback.format_exc()
        # Log the error traceback to the separate error log.
        with open(ERROR_LOG, "a") as err_log:
            err_log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error in ping_test:\n{error_message}\n")
        return PingResult(
            connected=False,
            loss_percent=100.0,
            sent=COUNT,
            received=0,
            lost=COUNT,
            min_time=None,
            max_time=None,
            avg_time=None,
            jitter=0,
            test_duration=test_duration,
            ping_results=[],
            error=error_message
        )

def log_status(log_all: LogManager, log_fail: LogManager, result: PingResult):
    """
    Creates and writes detailed log entries for ping test results.
    
    Formats a comprehensive log entry including:
    - Timestamp
    - Connection status
    - Packet loss statistics
    - Round-trip time statistics
    - Jitter measurements
    - Test duration
    - Individual ping results
    - Any errors encountered
    
    The entry is written to the main log file and printed to console.
    If the connection failed, it's also written to the failure log.
    
    Args:
        log_all (LogManager): Manager for the main log file
        log_fail (LogManager): Manager for the connection failure log file
        result (PingResult): Complete results from the ping test
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    status_str = "Connected" if result.connected else "Disconnected"
    
    entry = f"{timestamp} - {status_str}: {result.loss_percent:.1f}% packet loss (Sent: {result.sent}, Received: {result.received}, Lost: {result.lost})"
    if result.min_time is not None:
        entry += f" Min: {result.min_time}ms, Max: {result.max_time}ms, Avg: {result.avg_time}ms"
    entry += f" | Jitter: {result.jitter:.1f}ms, Duration: {result.test_duration*1000:.1f}ms"
    results_str = ", ".join(str(x) if x is not None else "timeout" for x in result.ping_results)
    entry += f" | Ping Results: [{results_str}]"
    if result.error:
        entry += f" | Error: {result.error.strip()}"
    entry += "\n"

    log_all.write(entry)
    print(entry)
    if not result.connected:
        log_fail.write(entry)

def main():
    """
    Main program loop that orchestrates the network monitoring process.
    
    This function:
    1. Gets the desired test duration from the user
    2. Initializes log managers
    3. Enters the main monitoring loop:
       - Performs ping tests at regular intervals
       - Logs results
       - Maintains timing between tests
    4. Handles cleanup when complete
    
    The loop continues until either:
    - The specified duration is reached
    - The user interrupts with Ctrl+C
    - An unhandled error occurs
    """
    duration_minutes = get_test_duration()
    start_time = time.time()
    
    log_all = LogManager(ALL_ATTEMPTS_LOG)
    log_fail = LogManager(LOST_CONNECTION_LOG)
    
    try:
        while True:
            # Check if we've exceeded the duration
            if duration_minutes is not None:
                elapsed_minutes = (time.time() - start_time) / 60
                if elapsed_minutes >= duration_minutes:
                    print(f"\nTest completed after {elapsed_minutes:.1f} minutes.")
                    break
            
            result = ping_test()
            log_status(log_all, log_fail, result)
            sleep_time = max(0, DESIRED_INTERVAL - result.test_duration)
            time.sleep(sleep_time)
    finally:
        log_all.close()
        log_fail.close()

if __name__ == '__main__':
    try:
        print("Commence test...")
        main()
    except KeyboardInterrupt:
        print("\nScript terminated by user.")
    except Exception:
        # Catch any unforeseen errors in main and log them.
        with open(ERROR_LOG, "a") as err_log:
            err_log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Fatal error in main:\n{traceback.format_exc()}\n")
        raise
