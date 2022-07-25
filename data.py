from dataclasses import dataclass 

from typing import List, Optional

from pure_protobuf.dataclasses_ import field, message, optional_field
from pure_protobuf.types import uint64

# Reaction data format found in
# https://github.com/signalapp/Signal-Android/blob/main/app/src/main/proto/Database.proto

@message
@dataclass
class ReactionData:
    emoji: str = optional_field(1)
    author: Optional[uint64] = optional_field(2)
    sentTime: Optional[uint64] = optional_field(3)
    receivedTime: Optional[uint64] = optional_field(4)

@message
@dataclass
class ReactionDataList:
    reactions: List[ReactionData] = field(1, default_factory=list)

class Reaction:

  def __init__(self, contact, emoji, date):
      self.contact = contact
      self.emoji = emoji
      self.date = date

class Message:

    def __init__(self, id, sender, date, message, reactions=None, quote=None):
        self.id = id
        self.sender = sender
        self.date = date
        self.message = message
        self.reactions = reactions if reactions is not None else []
        self.quote = quote

class SMS(Message):
    pass

class MMS(Message):

    def __init__(self, id, sender, date, message, reactions=None, attachments=None, quote=None):
        super().__init__(id, sender, date, message, reactions, quote)
        self.attachments = attachments

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

    def __init__(self, id, name, avatar_file_name=None):
        self.id = id
        self.name = name
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

    def add_contact(self, id=None, name=None):
        self.contacts[id] = Contact(id=id, name=name)

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
                if contact.name is not None and name in contact.name:
                    results.append(contact)

        return results

    @classmethod
    def from_db_cursor(cls, cursor):
        address_book = cls()
        for row in cursor.execute("SELECT * FROM recipient"):
            if row["group_id"] is not None: continue
            name = row["signal_profile_name"] if row["signal_profile_name"] is not None else row["system_display_name"]
            address_book.add_contact(id=int(row["_id"]), name=name)

        return address_book

