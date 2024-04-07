import sqlite3

from data import *

types = {"application/pdf": (Attachment, "pdf"),
         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (Attachment, "xls"),
         "application/zip": (Attachment, "zip"),
         "application/x-signal-view-once": (Attachment, ""),
         "audio/aac": (Audio, "aac"),
         "audio/AMR": (Audio, "amr"),
         "audio/mp3": (Audio, "mp3"),
         "audio/mp4": (Audio, "mp4"),
         "audio/mpeg": (Audio, "mpeg"),
         "audio/ogg": (Audio, "ogg"),
         "audio/ogg; codecs=opus": (Audio, "ogg"),
         "audio/wav": (Audio, "wav"),
         "audio/x-m4a": (Audio, "mp4"),
         "image/*": (Image, "jpg"),
         "image/bmp": (Image, "bmp"),
         "image/gif": (Image, "gif"),
         "image/heif": (Image, "heif"),
         "image/jpeg": (Image, "jpg"),
         "image/png": (Image, "png"),
         "image/webp": (Image, "webp"),
         "image/x-icon": (Attachment, ""),
         "text/plain": (Attachment, ""),
         "text/x-signal-plain": (Attachment, ""),
         "video/*": (Video, "mp4"),
         "video/mp4": (Video, "mp4"),
         "video/x-matroska": (Video, "mkv"),
         "video/mpeg": (Video, "mp4"),
         "video/quicktime": (Video, "qt"),
         "video/webm": (Video, "webm")}

def setup_db(db_file_name):
    """Return a database connection cursor for the given database file."""

    db = sqlite3.connect(db_file_name)
    db.row_factory = sqlite3.Row
    return db.cursor()

def contact_from_row(row):
    """Return a Contact object based on one row in the table recipient."""

    primary_source = row["profile_joined_name"]
    secondary_source = row["system_joined_name"]
    if primary_source is not None and len(primary_source) > 0:
        name = primary_source
        alternate_name = secondary_source
    else:
        name = secondary_source
        alternate_name = None

    return Contact(id=int(row["_id"]), name=name, alternate_name=alternate_name)

def find_contact(cursor, s):
    """Find all contacts whose name contains the given string."""

    r = "%{}%".format(s)
    query = "SELECT * FROM recipient WHERE profile_joined_name LIKE ? OR system_joined_name LIKE ?"
    return [contact_from_row(row) for row in cursor.execute(query, (r, r, ))]

def find_group(cursor, s):
    """Find all groups whose name contains the given string."""

    results = []
    query = "SELECT recipient._id, groups.title FROM groups LEFT JOIN recipient ON groups.group_id = recipient.group_id WHERE groups.title LIKE ?"
    for row in cursor.execute(query, ("%{}%".format(s), )):
        results.append(Group(id=int(row["_id"]), name=row["title"]))

    return results

def list_groups(cursor):
    """Returns all groups which have messages."""

    results = []
    query = "SELECT recipient._id, groups.title FROM groups LEFT JOIN recipient ON groups.group_id = recipient.group_id JOIN thread ON recipient._id = thread.recipient_id AND EXISTS(SELECT 1 FROM message WHERE message.thread_id = thread._id)"
    for row in cursor.execute(query):
        results.append(Group(id=int(row["_id"]), name=row["title"]))

    return results

def list_contacts(cursor):
    """Returns all contacts which have messages."""

    query = "SELECT recipient._id, profile_joined_name, system_joined_name FROM recipient JOIN thread ON recipient._id = thread.recipient_id WHERE recipient.group_id IS NULL AND EXISTS(SELECT 1 FROM message WHERE message.thread_id = thread._id)"
    return [contact_from_row(row) for row in cursor.execute(query)]

def find_thread_recipient(cursor, recipient):
    """Find the thread id for the recipient. This is for internal use."""

    # We currently assume that thread.recipient_id contains only one recipient
    # id. This has been true for all databases encountered so far.
    rows = cursor.execute("SELECT * FROM thread WHERE recipient_id = ? LIMIT 2", (str(recipient.id), )).fetchall()
    if len(rows) > 1:
        raise NotImplementedError("More than one thread found for recipient with name '{}'. Handling this is unsupported.".format(recipient.name))

    recipient.thread_id = rows[0]["_id"]

