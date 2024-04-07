class Reaction:

  def __init__(self, contact, emoji, date):
      self.contact = contact
      self.emoji = emoji
      self.date = date

class Message:

    def __init__(self, id, sender, date, message, reactions=None, attachments=None, quote=None, mentions=None):
        self.id = id
        self.sender = sender
        self.date = date
        self.message = message
        self.reactions = reactions if reactions is not None else []
        self.attachments = attachments
        self.quote = quote
        self.mentions = mentions

class Attachment:

    def __init__(self, file_name, timestamp, content_type):
        self.file_name = file_name
        self.timestamp = timestamp
        self.content_type = content_type

class Audio(Attachment):
    pass

class Image(Attachment):
    pass  

class Video(Attachment):
    pass

class Recipient:

    def __init__(self, id, name, alternate_name=None, avatar_file_name=None, color=None):
        # We have alternate_name because Signal has two sources for names. We
        # use name as de facto name and alternate_name is used to perform
        # searches with a given name more correctly.
        self.id = id
        self.name = name
        self.alternate_name = alternate_name
        self.avatar_file_name = avatar_file_name
        self.color = color
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
            primary_source = row["profile_joined_name"]
            secondary_source = row["system_joined_name"]
            if primary_source is not None and len(primary_source) > 0:
                name = primary_source
                alternate_name = secondary_source
            else:
                if secondary_source is None or (secondary_source is not None and len(secondary_source) == 0): continue
                name = secondary_source
                alternate_name = None
            address_book.add_contact(id=int(row["_id"]), name=name, alternate_name=alternate_name)

        return address_book

