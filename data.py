from dataclasses import dataclass 

class Reaction:

  def __init__(self, contact, emoji, date):
      self.contact = contact
      self.emoji = emoji
      self.date = date

class Message:

    def __init__(self, id, sender, date, message, reactions=None, attachments=None, quote=None):
        self.id = id
        self.sender = sender
        self.date = date
        self.message = message
        self.reactions = reactions if reactions is not None else []
        self.attachments = attachments
        self.quote = quote

class Attachment:

    def __init__(self, file_name_base, file_name_extensions, content_type):
        self.file_name_base = file_name_base
        self.file_name_extensions = file_name_extensions
        self.content_type = content_type

class Audio(Attachment):
    pass

class Image(Attachment):
    pass  

class Video(Attachment):
    pass

class Recipient:

    def __init__(self, id, name, alternate_name=None, avatar_file_name=None):
        # We have alternate_name because Signal has two sources for names. We
        # use name as de facto name and alternate_name is used to perform
        # searches with a given name more correctly.
        self.id = id
        self.name = name
        self.alternate_name = alternate_name
        self.avatar_file_name = None
        self.thread_id = None

    def __str__(self):
        return "{},{}".format(self.id, self.name)

class Contact(Recipient):
    pass

class Group(Recipient):
    pass

class AddressBook:

    def __init__(self):
        self.contacts = {}

    def add_contact(self, id=None, name=None, alternate_name=None):
        self.contacts[id] = Contact(id=id, name=name, alternate_name=alternate_name)

    def get_contact(self, ids=None, name=None):
        if ids is None and name is None:
            raise ValueError("Both id and name cannot be None.")

        results = []
        if ids is not None:
            if not isinstance(ids, list):
                ids = [ids]

            for id in ids:
                contact = self.contacts.get(id, None)
                if contact is None:
                    raise Exception("No contact with id '{}'.".format(id))
                results.append(contact)
        elif name is not None:
            for contact in self.contacts.values():
                if (contact.name is not None and name in contact.name) or (contact.alternate_name is not None and name in contact.alternate_name):
                    results.append(contact)

        return results

    @classmethod
    def from_db_cursor(cls, cursor):
        address_book = cls()
        for row in cursor.execute("SELECT * FROM recipient"):
            if row["group_id"] is not None: continue
            if row["signal_profile_name"] is not None and len(row["signal_profile_name"]) > 0:
                name = row["signal_profile_name"]
                alternate_name = row["system_display_name"]
            else:
                name = row["system_display_name"]
                alternate_name = None
            address_book.add_contact(id=int(row["_id"]), name=name, alternate_name=alternate_name)

        return address_book

