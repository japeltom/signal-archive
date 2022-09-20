#!/usr/bin/python3
# -*- coding: utf-8 -*-

from util import get_config
from db import setup_db, list_groups, list_contacts

if __name__ == "__main__":
    config = get_config()
    cursor = setup_db(config["db_file_name"])

    # Contacts.
    print("Contacts with messages:")
    print("-----------------------")
    for contact in list_contacts(cursor):
        print(contact.name)

    # Groups.
    print()
    print("Groups with messages:")
    print("---------------------")
    for group in list_groups(cursor):
        print(group.name)

