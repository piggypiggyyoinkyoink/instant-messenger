when one user messages another, upload message to a text file - containing source/destination users
- do not upload non-messages (e.g. anything with source/dest = SERVER etc)
when a user loads a conversation, all messages from this conversation should be downloaded and printed to the terminal sequentially.
- iterate through the file and send all messages sent to this conversation by all users
if a user has the chat open when another user messages in this chat, it should be displayed instantly.
- server should attempt to send message to target client. If target client has this conversation open, this message should be printed, 
otherwise either do nothing or notify them somehow