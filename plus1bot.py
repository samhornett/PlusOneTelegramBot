from telegram.ext import MessageHandler, Filters, StringRegexHandler
from telegram.ext import CommandHandler
from telegram.ext import Updater
import logging
import re
import secrets
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


def echo(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=update.message.text)


def count_plus1(update, context):
    context.user_data .setdefault("-1_given", 0)
    context.user_data.setdefault("+1_given", 0)
    context.user_data .setdefault("neg_total_given", 0)
    context.user_data.setdefault("pos_total_given", 0)

    context.chat_data.setdefault("Songs_recommended", {})

    number_finder = re.compile('[+-]\d*')
    m = number_finder.match(update.message.text)
    if m:
        number = int(m.group())
        if number > 0:
            context.user_data["+1_given"] += 1
            context.user_data["pos_total_given"] += number
        if number < 0:
            context.user_data["-1_given"] += 1
            context.user_data["neg_total_given"] += number

        if update.message.reply_to_message:
            if len(update.message.reply_to_message.entities) > 0:
                if update.message.reply_to_message.entities[0]["type"] == "url":
                    text = "{0!s} has given {1:+d} to {2!s}".format(
                        update.effective_user.first_name, number, update.message.reply_to_message.text)
            else:
                text = "{0!s} has given {1:+d} to {2!s}".format(
                    update.effective_user.first_name, number, update.message.reply_to_message.from_user.first_name)
        else:
            text = "{0!s} has given {1:+d} ".format(
                update.effective_user.first_name, number)
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)



if __name__ == "__main__":
    import json

    with open("secrets.json",'r') as f:
        token = json.load(f)["telegram_token"]

    number_finder = re.compile('[+-]\d*')
    updater = Updater(
        token=token, use_context=True)
    dispatcher = updater.dispatcher
    count_handler = MessageHandler(Filters.text, count_plus1)
    start_handler = CommandHandler('start', start)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(count_handler)

    updater.start_polling()
