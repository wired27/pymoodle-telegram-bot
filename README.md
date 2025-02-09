# PyMoodle Telegram Bot

This project is a Telegram bot that interacts with the Moodle API to provide various functionalities such as fetching assignments, grades, and sending deadline reminders. Written on pure Python ;)

## Prerequisites

- Python 3.8+
- PostgreSQL (or any other supported database)
- Redis
- Telegram Bot Token
  
## Installation

1. **Clone the repository:**

    ```sh
    git clone https://github.com/wired27/pymoodle-telegram-bot.git
    cd pymoodle-telegram-bot
    ```

2. **Install Poetry:**

    ```sh
    pip install pipx
    pipx install poetry
    ```

3. **Install the required dependencies:**

    ```sh
    poetry install
    ```

4. **Set up environment variables:**

    Create a `.env` file in the root directory of the project and add the following variables:

    ```env
    TELEGRAM_TOKEN=your_telegram_bot_token
    MOODLE_URL=your_moodle_url
    DATABASE_URL=your_database_url
    ```
## Running the Bot

1. **Start the bot:**

    ```sh
    poetry run python main.py
    ```
