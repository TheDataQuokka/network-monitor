"""
Network Log Reader & Plotter Version 1
-------------------------

A comprehensive network log analysis tool that processes and visualizes network
performance data from log files. This tool is designed for network administrators,
researchers, and anyone needing to analyze network performance metrics over time.

Key Features:
- Interactive chart type selection for each metric
- Automatic gap detection and segmentation
- Configurable minimum segment length filtering
- Time series visualization of network metrics
- Summary histograms with statistical insights
- Automated LLM prompt generation for analysis
- 30-minute data sample extraction

Usage:
1. Run the script: python LogReader.py
2. Follow the interactive prompts

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

import re
import sys
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import tkinter as tk
from tkinter import filedialog


class LogReader:
    """
    A class for reading, parsing, and visualizing network performance log files.
    
    Features:
    - File selection via GUI dialog
    - Regex-based log parsing
    - Data segmentation and filtering
    - Interactive visualization options
    - Statistical analysis and reporting
    - LLM-ready data extraction
    
    The class processes log files containing network performance metrics and
    provides various visualization and analysis tools to help understand the
    network's behavior over time.
    """
    
    # Pre-compile regex pattern for parsing log entries
    # Format: timestamp - status: loss% (stats) Min/Max/Avg | Jitter/Duration | Results
    LOG_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+) - '
        r'Connected: (?P<packet_loss>[\d.]+)% packet loss '
        r'\(Sent: (?P<sent>\d+), Received: (?P<received>\d+), Lost: (?P<lost>\d+)\) '
        r'Min: (?P<min>\d+)ms, Max: (?P<max>\d+)ms, Avg: (?P<avg>\d+)ms \| '
        r'Jitter: (?P<jitter>[\d.]+)ms, Duration: (?P<duration>[\d.]+)ms \| '
        r'Ping Results: \[(?P<ping_results>.*?)\]$'
    )
    
    def __init__(self, log_file_path=None):
        """
        Initialize the LogReader with an optional log file path.
        
        Args:
            log_file_path (str, optional): Path to the log file. If not provided,
                                         a file dialog will be shown.
        
        Raises:
            SystemExit: If no file is selected in the dialog
        """
        self.log_file_path = log_file_path or self.choose_file()
        if not self.log_file_path:
            print("No file selected. Exiting.")
            sys.exit(1)
            
        # Initialize data containers
        self.timestamps = []
        self.packet_losses = []
        self.avg_pings = []
        self.jitters = []
        self.detailed_logs = []
        self.segments = []
        
        self.parse_log()

    def choose_file(self):
        """
        Opens a file dialog for selecting a log file.
        
        Returns:
            str: Selected file path or None if cancelled
        """
        root = tk.Tk()
        root.withdraw()
        return filedialog.askopenfilename(
            title="Select log file",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )
    
    def parse_log(self):
        """
        Parses the log file and stores data into instance variables.
        
        This method:
        1. Reads the log file line by line
        2. Matches each line against LOG_PATTERN
        3. Extracts and processes numeric and timestamp values
        4. Handles special cases like timeouts
        5. Stores processed data in instance variables
        
        Raises:
            FileNotFoundError: If the log file doesn't exist
            Exception: For any parsing errors, which are logged
        """
        try:
            with open(self.log_file_path, 'r') as logfile:
                for line in logfile:
                    line = line.strip()
                    if not line:
                        continue  # Skip empty lines
                    
                    match = self.LOG_PATTERN.match(line)
                    if not match:
                        continue  # Skip non-matching lines
                    
                    data = match.groupdict()
                    try:
                        # Parse timestamp and numeric metrics
                        timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                        packet_loss = float(data['packet_loss'])
                        sent = int(data['sent'])
                        received = int(data['received'])
                        lost = int(data['lost'])
                        min_ping = int(data['min'])
                        max_ping = int(data['max'])
                        avg_ping = int(data['avg'])
                        jitter = float(data['jitter'])
                        duration = float(data['duration'])
                        
                        # Process individual ping results, handling timeouts
                        ping_results_raw = data['ping_results']
                        ping_results = []
                        for token in ping_results_raw.split(','):
                            token = token.strip().lower()
                            if token == 'timeout':
                                ping_results.append(None)
                            else:
                                try:
                                    ping_results.append(int(token))
                                except ValueError:
                                    ping_results.append(None)
                        
                        # Store parsed data in respective containers
                        self.timestamps.append(timestamp)
                        self.packet_losses.append(packet_loss)
                        self.avg_pings.append(avg_ping)
                        self.jitters.append(jitter)
                        
                        self.detailed_logs.append({
                            'timestamp': timestamp,
                            'packet_loss': packet_loss,
                            'sent': sent,
                            'received': received,
                            'lost': lost,
                            'min': min_ping,
                            'max': max_ping,
                            'avg': avg_ping,
                            'jitter': jitter,
                            'duration': duration,
                            'ping_results': ping_results
                        })
                    except Exception as e:
                        print(f"Error parsing line: {line}\nException: {e}")
        except FileNotFoundError:
            print("Error: The selected file was not found.")
            sys.exit(1)
    
    def chunk_data(self):
        """
        Splits the dataset into segments based on time gaps.
        
        This method:
        1. Identifies gaps > 60 seconds between consecutive timestamps
        2. Creates separate segments for data before and after gaps
        3. Prevents misleading visualizations across large time gaps
        
        Returns:
            list: A list of dictionaries, each containing segmented data
                  with timestamps and corresponding metrics
        """
        segments = []
        if not self.timestamps:
            return segments
        
        start_idx = 0
        for i in range(1, len(self.timestamps)):
            gap = (self.timestamps[i] - self.timestamps[i - 1]).total_seconds()
            if gap > 60:
                seg = {
                    'timestamps': self.timestamps[start_idx:i],
                    'packet_losses': self.packet_losses[start_idx:i],
                    'avg_pings': self.avg_pings[start_idx:i],
                    'jitters': self.jitters[start_idx:i],
                    'detailed_logs': self.detailed_logs[start_idx:i]
                }
                segments.append(seg)
                start_idx = i
        # Add the final segment
        seg = {
            'timestamps': self.timestamps[start_idx:],
            'packet_losses': self.packet_losses[start_idx:],
            'avg_pings': self.avg_pings[start_idx:],
            'jitters': self.jitters[start_idx:],
            'detailed_logs': self.detailed_logs[start_idx:]
        }
        segments.append(seg)
        self.segments = segments
        return segments

    def filter_segments(self, min_duration_minutes):
        """
        Filters segments based on minimum duration threshold.
        
        Args:
            min_duration_minutes (float): Minimum duration in minutes for a segment
                                        to be retained
        
        Returns:
            list: Filtered list of segments meeting the duration threshold
        """
        if min_duration_minutes <= 0:
            return self.segments
        
        new_segments = []
        threshold_secs = min_duration_minutes * 60
        for seg in self.segments:
            ts = seg['timestamps']
            if len(ts) < 2:
                continue
            duration = (ts[-1] - ts[0]).total_seconds()
            if duration >= threshold_secs:
                new_segments.append(seg)
        self.segments = new_segments
        return new_segments

    def plot_metric(self, ax, segments, metric_key, chart_type, color, label):
        """
        Plots a single metric across all segments on the provided axis.
        
        Args:
            ax (matplotlib.axes.Axes): The axis to plot on
            segments (list): List of segmented data
            metric_key (str): Key for the metric to plot ('avg_pings', 'jitters', 
                            or 'packet_losses')
            chart_type (str): '1' for line chart, '2' for bar chart
            color (str): Color to use for the plot
            label (str): Label for the legend
        """
        first_seg = True
        for seg in segments:
            x_data = seg['timestamps']
            # Select the correct metric data based on metric_key
            if metric_key == 'avg_pings':
                y_data = seg['avg_pings']
            elif metric_key == 'jitters':
                y_data = seg['jitters']
            elif metric_key == 'packet_losses':
                y_data = seg['packet_losses']
            else:
                continue
            
            if not x_data:
                continue
            
            if chart_type == '2':  # Bar chart
                x_num = mdates.date2num(x_data)
                bar_width = 0.0002  # Adjust width for visibility
                ax.bar(x_num, y_data, width=bar_width, color=color,
                       label=label if first_seg else None)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            else:  # Line chart
                ax.plot(x_data, y_data, '-o', color=color, linewidth=2, markersize=4,
                        label=label if first_seg else None)
            first_seg = False
        ax.grid(True)

    def plot_time_series(self, chart_type_ping, chart_type_jitter, chart_type_loss):
        """
        Creates a time series visualization for network performance metrics.
        
        This method generates three subplots showing:
        1. Average ping over time
        2. Jitter over time
        3. Packet loss percentage over time
        
        Each metric can be displayed as either a line or bar chart based on user
        preferences.
        
        Args:
            chart_type_ping (str): Chart type for ping ('1'=line, '2'=bar)
            chart_type_jitter (str): Chart type for jitter
            chart_type_loss (str): Chart type for packet loss
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        
        self.plot_metric(ax1, self.segments, 'avg_pings', chart_type_ping, 'blue', 'Average Ping (ms)')
        ax1.set_ylabel('ms')
        ax1.set_title('Time Series: Average Ping')
        ax1.legend()
        
        self.plot_metric(ax2, self.segments, 'jitters', chart_type_jitter, 'green', 'Jitter (ms)')
        ax2.set_ylabel('ms')
        ax2.set_title('Time Series: Jitter')
        ax2.legend()
        
        self.plot_metric(ax3, self.segments, 'packet_losses', chart_type_loss, 'red', 'Packet Loss (%)')
        ax3.set_ylabel('%')
        ax3.set_title('Time Series: Packet Loss')
        ax3.set_xlabel('Timestamp')
        ax3.legend()
        
        plt.tight_layout()
        plt.show()
    
    def plot_histograms(self):
        """
        Generates summary histograms for network performance metrics.
        
        Creates three histograms showing the distribution of:
        1. Individual ping times (including timeout count)
        2. Jitter values
        3. Packet loss percentages
        
        Each histogram includes descriptive statistics and annotations
        to aid in interpretation.
        """
        all_ping_values = []
        all_jitter_values = []
        all_packet_loss_values = []
        timeout_count = 0
        
        # Collect values for histograms from detailed log entries
        for record in self.detailed_logs:
            for ping_val in record['ping_results']:
                if ping_val is None:
                    timeout_count += 1
                else:
                    all_ping_values.append(ping_val)
            all_jitter_values.append(record['jitter'])
            all_packet_loss_values.append(record['packet_loss'])
        
        fig, axs = plt.subplots(3, 1, figsize=(10, 12))
        
        # Ping Histogram with timeout count
        if all_ping_values:
            bins_ping = range(min(all_ping_values), max(all_ping_values) + 2)
            axs[0].hist(all_ping_values, bins=bins_ping, color='blue', alpha=0.7, edgecolor='black')
            axs[0].set_xlabel('Ping Time (ms)')
            axs[0].set_ylabel('Frequency')
            axs[0].set_title(f'Histogram of Ping Times (Timeouts: {timeout_count})')
            axs[0].text(0.95, 0.95,
                        "Distribution of ping response times.",
                        transform=axs[0].transAxes, fontsize=9, va='top', ha='right',
                        bbox=dict(boxstyle="round", fc="w"))
        else:
            axs[0].text(0.5, 0.5, "No numeric ping results to display.", ha='center', va='center')
        
        # Jitter Histogram
        if all_jitter_values:
            axs[1].hist(all_jitter_values, bins=10, color='green', alpha=0.7, edgecolor='black')
            axs[1].set_xlabel('Jitter (ms)')
            axs[1].set_ylabel('Frequency')
            axs[1].set_title('Histogram of Jitter Values')
            axs[1].text(0.95, 0.95,
                        "Variability in latency.",
                        transform=axs[1].transAxes, fontsize=9, va='top', ha='right',
                        bbox=dict(boxstyle="round", fc="w"))
        else:
            axs[1].text(0.5, 0.5, "No jitter data to display.", ha='center', va='center')
        
        # Packet Loss Histogram
        if all_packet_loss_values:
            unique_losses = sorted(set(all_packet_loss_values))
            axs[2].hist(all_packet_loss_values, bins=unique_losses, color='red', alpha=0.7, edgecolor='black')
            axs[2].set_xlabel('Packet Loss (%)')
            axs[2].set_ylabel('Frequency')
            axs[2].set_title('Histogram of Packet Loss')
            axs[2].text(0.95, 0.95,
                        "Distribution of packet loss percentages.",
                        transform=axs[2].transAxes, fontsize=9, va='top', ha='right',
                        bbox=dict(boxstyle="round", fc="w"))
        else:
            axs[2].text(0.5, 0.5, "No packet loss data to display.", ha='center', va='center')
        
        plt.tight_layout()
        plt.show()
    
    def generate_sample(self):
        """
        Extracts a 30-minute data sample from the log file.
        
        This method:
        1. Identifies the first 30 minutes of data
        2. Extracts all log entries within that period
        3. Formats them into a markdown document
        4. Saves the sample to a file
        
        Returns:
            str: The generated sample text in markdown format
        """
        sample_lines = []
        if self.timestamps:
            sample_start = min(self.timestamps)
            sample_end = sample_start + timedelta(minutes=30)
            with open(self.log_file_path, 'r') as logfile:
                for line in logfile:
                    line_strip = line.strip()
                    if not line_strip:
                        continue
                    m = self.LOG_PATTERN.match(line_strip)
                    if m:
                        ts = datetime.strptime(m.group("timestamp"), '%Y-%m-%d %H:%M:%S.%f')
                        if ts <= sample_end:
                            sample_lines.append(line_strip)
        
        sample_text = "### 30-Minute Data Sample (Exact Excerpt from Log File)\n\n"
        if sample_lines:
            sample_text += "```\n" + "\n".join(sample_lines) + "\n```\n"
        else:
            sample_text += "No data available.\n"
        
        output_folder = os.path.dirname(self.log_file_path)
        sample_filepath = os.path.join(output_folder, "sample_data.md")
        with open(sample_filepath, "w") as f:
            f.write(sample_text)
        print(f"Sample data file saved at: {sample_filepath}")
        return sample_text

    def generate_prompt(self):
        """
        Generates an LLM-ready analysis prompt based on the log data.
        
        This method:
        1. Calculates summary statistics from the log data
        2. Creates a structured prompt for LLM analysis
        3. Includes context, task description, and data summary
        4. Saves the prompt to a markdown file
        
        Returns:
            str: The generated prompt text in markdown format
        """
        total_entries = len(self.detailed_logs)
        num_segments = len(self.segments)
        avg_ping_value = sum(self.avg_pings) / len(self.avg_pings) if self.avg_pings else 0
        avg_jitter_value = sum(self.jitters) / len(self.jitters) if self.jitters else 0
        avg_packet_loss_value = sum(self.packet_losses) / len(self.packet_losses) if self.packet_losses else 0
        timeout_count_prompt = sum(1 for record in self.detailed_logs for ping in record['ping_results'] if ping is None)
        
        prompt_text = f"""# IDENTITY and PURPOSE
        You are a network performance analyst responsible for evaluating the quality and reliability of network connections using detailed log data. Your expertise allows you to interpret key metrics such as ping, jitter, and packet loss, and provide actionable insights.

        # Task
        You are provided with processed network log data that includes:
        - Key performance metrics: an average ping of {avg_ping_value:.1f} ms, an average jitter of {avg_jitter_value:.1f} ms, and an average packet loss of {avg_packet_loss_value:.1f}%.
        - A total of {timeout_count_prompt} timeouts were recorded.

        Your task is to review this data, compare it to an ideal baseline (low ping, low jitter, near-zero packet loss), and provide a comprehensive analysis of the network's performance.

        # Actions
        - **Analyze the Metrics:** Evaluate the provided average values.
        - **Identify Anomalies:** Look for signs of high variability, numerous timeouts, or increased packet loss.
        - **Review Sample Data:** Examine the attached sample_data.md file, which contains an exact 30-minute excerpt from the original log file (or the entire dataset if shorter).
        - **Summarize Findings:** Provide a concise, data-driven markdown analysis explaining what each metric means in simple terms and offering recommendations for improvement.
        - **Score:** Score the performance of the dataset from 1 to 5 and put it under "Performace Score:" section, include a brief description on why you gave that score.
        - **Output stucture:** as follows and always keep definitions at the bottom as written below. Please output your answer in complete Markdown format.
        '''
        # Assessment

        1. Ping: 
        2. Jitter: 
        3. Packet Loss: 

        **Performance score:**

        **What does it mean?**

        **What are your next steps?**

        -------------------------------------------------------
        **Definitions (what are these things?)**
        Ping: The delay between sending and receiving data.
        Jitter: How much that delay varies.
        Packet Loss: The amount of data that never arrives.

        '''

        # Restrictions
        - Base your analysis solely on the provided input data.
        - Do not include external assumptions or personal opinions.
        - Your response must be in markdown format.

        # INPUT:
        - **Ping:** Average = {avg_ping_value:.1f} ms.
        - **Jitter:** Average = {avg_jitter_value:.1f} ms.
        - **Packet Loss:** Average = {avg_packet_loss_value:.1f}%.
        - **Timeouts:** {timeout_count_prompt} recorded timeouts.
        """
        output_folder = os.path.dirname(self.log_file_path)
        md_filepath = os.path.join(output_folder, "LLM_prompt.md")
        with open(md_filepath, "w") as f:
            f.write(prompt_text)
        print(f"LLM prompt file saved at: {md_filepath}")
        return prompt_text

    def run_all(self):
        """
        Executes the complete log analysis workflow interactively.
        
        This method orchestrates the entire analysis process:
        1. Gets user input for chart types
        2. Segments the data and handles time gaps
        3. Filters segments based on minimum duration
        4. Generates visualizations and statistical summaries
        5. Creates analysis prompts and data samples
        
        The workflow is interactive, allowing users to customize the analysis
        based on their needs while maintaining data integrity and visualization
        clarity.
        """
        print("Select chart type for each metric:")
        chart_type_ping = input("AVERAGE PING (1=Line, 2=Bar): ").strip()
        chart_type_jitter = input("JITTER (1=Line, 2=Bar): ").strip()
        chart_type_loss = input("PACKET LOSS (1=Line, 2=Bar): ").strip()
        
        
        # Data Segmentation (Chunking)
        
        self.chunk_data()
        if len(self.segments) > 1:
            print("\nWARNING: Large time gaps have been detected in your dataset.")
            print("The data has been split into multiple segments so that lines/bars won't cross those gaps.")
        
        
        # Minimum segment length filtering
        
        try:
            min_seg = float(input("\nEnter a minimum segment length (in minutes) to keep (0 = keep all): ").strip())
        except ValueError:
            print("Invalid input for minimum segment length. Exiting.")
            sys.exit(1)
        
        self.filter_segments(min_seg)
        
        
        # Time Series Visualization
        
        self.plot_time_series(chart_type_ping, chart_type_jitter, chart_type_loss)
        
        
        # Summary Histograms
        
        self.plot_histograms()
        
        
        # LLM Prompt Generation and Sample Data Extraction
        
        self.generate_sample()
        self.generate_prompt()


if __name__ == "__main__":
    log_reader = LogReader()
    log_reader.run_all()
