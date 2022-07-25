#!/usr/bin/python3
# -*- coding: utf-8 -*-

import datetime, html, json, os, shutil, re

import pytz

from data import *
from db import find_contact, find_group, get_messages, setup_db
from util import get_config

def produce_output_file(config, messages, timezone, address_book, default_recipient):
    """Produce a single HTML output file based on the given data."""

    # Notice: all output file formatting is here.

    # The below code is perhaps not very nice but it is simple.

    out = open(os.path.join(config["output_path"], "out.html"), mode="w")
    os.makedirs(os.path.join(config["output_path"], "attachment"), exist_ok=True)

    header = """
    <!DOCTYPE html>
    <html>
    <head>
    <title>{0}</title>
    <meta charset="utf-8" />
    <link rel="stylesheet" href="style.css" />
    </head>
    <body>

    <div id="reaction-overlay" onclick="disable_reaction_overlay(event)">
      <div id="reaction-box"></div>
    </div>

    <div id="group-avatar">
      <h1>{0}</h1>
      {1}
    </div>

    <div id="messages">
    """.format(recipient.name, '<img src="{}" />'.format(config["avatar"]) if "avatar" in config else "")

    def replace_url_to_link(s):
        regex = r"(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        urls = re.compile(regex, re.MULTILINE|re.UNICODE)
        s = urls.sub(r'<a href="\1" target="_blank">\1</a>', s)
        return s

    out.write(header + "\n")

    # TODO: Add a mechanism to produce arbitrarily many colors.
    color_list = ["#36389d", "#6c3483", "#922b21", "#28b463", "#d4ac0d", "#5f6a6a"]
    color_idx = 0
    colors = {}

    min_date = None

    for message in messages:
        if min_date is None: min_date = datetime.datetime.fromtimestamp(message.date, tz=timezone).strftime("%Y-%m-%d")
        date = datetime.datetime.fromtimestamp(message.date, tz=timezone).strftime("%Y-%m-%d %H.%M.%S")
        out.write('<div class="message-box" data="{}">\n'.format(message.date*1000))

        # Avatar.
        if message.sender.avatar_file_name is not None:
            out.write('<div class="avatar"><img src="{}" /></div>\n'.format(os.path.join(config["avatar_path"], message.sender.avatar_file_name)))
        else:
            if not message.sender.name in colors:
                colors[message.sender.name] = color_list[color_idx]
                color_idx += 1
            color = colors[message.sender.name]
            text = "".join(x[0] for x in message.sender.name.split(" ")).upper()
            out.write('<div class="avatar"><span data="{}" color="{}"></span></div>\n'.format(text, color))

        # Sender.
        out.write('<div class="sender">{} ({})</div>\n'.format(message.sender.name, date))

        out.write('<div class="message">')

        # Quote.
        if message.quote is not None:
            quote_date = datetime.datetime.fromtimestamp(message.quote.date, tz=timezone).strftime("%Y-%m-%d %H.%M.%S")
            out.write('<div class="quote">{} ({}): {}</div>\n'.format(message.quote.sender.name, quote_date, message.quote.message))

        # Message.
        out.write('{}'.format(replace_url_to_link(html.escape(message.message)) if message.message is not None else ""))

        # Attachments.
        if hasattr(message, "attachments") and len(message.attachments) > 0:
            for attachment in message.attachments:
                # Try to figure out the correct extension for the file type.
                for extension in attachment.file_name_extensions:
                    file_name = attachment.file_name_base + "." + extension if len(extension) > 0 else attachment.file_name_base
                    source_file_name = os.path.join(config["attachment_path"], file_name)
                    attachment_file_name = os.path.join(config["output_path"], "attachment", file_name)
                    if os.path.exists(source_file_name):
                        try:
                            shutil.copy(source_file_name, attachment_file_name)
                        except FileExistError:
                            pass
                        break

                file_name = os.path.join("attachment", file_name)
                if isinstance(attachment, Image):
                    out.write('<img src="{}" style="max-width: 100%" />\n'.format(file_name))
                elif isinstance(attachment, Video):
                    out.write('<video controls style="width: 100%"><source src="{0}" type="{1}">Video of type {1} <span><a href="{0}" type="{1}">&#x2913;</a></span></video>\n'.format(file_name, attachment.content_type))
                elif isinstance(attachment, Audio):
                    out.write('<audio controls><source src="{0}" type="{1}">Video of type {1} <span><a href="{0}" type="{1}">&#x2913;</a></span></audio>\n'.format(file_name, attachment.content_type))

        out.write('</div>\n')
        
        # Reactions.
        if len(message.reactions) > 0:
            # Group the reactions.
            reactions = {}
            reaction_data = []
            for reaction in message.reactions:
                if not reaction.emoji in reactions:
                    reactions[reaction.emoji] = [reaction.contact.name]
                else:
                    reactions[reaction.emoji].append(reaction.contact.name)
                reaction_data.append((reaction.contact.name, reaction.emoji))
            reaction_data.sort(key=lambda x: x[0])

            # Display the reaction bar.
            out.write('<div class="reaction" data="{}">\n'.format(html.escape(json.dumps(reaction_data))))
            for emoji, authors in reactions.items():
                out.write('<span onclick="enable_reaction_overlay(event)">{} {}</span>\n'.format(emoji, "" if len(authors) == 1 else str(len(authors))))
            out.write("</div>")

        out.write("</div>\n\n")

    max_date = datetime.datetime.fromtimestamp(message.date, tz=timezone).strftime("%Y-%m-%d")

    footer = """
    </div>

    <div id="search-box">
      Search: <input type="search" id="search-input" />
      From: <input type="date" id="search-date-from" min="{0}" max="{1}" onchange="live_search()" />
      To: <input type="date" id="search-date-to" min="{0}" max="{1}" onchange="live_search()" />
    </div>

    <script src="script.js"></script>

    </body>
    </html>
    """.format(min_date, max_date)

    out.write(footer)

    out.close()

    shutil.copy("html/style.css", config["output_path"])
    shutil.copy("html/script.js", config["output_path"])