def get_messages(cursor, recipient, address_book, default_recipient=None):
    """Return all messages for the given recipient (group or contact) as a list
    of Message objects ordered by message date."""

    """
    My current understanding is the following.

    Messages are stored in the table messages. The recipient (a contact or a
    group) has a thread id which is used to obtain messages related to this
    recipient from this table. Determining the sender of a message is curiously
    tricky.

    The default recipient is the person from whose backups the database was
    obtained from. My understanding is that this recipient cannot be determined
    from the database, and must be provided as a parameter.

    If the recipient is a group, then the address field tells the id of the
    sender in the table recipient (this is implemented in the address book)
    except when the sender is the default recipient.

    If the recipient is a contact, then the address field always points to the
    non-default user in the conversation. It seems to me that if the
    date_server field is -1, then the message was sent by the default user. All
    of this is based on observations, and could be wrong. It works for me
    though.
    """

    messages = []

    if not (isinstance(recipient, Group) or isinstance(recipient, Contact)):
        raise Exception("Unknown recipient type '{}'.".format(type(recipient)))

    if recipient.thread_id is None:
        find_thread_recipient(cursor, recipient)

    if default_recipient is None:
        default_recipient = Recipient(id=-1, name="UNKNOWN")

    def process_contact_group(id):
        try:
            contact = address_book.get_contact(int(id))[0]
        except:
            contact = default_recipient

        return contact

    def process_reactions(row):
        reactions = []
        for row in cursor.execute("SELECT * FROM reaction WHERE message_id = ?", (row["_id"], )).fetchall():
            reaction = Reaction(contact=address_book.get_contact(ids=int(row["author_id"]))[0], emoji=row["emoji"], date=int(row["date_sent"])/1000)
            reactions.append(reaction)

        return reactions

    # Get messages.
    for row in cursor.execute("SELECT * FROM message WHERE thread_id = ?", (recipient.thread_id, )).fetchall():
        # sender
        if isinstance(recipient, Group):
            contact = process_contact_group(row["from_recipient_id"])
        else:
            if row["date_server"] == -1:
                contact = default_recipient
            else:
                contact = address_book.get_contact(int(row["from_recipient_id"]))[0]
        # If the name is not available, then our best option is to use the
        # default recipient. It seems that this happens with messages
        # concerning changes in group settings.
        if len(contact.name) == 0:
          contact = default_recipient

        # reactions
        reactions = process_reactions(row)

        # attachments
        attachments = []
        for row_attachment in cursor.execute("SELECT * FROM attachment WHERE message_id = ?", (row["_id"], )):
            content_type = row_attachment["content_type"]
            file_name = "Attachment_{}_-1.bin".format(row_attachment["_id"])
            cls, extensions = types[content_type]
            attachments.append(cls(file_name=file_name, timestamp=row_attachment["upload_timestamp"], content_type=content_type))

        # quotes
        if row["quote_id"] is not None and row["quote_id"] > 0:
            sender = process_contact_group(row["quote_author"])
            # In my data I have never seen that row["quote_attachment"] != -1,
            # so I am ignoring quote attachments.
            quote = Message(id=-1, sender=sender, date=int(row["quote_id"])/1000, message=row["quote_body"])
        else:
            quote = None

        # mentions
        mentions = []
        if row["body"] is not None:
            for row_mention in cursor.execute("SELECT * FROM mention WHERE thread_id = ? AND message_id = ?", (recipient.thread_id, row["_id"], )).fetchall():
                mention_contact = address_book.get_contact(int(row_mention["recipient_id"]))[0]
                mention_range = [int(row_mention["range_start"]), int(row_mention["range_length"])]
                mentions.append([mention_contact, mention_range])

        messages.append(Message(id=int(row["_id"]), sender=contact, date=int(row["date_sent"])/1000, message=row["body"], reactions=reactions, attachments=attachments, quote=quote, mentions=mentions))

    # Order by date.
    messages.sort(key=lambda m: m.date)

    return messages

