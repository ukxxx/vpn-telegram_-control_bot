import csv
import json
import os
import socket
import time
import logging
import re
from datetime import datetime
from typing import Optional, Tuple
from functools import wraps

from dotenv import load_dotenv
import matplotlib
import matplotlib.pyplot as plt
import paramiko
import telebot

load_dotenv()

matplotlib.use('Agg')

# Configure logging
logging.basicConfig(
    filename='vpnbotlog.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Constants for file paths
SPD_FILE = os.path.join(os.getcwd(), 'spddata.csv')
GRAPH_FILE = os.path.join(os.getcwd(), 'graph.png')

# Custom exception for file-related errors
class FileError(Exception):
    def __init__(self, message):
        super().__init__(message)

# Load configuration
config = {}
try:
    with open('config.json', 'r') as file:
        config = json.load(file)
except FileNotFoundError:
    raise FileError("The config.json file is missing.")
except json.JSONDecodeError:
    raise FileError("The config.json file is corrupted or contains invalid JSON.")

# Securely retrieve sensitive data from environment variables
config['token'] = os.environ.get('TELEGRAM_TOKEN')
config['password'] = os.environ.get('SSH_PASSWORD')

if not config['token'] or not config['password']:
    raise FileError("Missing environment variables for TELEGRAM_TOKEN or SSH_PASSWORD.")

bot = telebot.TeleBot(config['token'])

# Help message
HELP = """
/start - run the bot
/help - show this help
/reboot - restart server
/speedtest - check internet speed
/spdhist - view speed history
/stats - display statistics
"""

# Rate limiting decorator
user_last_activity = {}

def rate_limit(func):
    @wraps(func)
    def wrapper(message):
        user_id = message.chat.id
        current_time = time.time()
        if user_id in user_last_activity and current_time - user_last_activity[user_id] < 1:  # 1 second limit
            return  # Ignore the message
        user_last_activity[user_id] = current_time
        return func(message)
    return wrapper

# Helper functions
def send_user_message(chat_id, text):
    bot.send_message(chat_id, text)

def parse_speedtest_json(output: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        data = json.loads(output)
        download_speed = data['download']['bandwidth'] * 8 / 1_000_000  # Convert to Mbps
        upload_speed = data['upload']['bandwidth'] * 8 / 1_000_000  # Convert to Mbps
        result_url = data.get('result', {}).get('url')
        return download_speed, upload_speed, result_url
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Failed to parse speedtest JSON output: {e}")
        return None, None, None

def write_speed_data(date_str: str, download_speed: Optional[float], upload_speed: Optional[float]):
    file_exists = os.path.isfile(SPD_FILE)
    with open(SPD_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['date', 'download_speed', 'upload_speed'])
        writer.writerow([date_str, download_speed, upload_speed])

def execute_ssh_command(
    ip: str,
    username: str,
    password: str,
    command: str,
    timeout: int = 120
) -> Optional[str]:
    try:
        with paramiko.SSHClient() as cl:
            cl.load_system_host_keys()
            cl.set_missing_host_key_policy(paramiko.RejectPolicy())
            cl.connect(
                hostname=ip,
                username=username,
                password=password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            stdin, stdout, stderr = cl.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            if error:
                logging.error(f"Error executing command: {error}")
            return output
    except (paramiko.AuthenticationException, paramiko.SSHException, socket.error, Exception) as e:
        logging.error(f"SSH command execution failed: {e}")
        return None

# Security check for unauthorized users
@bot.message_handler(func=lambda message: message.chat.id not in config['users'])
def security_check(message):
    logging.warning(f"Unauthorized access attempt by user {message.chat.username}")
    send_user_message(message.chat.id, 'Not allowed to talk to strangers.')

# /help and /start command handler
@bot.message_handler(commands=['help', 'start'])
@rate_limit
def helpme(message):
    logging.info(f"User {message.chat.username} requested help")
    send_user_message(message.chat.id, HELP)

# /reboot command handler
@bot.message_handler(commands=['reboot'])
@rate_limit
def reboot(message):
    try:
        logging.info(f"User {message.chat.username} initiated reboot")
        send_user_message(message.chat.id, 'Rebooting...')
        result = execute_ssh_command(config['ip'], config['login'], config['password'], 'sudo reboot')
        if result is not None:
            send_user_message(message.chat.id, "Reboot command sent successfully.")
        else:
            send_user_message(message.chat.id, "Failed to send reboot command.")
    except Exception as e:
        logging.error(f"Error in reboot handler: {e}")
        send_user_message(message.chat.id, "An error occurred while trying to reboot the server.")

# /speedtest command handler
@bot.message_handler(commands=['speedtest'])
@rate_limit
def speedtest(message):
    try:
        logging.info(f"User {message.chat.username} requested speedtest")
        send_user_message(message.chat.id, 'Measuring. It usually takes about 1 minute...')
        # Use JSON output for reliable parsing
        speedtest_command = 'speedtest --accept-license --accept-gdpr --format=json'
        result = execute_ssh_command(
            config['ip'],
            config['login'],
            config['password'],
            speedtest_command
        )
        if result:
            download_speed, upload_speed, result_url = parse_speedtest_json(result)
            if download_speed is not None:
                send_user_message(message.chat.id, f"Download: {download_speed:.2f} Mbps")
            else:
                send_user_message(message.chat.id, "Download speed not found.")

            if upload_speed is not None:
                send_user_message(message.chat.id, f"Upload: {upload_speed:.2f} Mbps")
            else:
                send_user_message(message.chat.id, "Upload speed not found.")
                
            if result_url is not None:
                send_user_message(message.chat.id, f"Result URL: {result_url}")
            else:
                send_user_message(message.chat.id, "Result URL not found.")

            if download_speed is not None or upload_speed is not None:
                date_str = datetime.now().strftime('%d %b %H:%M')
                write_speed_data(date_str, download_speed, upload_speed)
            else:
                send_user_message(message.chat.id, "Failed to parse speedtest results.")
        else:
            send_user_message(message.chat.id, "Failed to execute speedtest command.")
    except Exception as e:
        logging.error(f"Error in speedtest handler: {e}")
        send_user_message(message.chat.id, "An error occurred while performing the speed test.")

# /stats command handler
@bot.message_handler(commands=['stats'])
@rate_limit
def stats(message):
    try:
        logging.info(f"User {message.chat.username} requested stats")
        send_user_message(message.chat.id, 'Collecting statistics...')
        result = execute_ssh_command(config['ip'], config['login'], config['password'], 'ipsec statusall')
        if result:
            # Parse uptime information
            uptime_match = re.search(r'uptime: (.+)', result)
            if uptime_match:
                uptime_info = uptime_match.group(1)
                send_user_message(message.chat.id, f"Server uptime: {uptime_info}")
            else:
                send_user_message(message.chat.id, "Failed to parse uptime information.")

            # Check client connections
            for client in config['clients']:
                client_pattern = re.compile(rf'{client}.*?ESTABLISHED.*?(\d+\.\d+\.\d+\.\d+)', re.DOTALL)
                client_match = client_pattern.search(result)
                if client_match:
                    ip_address = client_match.group(1)
                    send_user_message(message.chat.id, f"Client {client} is connected with IP: {ip_address}")
                else:
                    send_user_message(message.chat.id, f"Client {client} is not connected.")
        else:
            send_user_message(message.chat.id, "Failed to execute command to get stats.")
    except Exception as e:
        logging.error(f"Error in stats handler: {e}")
        send_user_message(message.chat.id, "An error occurred while collecting statistics.")

# /spdhist command handler
@bot.message_handler(commands=['spdhist'])
@rate_limit
def spdhist(message):
    try:
        logging.info(f"User {message.chat.username} requested speed history")
        if not os.path.isfile(SPD_FILE):
            send_user_message(message.chat.id, "No speed data available to display.")
            return
        with open(SPD_FILE, 'r') as file:
            data = list(csv.DictReader(file))
            if not data:
                send_user_message(message.chat.id, "No speed data available to display.")
                return
            dates = [row['date'] for row in data]
            download_speeds = [float(row['download_speed']) if row['download_speed'] else None for row in data]
            upload_speeds = [float(row['upload_speed']) if row['upload_speed'] else None for row in data]

        plt.figure(facecolor='gray')
        if any(download_speeds):
            plt.plot(dates, download_speeds, color='#4CAF50', marker='v', label='Download')
        if any(upload_speeds):
            plt.plot(dates, upload_speeds, color='#FED700', marker='^', label='Upload')
        plt.title('Speed plot', loc='left')
        plt.ylabel('Speed, Mbps')
        plt.xticks(rotation=30, ha='right')
        plt.legend()
        plt.tight_layout()
        plt.savefig(GRAPH_FILE)
        with open(GRAPH_FILE, 'rb') as photo:
            bot.send_photo(message.chat.id, photo)
    except Exception as e:
        logging.error(f"Error in spdhist handler: {e}")
        send_user_message(message.chat.id, "An error occurred while generating the speed history graph.")

# Main function to run the bot
def main():
    bot.infinity_polling()

if __name__ == '__main__':
    main()