import pickle
import socket
import threading
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import sys
import Serverui

PORT_NO = 50500

server = None

nicknames = []
clients = []
toplevelitems = []


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.ui = Serverui.Ui_MainWindow()
        self.ui.setupUi(self)
        self.server_flag = False

        self.ui.actionStart.triggered.connect(self.actionStartHandler)
        self.ui.actionStart_2.triggered.connect(self.actionStartHandler)
        self.ui.actionStop.triggered.connect(self.actionStopHandler)
        self.ui.actionStop_2.triggered.connect(self.actionStopHandler)
        self.ui.actionExit.triggered.connect(self.actionExitHandler)
        self.setWindowTitle('Chat Server')
        self.ui.actionStart_2.setIcon(QIcon('icons/play.png'))
        self.ui.actionStop.setIcon(QIcon('icons/stop.png'))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.actionExitHandler()

    def closeEvent(self, event):
        self.actionExitHandler()

    def actionExitHandler(self):
        if self.server_flag:
            self.actionStopHandler()
        self.close()

    def actionStartHandler(self):
        self.server_flag = True
        server_thread = threading.Thread(target=server_socket_proc, args=(self, ))
        server_thread.start()

    def actionStopHandler(self):
        if self.server_flag:
            print('Server closed...')
            self.server_flag = False
            self.ui.labelConnectionInfo.setText('Stopped...')
            self.ui.treeWidget.clear()
            for client in clients:
                client.send('SERVER_CLOSED'.encode())
            clients.clear()
            nicknames.clear()
            server.close()
            self.ui.textEdit.clear()


def server_socket_proc(cls):
    global server
    if cls.server_flag:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP) as server_sock:
                server_sock.bind(('', PORT_NO))
                server_sock.listen()
                server = server_sock
                cls.ui.labelConnectionInfo.setText('Server listening...')
                print('Waiting for connection...')

                while cls.server_flag:
                    client_sock, (client_addr, client_port) = server_sock.accept()
                    print(f'Connected with client {client_addr}: {client_port}...')
                    cls.client_flag = True

                    client_thread = threading.Thread(target=client_thread_proc, args=(client_sock, client_addr, client_port, cls))
                    client_thread.start()

        except OSError:
            pass


def client_thread_proc(client_sock, client_addr, client_port, cls):
    while cls.server_flag:
        process_cmd(client_sock, cls, client_addr, client_port)


def process_cmd(client_sock, cls, client_addr, client_port):
    try:
        cmd_dict = {'LOGIN': login_proc, 'SEND_MESSAGE': send_message_proc, 'LOGOUT': logout_proc, 'ERROR': error_proc}
        while cls.server_flag:
            client_cmd = client_sock.recv(1024).decode().split()
            if client_cmd and cls.server_flag:
                client_message = client_cmd[0]
                text = ' '.join(client_cmd[1:])
                fulltext = f'{client_message} {text}'
                cls.ui.textEdit.append(fulltext)
                cls.ui.textEdit.moveCursor(QTextCursor.End)
                proc = cmd_dict.get(client_message, text)
                return proc(client_sock, text, cls, client_addr, client_port)
    except OSError:
        pass

def login_proc(client_sock, nickname, cls, client_addr, client_port):
    try:
        if nickname not in nicknames:
            client_sock.send(f'LOGIN_ACCEPTED'.encode())
            print(f'{nickname} joined to server')
            user = QTreeWidgetItem(cls.ui.treeWidget)
            user.setText(0, nickname)
            user.setText(1, client_addr)
            user.setText(2, str(client_port))
            for client in clients:
                client.send(f'NEW_USER_LOGGED_IN {nickname}'.encode())
            toplevelitems.append(user)
            clients.append(client_sock)
            nicknames.append(nickname)
            client_sock.send(pickle.dumps(nicknames))
        else:
            error_proc(client_sock, nickname, cls, client_addr, client_port)

    except Exception as e:
        print(e)


def send_message_proc(client_sock, text, cls, client_addr, client_port):
    for client in clients:
        client.send(f'NEW_MESSAGE {text}'.encode())


def logout_proc(client_sock, nickname, cls, client_addr, client_port):
    item = toplevelitems[clients.index(client_sock)]
    index = cls.ui.treeWidget.indexOfTopLevelItem(item)
    cls.ui.treeWidget.takeTopLevelItem(index)
    client_sock.send(f'LOGOUT_ACCEPTED {nickname}'.encode())
    client_sock.shutdown(socket.SHUT_RDWR)
    client_sock.close()
    clients.remove(client_sock)
    nicknames.remove(nickname)
    toplevelitems.remove(item)
    for client in clients:
        client.send(f'USER_LOGGED_OUT {nickname}'.encode())


def error_proc(client_sock, nickname, cls, client_addr, client_port):
    client_sock.send(f'ERROR <{nickname}> already taken. Choose another one !'.encode())


app = QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()
app.exec()

