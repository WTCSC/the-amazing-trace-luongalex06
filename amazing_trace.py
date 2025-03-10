import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib.ticker import MaxNLocator
import time
import os
import subprocess
import re
import logging

logging.basicConfig(filename='amazing_trace.log', encoding="utf-8", level=logging.DEBUG)

def execute_traceroute(destination):
    """
    Executes a traceroute to the specified destination and returns the output.

    Args:
        destination (str): The hostname or IP address to trace

    Returns:
        str: The raw output from the traceroute command
    """

    try:
        run = subprocess.run(['traceroute', destination], capture_output=True, text=True)
        if run.returncode != 0:
            logging.error(f"Traceroute failed with return code {run.returncode}")
            return ""
        return run.stdout
    except Exception as e:
        logging.error(f"Error executing traceroute: {e}")
        return ""

def parse_traceroute(traceroute_output):
    parsed_result = []
    lines = traceroute_output.strip().split("\n")[1:] 

    for line in lines:
   
        hop_match = re.match(r'\s*(\d+)\s+(.*)', line)
        if hop_match:
            hop = int(hop_match.group(1))
            remainder = hop_match.group(2)

      
            hostname = None
            ip = None
            rtt_values = []

       
            if remainder.strip() == '* * *':
                rtt_values = [None, None, None]
            else:
                
                mixed_pattern = r'\*?\s*([^\s(]+)\s*\(([^\)]+)\)'
                mixed_match = re.search(mixed_pattern, remainder)
                if mixed_match:
                    hostname = mixed_match.group(1)
                    ip = mixed_match.group(2)
                else:
    
                    ip_pattern = r'(?:.*?[^\s(]+\s*)?\(([^\)]+)\)'
                    ip_match = re.search(ip_pattern, remainder)
                    if ip_match:
                        ip = ip_match.group(1)
                    
                        hostname_match = re.match(r'\s*([^\s(]+)\s*\(', remainder)
                        hostname = hostname_match.group(1) if hostname_match else None
                    else:

                        no_stars = re.sub(r'\s*\*\s*', '', remainder)
                        first_word = re.match(r'\s*([^\s]+)', no_stars)
                        if first_word:
                            ip = first_word.group(1)

                rtt_matches = re.finditer(r'(?:([0-9.]+)\s*ms|[*](?:\s*ms)?)', remainder)
                rtt_values = []
                for rtt_match in rtt_matches:
                    if rtt_match.group(1):
                        rtt_values.append(float(rtt_match.group(1)))
                    else:
                        rtt_values.append(None)

  
                if '<1' in remainder:
                    rtt_values = [0.5 if v is None else v for v in rtt_values]

        
            while len(rtt_values) < 3:
                rtt_values.append(None)
            rtt_values = rtt_values[:3]

            
            if hostname == '*' or hostname == ip:
                hostname = None

            parsed_result.append({
                'hop': hop,
                'ip': ip,
                'hostname': hostname,
                'rtt': rtt_values
            })

    return parsed_result

# ============================================================================ #
#                    DO NOT MODIFY THE CODE BELOW THIS LINE                    #
# ============================================================================ #
def visualize_traceroute(destination, num_traces=3, interval=5, output_dir='output'):
    """
    Runs multiple traceroutes to a destination and visualizes the results.

    Args:
        destination (str): The hostname or IP address to trace
        num_traces (int): Number of traces to run
        interval (int): Interval between traces in seconds
        output_dir (str): Directory to save the output plot

    Returns:
        tuple: (DataFrame with trace data, path to the saved plot)
    """
    all_hops = []

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print(f"Running {num_traces} traceroutes to {destination}...")

    for i in range(num_traces):
        if i > 0:
            print(f"Waiting {interval} seconds before next trace...")
            time.sleep(interval)

        print(f"Trace {i+1}/{num_traces}...")
        output = execute_traceroute(destination)
        hops = parse_traceroute(output)

        # Add timestamp and trace number
        timestamp = time.strftime("%H:%M:%S")
        for hop in hops:
            hop['trace_num'] = i + 1
            hop['timestamp'] = timestamp
            all_hops.append(hop)

    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(all_hops)

    # Calculate average RTT for each hop (excluding timeouts)
    df['avg_rtt'] = df['rtt'].apply(lambda x: np.mean([r for r in x if r is not None]) if any(r is not None for r in x) else None)

    # Plot the results
    plt.figure(figsize=(12, 6))

    # Create a subplot for RTT by hop
    ax1 = plt.subplot(1, 1, 1)

    # Group by trace number and hop number
    for trace_num in range(1, num_traces + 1):
        trace_data = df[df['trace_num'] == trace_num]

        # Plot each trace with a different color
        ax1.plot(trace_data['hop'], trace_data['avg_rtt'], 'o-',
                label=f'Trace {trace_num} ({trace_data.iloc[0]["timestamp"]})')

    # Add labels and legend
    ax1.set_xlabel('Hop Number')
    ax1.set_ylabel('Average Round Trip Time (ms)')
    ax1.set_title(f'Traceroute Analysis for {destination}')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend()

    # Make sure hop numbers are integers
    ax1.xaxis.set_major_locator(MaxNLocator(integer=True))

    plt.tight_layout()

    # Save the plot to a file instead of displaying it
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    safe_dest = destination.replace('.', '-')
    output_file = os.path.join(output_dir, f"trace_{safe_dest}_{timestamp}.png")
    plt.savefig(output_file)
    plt.close()

    print(f"Plot saved to: {output_file}")

    # Return the dataframe and the path to the saved plot
    return df, output_file

# Test the functions
if __name__ == "__main__":
    # Test destinations
    destinations = [
        "google.com",
        "amazon.com",
        "bbc.co.uk"  # International site
    ]

    for dest in destinations:
        df, plot_path = visualize_traceroute(dest, num_traces=3, interval=5)
        print(f"\nAverage RTT by hop for {dest}:")
        avg_by_hop = df.groupby('hop')['avg_rtt'].mean()
        print(avg_by_hop)
        print("\n" + "-"*50 + "\n")
