# signal-archive
The purpose of this Python code is to transform a Signal backup file into an archived HTML format which has a look similar to the Signal app and a search feature. I created this project in order to archive the chats from my beloved brother Sauli Peltomäki's (1996-2021) phone and to share them with family members and Sauli's friends. Originally the code supported the backup format used at the time I pulled the backup from my brother's phone. The code has subsequently been updated to support more recent formats. The latest update was done based on a backup created on 16.3.2024. This project is dedicated to Sauli.

# Usage
* Use <https://github.com/bepaald/signalbackup-tools> to decrypt the Signal backup file. For reference, the relevant command is `signalbackup-tools/build/signalbackup-tools <backup-file> <password> --output <output_path>`. After this, the output path should have everything needed for the backups including the database file `database.sqlite`.
* Create a JSON file describing which contact or group to process. The key `contact` (as in the example file) refers to contacts (single persons) and the key `group` to groups. So if you have a group named `Family`, write `"group": "Family"` in the JSON file.
* When the example JSON file is run, a directory `archived` will be created in the current directory. If such a directory already exists, files can be overwritten.
* Default recipient (key `default_recipient`) needs to be specified. The default recipient is the person from whose phone the backups are from.
* The values of the key `contacts` allow to rename contacts and override avatar files and colors for each contact.
* When done setuping, run `./signal-archive.py <file>` where `<file>` is the JSON file you have created.
* Open the file `out.html` from the output path to view the messages.

# Misc
* Stickers are unsupported because the backup files I processed did not use them.
* I recommend to view the HTML files on a desktop browser.
* The format is designed in such a way that the body contents of the HTML files can be concatenated. Thus if you receive new messages but do not have older backups, do not worry and just concatenate to obtain one whole file. Files under `attachments` need to be copied as well.

