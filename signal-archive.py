#!/usr/bin/python3
# -*- coding: utf-8 -*-

import datetime, html, json, os, shutil, re, time
from functools import partial

import pytz

from data import *
import db
from db import types as content_types
from util import get_config

def produce_output_file(config, recipient, messages, timezone, address_book, default_recipient):
    """Produce a single HTML output file based on the given data."""

    # Notice: all output file formatting is here.

    # The below code is perhaps not very nice but it is simple.

    edit_avatar_file_name = lambda x: ".".join(x.split(".")[:-1]) + ".jpg"

    os.makedirs(config["output_path"], exist_ok=True)
    out = open(os.path.join(config["output_path"], "out.html"), mode="w")
    os.makedirs(os.path.join(config["output_path"], "attachment"), exist_ok=True)
    os.makedirs(os.path.join(config["output_path"], "other"), exist_ok=True)

    header = """
    <!DOCTYPE html>
    <html>
    <head>
    <title>{0}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta charset="utf-8" />
    <link rel="stylesheet" href="other/style.css" />
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
    """.format(recipient.name, '<img src="other/{}" />'.format(edit_avatar_file_name(recipient.avatar_file_name)) if recipient.avatar_file_name is not None else "")

    copy_avatars = set()
    if recipient.avatar_file_name is not None:
        copy_avatars.add(recipient.avatar_file_name)

    def replace_url_to_link(s):
        regex = r"(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        urls = re.compile(regex, re.MULTILINE|re.UNICODE)
        s = urls.sub(r'<a href="\1" target="_blank">\1</a>', s)
        return s

    out.write(header + "\n")

    # TODO: Add a mechanism to produce arbitrarily many colors.
    color_list = ["#36389d", "#6c3483", "#922b21", "#28b463", "#d4ac0d", "#5f6a6a", "#92a8d1"]
    color_idx = 0

    min_date = None

    for message in messages:
        if min_date is None: min_date = datetime.datetime.fromtimestamp(message.date, tz=timezone).strftime("%Y-%m-%d")
        date = datetime.datetime.fromtimestamp(message.date, tz=timezone).strftime("%Y-%m-%d %H.%M.%S")
        out.write('<div class="message-box" data="{}">\n'.format(message.date*1000))

        # Avatar.
        if message.sender.avatar_file_name is not None:
            copy_avatars.add(message.sender.avatar_file_name)
            out.write('<div class="avatar"><img src="{}" /></div>\n'.format(os.path.join("other", edit_avatar_file_name(message.sender.avatar_file_name))))
        else:
            if message.sender.color is None:
                message.sender.color = color_list[color_idx]
                color_idx += 1
            color = message.sender.color
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
                source_file_name = os.path.join(config["data_path"], attachment.file_name)
                if attachment.timestamp == 0:
                    # Use the current timestamp to minimize collisions.
                    timestamp = int(time.time())
                else:
                    timestamp = attachment.timestamp
                base = str(timestamp) + "_" + attachment.file_name.split(".")[0].split("_")[1]
                target_file_name = os.path.join(config["output_path"], "attachment", base + "." + content_types[attachment.content_type][1])

                if os.path.exists(source_file_name):
                    try:
                        shutil.copy(source_file_name, target_file_name)
                    except FileExistsError:
                        pass
                else:
                    print("Copying attachment '{}' failed. File does not exist.".format(source_file_name))

                file_name = os.path.join("attachment", os.path.basename(target_file_name))
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

    <script src="other/script.js"></script>

    </body>
    </html>
    """.format(min_date, max_date)

    out.write(footer)

    out.close()

    other_path = os.path.join(config["output_path"], "other")
    shutil.copy("html/style.css", other_path)
    shutil.copy("html/script.js", other_path)
    for file_name in copy_avatars:
        try:
            shutil.copy(os.path.join(config["data_path"], file_name), os.path.join(other_path, edit_avatar_file_name(file_name)))
        except FileNotFoundError:
            print("Could not find avatar file '{}'.".format(file_name))

if __name__ == "__main__":
    config = get_config()

    # Database connection and utility functions.
    cursor = db.setup_db(os.path.join(config["data_path"], config["db_file_name"]))
    get_messages = partial(db.get_messages, cursor)
    find_group = partial(db.find_group, cursor)
    find_contact = partial(db.find_contact, cursor)

    # Timezone.
    if not "timezone" in config:
        config["timezone"] = "UTC"
    timezone = pytz.timezone(config["timezone"])

    # Contacts.
    address_book = AddressBook.from_db_cursor(cursor)
    default_recipient = address_book.get_contact(name=config["default_recipient"])
    if len(default_recipient) == 0:
        raise SystemExit("Default recipient with name '{}' not found.".format(config["default_recipient"]))
    default_recipient = default_recipient[0]
    # Find avatars for contacts.
    avatar_files = [x for x in os.listdir(config["data_path"]) if x.startswith("Avatar") and x.endswith(".bin")]
    get_id = lambda x: int(x.split("_")[-1].split(".")[0])
    avatar_map = {get_id(x):x for x in avatar_files}
    for contact in address_book.contacts.values():
        if contact.id in avatar_map:
            contact.avatar_file_name = avatar_map[contact.id]

    # Figure out the recipient (contact or group) whose messages we are after.
    if "contact" in config:
        try:
            _recipient = find_contact(config["contact"])[0]
            recipient = address_book.get_contact(ids=_recipient.id)[0]
        except IndexError:
            raise SystemExit("No contact '{}'.".format(config["contact"]))
    elif "group" in config:
        try:
            recipient = find_group(config["group"])[0]
        except IndexError:
            raise SystemExit("No group '{}'.".format(config["group"]))
    else:
        raise SystemExit("No contact or group defined for which to load messages.")

    # Find avatar for group (if applicable).
    if isinstance(recipient, Group) and recipient.id in avatar_map:
        recipient.avatar_file_name = avatar_map[recipient.id]

    # Get messages and produce an output file.
    messages = get_messages(recipient, address_book, default_recipient=default_recipient)
    if len(messages) == 0:
        raise SystemExit("No messages found.")

    # Edit the recipient based on the config.
    if not "contacts" in config:
        config["contacts"] = {}
    if "avatar_file_name" in config:
        recipient.avatar_file_name = config["avatar_file_name"]
    # Edit contacts based on the config.
    for _recipient, recipient_data in config["contacts"].items():
        contacts = address_book.get_contact(name=_recipient)
        if len(contacts) > 0:
            contact = contacts[0]
            if "display_name" in recipient_data:
                contact.name = recipient_data["display_name"]
            if "avatar_file_name" in recipient_data:
                contact.avatar_file_name = recipient_data["avatar_file_name"]
            if "color" in recipient_data:
                contact.color = recipient_data["color"]
    # Edit the messages for mentions (this must be here as the names could have
    # changed above).
    for message in messages:
        if len(message.mentions) > 0:
            mention_map = {mention[1][0]:[mention[0], mention[1][1]] for mention in message.mentions}
            modified_message = ""
            # This is for skipping extra spaces that are sometimes introduced.
            skip = []
            for n, c in enumerate(message.message):
              if n in skip and c == " ": continue
              if n in mention_map:
                  if mention_map[n][1] == 1:
                      modified_message += "@{}".format(mention_map[n][0].name)
                      if len(message.message) > n + 2 and message.message[n + 1] == " " and message.message[n + 2] in [" ", ".", ",", "!", "?"]:
                          skip.append(n + 1)
                  else:
                      modified_message += c
                      skip.append(n + mention_map[n][1])
              else:
                  modified_message += c
            message.message = modified_message

    produce_output_file(config, recipient, messages, timezone, address_book, default_recipient)

