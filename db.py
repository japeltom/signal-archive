import sqlite3

from data import Group, Contact

def setup_db(db_file_name):
    """Return a database connection cursor for the given database file."""

    db = sqlite3.connect(db_file_name)
    db.row_factory = sqlite3.Row
    return db.cursor()

def list_groups(cursor):
    """Returns all groups which have messages."""

    results = []
    for row in cursor.execute("SELECT recipient._id, groups.title FROM groups LEFT JOIN recipient ON groups.group_id = recipient.group_id JOIN thread ON recipient._id = thread.recipient_ids WHERE thread.message_count > 0"):
        results.append(Group(id=int(row["_id"]), name=row["title"]))

    return results

def list_contacts(cursor):
    """Returns all contacts which have messages."""

    results = []
    for row in cursor.execute("SELECT recipient._id, signal_profile_name, system_display_name FROM recipient JOIN thread ON recipient._id = thread.recipient_ids WHERE recipient.group_id IS NULL AND thread.message_count > 0"):
        if row["signal_profile_name"] is not None and len(row["signal_profile_name"]) > 0:
          name = row["signal_profile_name"]
        else:
          name = row["system_display_name"]
        results.append(Contact(id=int(row["_id"]), name=name))

    return results

