# ChatApp
This is a simple chat application that allows multiple users to communicate securely via the command line. The application features message encryption and decryption using the cryptography library.

Clone the repository
git clone <repository_url>
cd <repository_directory>
Install dependencies:

pip install websockets cryptography
Generate encryption keys:

python key_manager.py
Running the Application
Running the Server
Start the server:

python server.py <port> <peer_port_1> <peer_port_2> ...
Example:
python server.py 1234 4321 5678
Running the Client
Start the client:

python client.py <server_address>:<port> <jid> <nickname>
Example:
python client.py 127.0.0.1:1234 user1 Alice
Usage
Client Commands
View Members:

Enter your command(1: view members, 2: chat, 3: view messages): 1
Chat:

Enter your command(1: view members, 2: chat, 3: view messages): 2
Input with format jid:content > <jid>:<message>
View Messages:


Enter your command(1: view members, 2: chat, 3: view messages): 3
Example
Start the server:


python server.py 1234 4321
Start the first client:


python client.py 127.0.0.1:1234 user1 Alice
Start the second client:


python client.py 127.0.0.1:1234 user2 Bob
Client Alice sends a message to Bob:


Enter your command(1: view members, 2: chat, 3: view messages): 2
Input with format jid:content > user2:Hello Bob!
Client Bob views the received message:


Enter your command(1: view members, 2: chat, 3: view messages): 3
This README provides a brief overview and basic usage instructions for the chat application. Feel free to explore and modify the code to suit your needs.








