import sqlite3

from data import *

types = {"application/pdf": (Attachment, ["pdf"]),
         "audio/aac": (Audio, ["aac", "m4a"]),
         "audio/mp3": (Audio, ["mp3"]),
         "audio/mp4": (Audio, ["mp4"]),
         "audio/mpeg": (Audio, ["mpeg"]),
         "audio/ogg; codecs=opus": (Audio, ["ogg"]),
         "audio/wav": (Audio, ["wav"]),
         "image/*": (Image, ["jpg"]),
         "image/bmp": (Image, ["bmp"]),
         "image/gif": (Image, ["gif"]),
         "image/heif": (Image, ["heif"]),
         "image/jpeg": (Image, ["jpg"]),
         "image/png": (Image, ["png"]),
         "image/webp": (Image, ["webp"]),
         "image/x-icon": (Attachment, [""]),
         "text/x-signal-plain": (Attachment, [""]),
         "video/*": (Video, ["mp4"]),
         "video/mp4": (Video, ["mp4", ""]), # strangely some mp4 files are without extension
         "video/mpeg": (Video, ["mp4"]),
         "video/quicktime": (Video, ["qt"]),
         "video/webm": (Video, ["webm"])}

def setup_db(db_file_name):
    """Return a database connection cursor for the given database file."""

    db = sqlite3.connect(db_file_name)
    db.row_factory = sqlite3.Row
    return db.cursor()

def contact_from_row(row):
    """Return a Contact object based on one row in the table recipient."""

    if row["signal_profile_name"] is not None and len(row["signal_profile_name"]) > 0:
        name = row["signal_profile_name"]
        alternate_name = row["system_display_name"]
    else:
        name = row["system_display_name"]
        alternate_name = None

    return Contact(id=int(row["_id"]), name=name, alternate_name=alternate_name)

def find_contact(cursor, s):
    """Find all contacts whose name contains the given string."""

    r = "%{}%".format(s)
    query = "SELECT * FROM recipient WHERE system_display_name LIKE ? OR signal_profile_name LIKE ?"
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
    query = "SELECT recipient._id, groups.title FROM groups LEFT JOIN recipient ON groups.group_id = recipient.group_id JOIN thread ON recipient._id = thread.recipient_ids WHERE thread.message_count > 0"
    for row in cursor.execute(query):
        results.append(Group(id=int(row["_id"]), name=row["title"]))

    return results

def list_contacts(cursor):
    """Returns all contacts which have messages."""

    query = "SELECT recipient._id, signal_profile_name, system_display_name FROM recipient JOIN thread ON recipient._id = thread.recipient_ids WHERE recipient.group_id IS NULL AND thread.message_count > 0"
    return [contact_from_row(row) for row in cursor.execute(query)]

def find_thread_recipient(cursor, recipient):
    """Find the thread id for the recipient. This is for internal use."""

    # We currently assume that thread.recipient_ids contains only one recipient
    # id. This has been true for all databases encountered so far.
    rows = cursor.execute("SELECT * FROM thread WHERE recipient_ids = ? LIMIT 2", (str(recipient.id), )).fetchall()
    if len(rows) > 1:
        raise NotImplementedError("More than one thread found for recipient with name '{}'. Handling this is unsupported.".format(recipient.name))

    recipient.thread_id = rows[0]["_id"]

def get_messages(cursor, recipient, address_book, default_recipient=None):
    """Return all messages for the given recipient (group or contact) as a list
    of Message objects ordered by message date."""

    """
    My current understanding is the following.

    There are two types of messages SMS and MMS corresponding to the tables sms
    and mms. The recipient (a contact or a group) has a thread id which is used
    to obtain messages related to this recipient from both tables. Determining
    the sender of a message is curiously tricky.

    The default recipient is the person from whose backups the database was
    obtained from. My understanding is that this recipient cannot be determined
    from the database, and must be provided as a parameter.

    If the recipient is a group, then the address field tells the id of the
    sender in the table recipient (this is implemented in the address book)
    except when the sender is the default recipient. This works similarly for
    both SMS and MMS messages.

    If the recipient is a contact, then the address field always points to the
    non-default user in the conversation. It seems to me that for SMS messages
    the protocol field is NULL when the message was sent by the default user
    and not NULL otherwise. For MMS messages, if the date_server field is -1,
    then the message was sent by the default user. All of this is based on
    observations, and could be wrong. It works for me though.
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
        reactions_blob = row["reactions"]
        reactions = []
        if reactions_blob is not None:
            for data in ReactionDataList.loads(reactions_blob).reactions:
                reactions.append(Reaction(contact=address_book.get_contact(ids=data.author)[0], emoji=data.emoji, date=data.sentTime/1000))

        return reactions

    # Get SMS messages.
    for row in cursor.execute("SELECT * FROM sms WHERE thread_id = ?", (recipient.thread_id, )).fetchall():
        # sender
        if isinstance(recipient, Group):
            contact = process_contact_group(row["address"])
        else:
            if row["protocol"] is None:
                contact = default_recipient
            else:
                contact = address_book.get_contact(int(row["address"]))[0]

        # reactions
        reactions = process_reactions(row)

        messages.append(SMS(id=int(row["_id"]), sender=contact, date=int(row["date"])/1000, message=row["body"], reactions=reactions))

    # Get MMS messages.
    for row in cursor.execute("SELECT * FROM mms WHERE thread_id = ?", (recipient.thread_id, )).fetchall():
        # sender
        if isinstance(recipient, Group):
            contact = process_contact_group(row["address"])
        else:
            if row["date_server"] == -1:
                contact = default_recipient
            else:
                contact = address_book.get_contact(int(row["address"]))[0]

        # reactions
        reactions = process_reactions(row)

        # attachments
        attachments = []
        for row_attachment in cursor.execute("SELECT * FROM part WHERE mid = ?", (row["_id"], )):
            content_type = row_attachment["ct"]
            file_name_base = "{}_{}".format(row_attachment["unique_id"], row_attachment["_id"])
            cls, extensions = types[content_type]
            attachments.append(cls(file_name_base=file_name_base, file_name_extensions=extensions, content_type=content_type))

        # quotes
        if row["quote_id"] is not None and row["quote_id"] > 0:
            sender = process_contact_group(row["quote_author"])
            # In my data I have never seen that row["quote_attachment"] != -1,
            # so I am ignoring quote attachments.
            quote = Message(id=-1, sender=sender, date=int(row["quote_id"])/1000, message=row["quote_body"])
        else:
            quote = None

        messages.append(MMS(id=int(row["_id"]), sender=contact, date=int(row["date"])/1000, message=row["body"], reactions=reactions, attachments=attachments, quote=quote))

    # Order by date.
    messages.sort(key=lambda m: m.date)

    return messages

