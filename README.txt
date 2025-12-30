Python CLI Instant Messenger

Initialisation:

Start server: python server.py <PORT_NUMBER>
Note: if no port number specified, the default is 42000.

Start client: python client.py <USERNAME> <IP_ADDRESS> <PORT_NUMBER>
Note: default values are "default" "


Instant Messenger commands:

/chat <username> :
Enter chat mode with a user. Subsequent messages are unicasted to user <username>.
Note: <username> has to be online for messages to be received, otherwise attempts to send messages will display a "recipient is offline" message.

/gc <groupname> : 
Enter group chat mode with group <groupname>. Subsequent messages are multicasted to all users in group <groupname>.
If you are not a member of <groupname>, the chat mode will not be changed and a suitable message is displayed.

/broadcast :
Enter broadcast mode. Subsequent messages are broadcasted to all online users.

/join <groupname> : 
Join a group with name <groupname>. If the group does not exist, it will be created.

/leave <groupname> : 
Leave group <groupname>. If you are not a member of the group a suitable message is displayed.
If this command is entered while in the group chat for this group, your chat mode is reset (so you can no longer message the group you just left).
If you are not a member of <groupname>, a suitable message is displayed.

/listfiles : 
List all files (and their size in bytes) in the folder located at the directory in the SERVER_SHARED_FILES environment variable. This environment variable can be read from the Windows User Environment Variables or from a .env file in the same directory as server.py.
If this environment variable does not exist, the default directory is ./SharedFiles 

/dl <filename.ext> : 
Download file <filename.ext> from the shared files directory using the specified protocol. This is TCP by default, but can be changed using /protocol. The size of the downloaded file is also output on successful download.
Files are downloaded to the ./<username>/ directory, which is created if it doesn't exist.

/protocol <tcp|udp> :
Select file download protocol (TCP or UDP). 

/kill : 
Exit the messenger.


All commands can be entered into the terminal from any chat mode, and will perform their function as described above instead of sending a message.
Anything entered into the terminal which does not match any of the above command formats will be interpreted as a message.


The terminal input prompt takes the following format depending on chat mode:
me -> $S_SERVER: Default: messages only get sent to the server, not to any other users.
me -> <username>: Unicast chat mode with <username>. Messages get sent to <username> only.
[BROADCAST] me: Broadcast chat mode. Messages are sent to all other users.
[<groupname>] me: Group chat mode. Messages are sent only to members in <groupname>.

Incoming messages take a similar format:
<username> -> me: Incoming message is a unicast message from <username>.
[BROADCAST] <username>: Incoming message is a broadcast message from <username>.
[<groupname>] <username>: Incoming message is a group chat message sent in group <groupname> from <username>.


Messages are also colour-coded to help differentiate them:
- Broadcast messages are magenta
- outgoing unicast messages are cyan
- incoming unicast messages are blue
- group chat messages are green


CMD, Windows Terminal, PowerShell and the VSCode Terminal all support ANSI escape codes.
If your terminal does not support ANSI escape codes, start the client with a fourth argument "ugly" as follows:
    python client.py <USERNAME> <IP_ADDRESS> <PORT_NUMBER> ugly
This will run the client in "ugly" mode, with no ANSI codes for colours, effects or cursor manipulation.
(you will know if ANSI is not supported as there will be weird characters everywhere)