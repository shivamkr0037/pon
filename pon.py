
import logging
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup
import os
import random

# Telegram bot token
TELEGRAM_BOT_TOKEN = '6074446870:AAFxdydW2mS2fXv5cjroi0-aYekvU2LoNX8'

# Initialize bot
updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
query = ""
sort_by = ""
page_number = 1
videos_to_send = 0
videos_sent = 0

def extract_video_source(url):
    headers = {'User-Agent': 'Mozilla/5.0', 'Host': 'www.homemoviestube.com', 'Connection': 'keep-alive', 'Accept-Encoding': 'gzip'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        video_tags = soup.find_all('video')
        if video_tags:
            return random.choice(video_tags).find('source')['src']
    return None

def download_video(url):
    try:
        r = requests.get(url, stream=True)
        local_filename = url.split('/')[-1]
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        return local_filename
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

# Function to remove video file
def remove_video_file(video_file):
    if os.path.exists(video_file):
        os.remove(video_file)

def run(update, context):
    update.message.reply_text('Please enter a query:')
    return 'QUERY'

def query_callback(update, context):
    global query
    query = update.message.text
    update.message.reply_text(f'Query set to: {query}. Please select a page number:')
    keyboard = [[InlineKeyboardButton(str(i), callback_data=f'page_{i}') for i in range(1, 6)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please select a page number:', reply_markup=reply_markup)
    return 'PAGE_NUMBER'

def page_callback(update, context):
    global page_number
    page_number = int(update.callback_query.data.split('_')[1])
    keyboard = [[InlineKeyboardButton("Relevancy", callback_data='sort_relevancy'),
                 InlineKeyboardButton("Length", callback_data='sort_length'),
                 InlineKeyboardButton("Rating", callback_data='sort_rating'),
                 InlineKeyboardButton("Views", callback_data='sort_views')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(f'Page number set to: {page_number}. Please select a sorting option:', reply_markup=reply_markup)
    return 'SORTING_OPTION'

def sort_callback(update, context):
    global sort_by
    sort_by = update.callback_query.data.split('_')[1]
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorting by: " + sort_by.capitalize())
    send_videos(update, context)
    return 'END'

def video_count_callback(update, context):
    global videos_to_send
    videos_to_send = int(update.message.text)
    return 'SUCCESS'

def send_videos(update, context):
    url = f"https://www.homemoviestube.com/search/{query}/page{page_number}.html?sortby={sort_by}"
    headers = {'User-Agent': 'Mozilla/5.0', 'Host': 'www.homemoviestube.com', 'Connection': 'keep-alive', 'Accept-Encoding': 'gzip'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)
        valid_video_links = []  # List to store valid video links
        for link in links:
            if link['href'].startswith('https://www.homemoviestube.com/videos/'):
                valid_video_links.append(link['href'])

        # Shuffle the list of video links
        random.shuffle(valid_video_links)

        # Select three random video links
        selected_links = valid_video_links[:3]

        for video_link in selected_links:
            video_source = extract_video_source(video_link)
            if video_source:
                msg = "Sending videos from this source link..."
                context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
                
                video_file = download_video(video_source)
                if video_file:
                    with open(video_file, 'rb') as video:
                        context.bot.send_video(chat_id=update.effective_chat.id, video=video)
                    
                    # Remove the video file from the system after uploading
                    remove_video_file(video_file)
                    
        context.bot.send_message(chat_id=update.effective_chat.id, text="Three random videos sent.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Failed to retrieve the webpage. Please try again.")

def cancel(update, context):
    update.message.reply_text('Operation cancelled.')
    return 'END'

# Conversation states
RUNNING, QUERY, PAGE_NUMBER, SORTING_OPTION, END, SUCCESS = range(6)

# Handlers
run_handler = CommandHandler('run', run)
query_handler = MessageHandler(Filters.text & ~Filters.command, query_callback)
page_handler = CallbackQueryHandler(page_callback, pattern='^page_')
sort_handler = CallbackQueryHandler(sort_callback, pattern='^sort_')
video_count_handler = MessageHandler(Filters.text & ~Filters.command, video_count_callback)
cancel_handler = CommandHandler('cancel', cancel)

dispatcher.add_handler(run_handler)
dispatcher.add_handler(query_handler)
dispatcher.add_handler(page_handler)
dispatcher.add_handler(sort_handler)
dispatcher.add_handler(video_count_handler)
dispatcher.add_handler(cancel_handler)

# Start the bot
updater.start_polling()
updater.idle()