if __name__ == "__main__":
    config = get_config()

    # Database connection.
    cursor = setup_db(config["db_file_name"])

    # Timezone.
    if not "timezone" in config:
        config["timezone"] = "UTC"
    timezone = pytz.timezone(config["timezone"])

    # Contacts.
    address_book = AddressBook.from_db_cursor(cursor)
    default_recipient = address_book.get_contact(name=config["default_recipient"])[0]
    # Edit contacts based on the config.
    if not "contacts" in config:
        config["contacts"] = {}
    for recipient, recipient_data in config["contacts"].items():
        contacts = address_book.get_contact(name=recipient)
        if len(contacts) > 0:
            contact = contacts[0]
            if "display_name" in recipient_data:
                contact.name = recipient_data["display_name"]
            if "avatar_file_name" in recipient_data:
                contact.avatar_file_name = recipient_data["avatar_file_name"]

    # Figure out the recipient (contact or group) whose messages we are after.
    if "contact" in config:
        try:
            recipient = find_contact(cursor, config["contact"])[0]
        except IndexError:
            raise SystemExit("No contact '{}'.".format(config["contact"]))
    elif "group" in config:
        try:
            recipient = find_group(cursor, config["group"])[0]
        except IndexError:
            raise SystemExit("No group '{}'.".format(config["group"]))
    else:
        raise SystemExit("No contact or group defined for which to load messages.")

    # Get messages and produce an output file.
    messages = get_messages(cursor, recipient, address_book, default_recipient=default_recipient)
    if len(messages) == 0:
        raise SystemExit("No messages found.")

    produce_output_file(config, messages, timezone, address_book, default_recipient)

