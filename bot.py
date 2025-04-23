import requests

def send_message_to_telegram(chat_id, text):
    """Sends a message to a specified chat via Telegram bot."""
    token = '6776835044:AAEFmORS02CYQ6wAA6h_lHOMdrHcNzNDf9Y'  # Replace YOUR_BOT_TOKEN with your actual bot token
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    response = requests.post(url, data=payload)
    return response.json()  # Returns the result of the API call
