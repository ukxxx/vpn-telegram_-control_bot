# VPN Bot README.md

## Overview

This Python script is a VPN management Telegram bot that uses the telebot library to interact with users. The bot connects to the server via SSH and provides the functionality to manage a Strongswan VPN server , perform speed tests using Ookla speedtest, and display server statistics. It can also show a graph of the speed test history.

## Installation

    Make sure you have Python 3.6 or higher installed on your machine.
    Install required dependencies using pip:

    pip install -r requirements.txt

## Configuration

    Create a config.json file in the same directory as the script. The contents of the file should be in the following format:

    json

        {
            "ip": "YOUR_VPN_SERVER_IP",
            "login": "YOUR_VPN_SERVER_LOGIN",
            "users": [123456789, 987654321],
            "clients": ["client1", "client2"]
        }

    Replace YOUR_VPN_SERVER_IP and YOUR_VPN_SERVER_LOGIN with the corresponding values. Add Telegram user IDs you want to grant access to the bot in the users array. List the VPN client names in the clients array.

    The bot requires certain sensitive data to be set as environment variables. Using the python-dotenv package, you can store these variables in a .env file in the same directory as your script.

    Create a file named .env in the same directory as your Python script.

    Add the following lines to the .env file:

        TELEGRAM_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
        SSH_PASSWORD=YOUR_SSH_PASSWORD

    Replace YOUR_TELEGRAM_BOT_TOKEN and YOUR_SSH_PASSWORD with your actual Telegram bot token and SSH password.

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

The script contains several functions to handle different bot commands, as well as utility functions for managing the VPN server and performing speed tests.

## Acknowledgments

Thanks a lot to the developers of pytelegrambotapi, paramiko, matplotlib, and python-dotenv for their excellent libraries.

## Contact

If you have any questions or need assistance, feel free to open an issue or contact the repository owner..
