import socket
import pickle

HOST = "localhost"
PORT = 50007

def _broadcast(HOST, PORT, message):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, int(PORT)))
    s.send(pickle.dumps(message))
    s.close()

def _receive(HOST, PORT):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.4)
    s.bind((HOST, int(PORT)))
    s.listen(1)
    conn, addr = s.accept()
    data = conn.recv(4096)
    conn.close()    
    return pickle.loads(data)

#---------------------------------------

def broadcast(HOST, PORT, message):
    try:
        _broadcast(HOST, PORT, message)
    except:
        pass

def receive(HOST, PORT):
    try:
        message = _receive(HOST, PORT)
        return message
    except:
        return None

    


    
