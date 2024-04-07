#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os

from util import get_config
import db

if __name__ == "__main__":
    config = get_config()
    cursor = db.setup_db(os.path.join(config["data_path"], config["db_file_name"]))

    # Contacts.
    print("Contacts with messages:")
    print("-----------------------")
    for contact in db.list_contacts(cursor):
        print(contact.name)

    # Groups.
    print()
    print("Groups with messages:")
    print("---------------------")
    for group in db.list_groups(cursor):
        print(group.name)

