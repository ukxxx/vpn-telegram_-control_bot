import csv
import json
import os
import socket
import time
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
import paramiko
import telebot

matplotlib.use('Agg')

# os.chdir('PATH_TO_FOLDER') # Uncomment and replace PATH_TO_FOLDER with your actual pat in case of environment do not gives you full path to the working directory
log_file = os.path.join(os.getcwd(), 'vpnbotlog.txt')
spd_file = os.path.join(os.getcwd(), 'spddata.csv')
graph_file = os.path.join(os.getcwd(), 'graph.png')

class FileError(Exception):
    def __init__(self, message):
        super().__init__(message)

try:
    with open('config.json', 'r') as file:
        config = json.load(file)
    bot = telebot.TeleBot(config['token'])
except:
     raise FileError("There is no config.json file or file is corrupted.")

HELP = """
/start - run the bot
/help - show this help
/reboot - restart server 
/speedtest - check internet speed
/spdhist - view speed history
/stats - display statistics"""

# Function to write logs to a log file
def write_log(message, action):
    with open(log_file, 'a', encoding='utf-8') as log:
        time_str = datetime.now().strftime('%X %d %b %Y')
        if message == None:
            log.write(f"{time_str} {action}.\n")
        else:
            log.write(f"{time_str} user {message.chat.username} {action}.\n")

# Function to send command to the server via SSH
def send_show_command(ip, username, password, command, max_bytes=60000, short_pause=1):
    cl = paramiko.SSHClient()
    cl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cl.connect(hostname=ip, username=username, password=password, look_for_keys=False, allow_agent=False)

    with cl.invoke_shell() as ssh:
        time.sleep(short_pause)
        ssh.recv(max_bytes)
        ssh.send(command)
        ssh.settimeout(5)
        ssh.send("\n")

        output = ""
        while True:
            try:
                part = ssh.recv(max_bytes).decode("utf-8")
                output += part
                time.sleep(0.5)
            except socket.timeout:
                break
    return output

# Message handler for unauthorized users
@bot.message_handler(func=lambda message: message.chat.id not in config['users'])
def security_check(message):
    write_log(message, "tried to run the bot")
    bot.send_message(message.chat.id, 'Not allowed to talk to strangers.')

# Message handler for /help and /start commands
@bot.message_handler(commands=['help', 'start'])
def helpme(message):
    write_log(message, "opened help")
    bot.send_message(message.chat.id, HELP)

# Message handler for /reboot command
@bot.message_handler(commands=['reboot'])
def reboot(message):
    write_log(message, "rebooted server")
    message_chat = 'Rebooting...'
    bot.send_message(message.chat.id, message_chat)
    send_show_command(config['ip'], config['login'], config['password'], 'sudo reboot')

# Message handler for /speedtest command
@bot.message_handler(commands=['speedtest'])
def speedtest(message):
    write_log(message, "measured speed")
    bot.send_message(message.chat.id, 'Measuring. It usually takes about 1 minute...')
    command_result_unsplitted = send_show_command(config['ip'], config['login'], config['password'], 'speedtest')
    command_result = command_result_unsplitted.split()

    bot.send_message(message.chat.id, 'Upload:')
    last_occurrence = -1
    element_found = True
    while element_found:
        try:
            last_occurrence = command_result.index('Upload:', last_occurrence + 1)
        except ValueError:
            element_found = False
    last_occurrence += 1
    message_chat = command_result[last_occurrence] + ' Mb\s'
    bot.send_message(message.chat.id, message_chat)

    up_speed = int(float(command_result[last_occurrence]))

    bot.send_message(message.chat.id, 'Download:')
    last_occurrence = -1
    element_found = True
    while element_found:
        try:
            last_occurrence = command_result.index('Download:', last_occurrence + 1)
        except ValueError:
            element_found = False
    last_occurrence += 1
    message_chat = command_result[last_occurrence] + ' Mb\s'
    bot.send_message(message.chat.id, message_chat)

    down_speed = int(float(command_result[last_occurrence]))

    with open(spd_file, 'a', newline="") as file:
        time_str = datetime.now().strftime('%d %b %H:%M')# + 'h'
        data_to_write = (time_str, down_speed, up_speed)
        writer = csv.writer(file)
        writer.writerow(data_to_write)

# Message handler for /test command
@bot.message_handler(commands=['test'])
def test(message):
    message_sent = datetime.now().strftime('%X %d %b %Y')
    bot.send_message(message.chat.id, message_sent)

# Message handler for /stats command
@bot.message_handler(commands=['stats'])
def stat(message):
    write_log(message, "collected stats")
    message_chat = 'Collecting statistics...'
    bot.send_message(message.chat.id, message_chat)
    command_result_unsplitted = send_show_command(config['ip'], config['login'], config['password'], 'ipsec statusall')
    command_result_unsplitted = command_result_unsplitted.lower()
    command_result = command_result_unsplitted.split()

    last_occurrence = -1
    element_found = True
    while element_found:
        try:
            last_occurrence = command_result.index(
                'uptime:', last_occurrence + 1)
        except ValueError:
            element_found = False
    last_occurrence += 1
    message_chat = f"Server uptime: {command_result[last_occurrence]} {command_result[last_occurrence + 1]} since {command_result[last_occurrence + 4]} {command_result[last_occurrence + 3]} {command_result[last_occurrence + 6]} {command_result[last_occurrence + 5]}."
    bot.send_message(message.chat.id, message_chat)

    for client in config['clients']:
        try:
            ip_address_unsplitted = command_result[command_result.index(
                client) - 5]
            ip_address_split_first = ip_address_unsplitted.split("...")
            ip_address_split = ip_address_split_first[1].split("[")
            message_chat = f"Client {client} connected {command_result[command_result.index(client) - 8]} {command_result[command_result.index(client) - 7]} ago.\nIP-address: {ip_address_split[0]}"
            bot.send_message(message.chat.id, message_chat)
        except ValueError:
            message_chat = 0

# Message handler for /spdhist command
@bot.message_handler(commands=['spdhist'])
def spdhist(message):
    result_down = {}
    result_up = {}
    with open(spd_file, 'r') as file:
        spddata = csv.DictReader(file)
        for row in spddata:
            result_down[row['date']] = row['download_speed']
            result_up[row['date']] = row['upload_speed']

    xpoints = list(result_down.keys())
    ypoints_down = list(map(int, list(result_down.values())))
    ypoints_up = list(map(int, list(result_up.values())))
    plt.title(label='Speed plot', loc='left')
    plt.figure(facecolor='gray')
    plt.plot(xpoints, ypoints_down, color='#4CAF50', marker='v', label='Download')
    plt.plot(xpoints, ypoints_up, color='#FED700', marker='^', label='Upload')
    plt.ylabel('Speed, Mb\s')
    plt.xticks(rotation=30, ha='right')
    plt.legend()
    plt.tight_layout()
    plt.savefig(graph_file)

    bot.send_photo(message.chat.id, photo=open(graph_file, 'rb'))

# Main function to run the bot
def main():
   
    while True:
        try:
            bot.polling(none_stop=True)
        except:
            write_log(None, "Telegram connection has lost")
            time.sleep(15)


if __name__ == '__main__':
    main()