# Network Monitoring Tools

This repository provides two Python-based tools designed to help you monitor and analyze network performance. They are ideal for network administrators, researchers, or anyone interested in tracking network reliability.

## Overview

- **LogReader**  
  A log parsing and plotting utility that:
  - Reads network log files containing metrics such as packet loss, ping times, and jitter.
  - Datawrangling options
  - Offers interactive chart options (line or bar) to visualize each metric.
  - Generates summary histograms and a 30-minute sample with an LLM prompt for detailed analysis.

- **Network Uptime Monitor**  
  A robust network monitoring tool that:
  - Continuously performs ping tests to a configurable target.
  - Logs detailed performance metrics (including latency, jitter, and packet loss) along with error information.
  - Automatically rotates log files to manage disk space.
  - Supports cross-platform usage and configurable settings via an auto-generated `ping_config.ini`.

## Features

### LogReader
- **Log Parsing & Segmentation:** Automatically detects time gaps in log data to prevent misleading visualizations.
- **Interactive Visualization:** Choose between line and bar charts for average ping, jitter, and packet loss.
- **Data Summaries:** Generates histograms and an LLM prompt along with a 30-minute data sample for further analysis.

### Network Uptime Monitor
- **Continuous Testing:** Conducts regular ping tests based on user-specified durations.
- **Detailed Logging:** Captures connectivity status, response times, packet loss, and jitter.
- **Configurable & Robust:** Uses a configuration file to customize target IPs, test parameters, and log file names. Implements log rotation and comprehensive error handling.

## Requirements

- Python 3.x
- Libraries: `matplotlib`, `tkinter`, and `configparser`
- A working `ping` command (platform-dependent)

***Tested working on windows 11 but untested on linux and apple. 

## Installation

1. **Clone the repository:**

    git clone https://github.com/yourusername/NetworkMonitoringTools.git
    cd NetworkMonitoringTools

2. **(Optional) Create and activate a virtual environment:**

    python3 -m venv env
    source env/bin/activate  # On Windows: env\Scripts\activate

3. **Install required packages:**

    pip install matplotlib

## Usage

### LogReader
1. Run the script:

       python LogReader.py

2. Use the GUI file dialog to select your log file.
3. Follow the prompts to choose chart types and set filtering options.
4. Visualizations will be displayed, and summary files (data sample and LLM prompt) are saved in the log file’s directory.

### Network Uptime Monitor
1. On the first run, a `ping_config.ini` file is generated with default settings. Modify this file if needed.
2. Run the script:

       python NetworkuptimeMonitor.py

3. Follow the interactive prompts to select the test duration and monitor real-time output.
4. Detailed logs will be saved in the specified log files.

## Configuration

- **LogReader:** No extra configuration is required beyond runtime prompts.
- **Network Uptime Monitor:** Customize settings in `ping_config.ini`:
  - **target:** IP address to ping (default: `8.8.8.8`)
  - **count:** Number of ping packets per test
  - **timeout:** Ping timeout in milliseconds
  - **desired_interval:** Time between tests
  - Log file names for all attempts and connection failures.

## License

This project is licensed under the GNU General Public License v3.0. For more details, see the [LICENSE](https://www.gnu.org/licenses/) file.

## Contributing

Contributions, issues, and feature requests are welcome! Please feel free to open issues or submit pull requests.
-TheDataQuokka

## Acknowledgements

- Built with Python using libraries such as `matplotlib` and `tkinter`.
- Inspired by real-world network monitoring needs.
