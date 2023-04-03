# VPN Bot README.md

## Overview

This Python script is a VPN management Telegram bot that uses the telebot library to interact with users. The bot connects to the server via SSH and provides the functionality to manage a Strangswan VPN server , perform speed tests using Ookla speedtest, and display server statistics. It can also show a graph of the speed test history.

## Installation

    Make sure you have Python 3.6 or higher installed on your machine.
    Install required dependencies using pip:

    pip install telebot paramiko matplotlib

## Configuration

    Create a config.json file in the same directory as the script. The contents of the file should be in the following format:

    json

    {
        "token": "YOUR_BOT_TOKEN",
        "ip": "YOUR_VPN_SERVER_IP",
        "login": "YOUR_VPN_SERVER_LOGIN",
        "password": "YOUR_VPN_SERVER_PASSWORD",
        "users": [ALLOWED_USER_IDS],
        "clients": ["CLIENT1", "CLIENT2", ...]
    }

    Replace YOUR_BOT_TOKEN, YOUR_VPN_SERVER_IP, YOUR_VPN_SERVER_LOGIN, and YOUR_VPN_SERVER_PASSWORD with the corresponding values. Add Telegram user IDs you want to grant access to the bot in the users array. List the VPN client names in the clients array.

    Make sure the following files are in the same directory as the script:
        vpnbotlog.txt: This file stores logs of user actions and bot events.
        spddata.csv: This file stores the speed test data in CSV format.
        graph.png: This file will be used to store the speed history graph.

## Usage

To run the bot, execute the script using Python:

python main.py

The bot understands the following commands:

    /start: Run the bot.
    /help: Show help information.
    /reboot: Restart the server.
    /speedtest: Check internet speed.
    /spdhist: View speed history.
    /stats: Display statistics.

## Functions

The script contains several functions to handle different bot commands, as well as utility functions for managing the VPN server and performing speed tests. The main function main() starts the bot and handles connection issues with Telegram.
