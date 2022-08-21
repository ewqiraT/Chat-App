import pickle
import socket
import threading
import Clientui
import Dialogui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import sys

FLAG = False
client_infos = dict()
NICKNAMES = []

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Clientui.Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.textEdit.setReadOnly(True)
        self.setWindowTitle('Chat Client')
        self.ui.actionDisconnect.setEnabled(False)
        self.ui.actionConnect_to_Chat.triggered.connect(self.connectionTriggredHandler)
        self.ui.actionDisconnect.triggered.connect(self.connectionDisconnectHandler)
        self.ui.actionExit.triggered.connect(self.actionExitHandler)
        self.ui.pushButtonSend.clicked.connect(self.pushButtonSendHandler)
        self.ui.lineEdit.returnPressed.connect(self.pushButtonSendHandler)
        self.ui.textEdit.setLineWrapMode(QTextEdit.NoWrap)


    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.actionExitHandler()
        if e.key() == Qt.Key_Enter:
            self.pushButtonSendHandler()


    def closeEvent(self, event):
        self.actionExitHandler()

    def pushButtonSendHandler(self):
        self.ui.lineEdit.setFocusPolicy(Qt.StrongFocus)
        self.ui.lineEdit.setFocus()

        message = self.ui.lineEdit.text()
        if message != '' and FLAG:
            client_infos['client'].send(f"SEND_MESSAGE {client_infos['nickname']} {message}".encode())
            self.ui.lineEdit.setText('')


    def actionExitHandler(self):
        if FLAG:
            self.connectionDisconnectHandler()
        self.close()

    def connectionDisconnectHandler(self):
        global FLAG
        try:
            self.ui.textEdit.clear()
            self.ui.textEdit.append('Disconnected...')
            self.ui.labelNickname.setText('')
            FLAG = False
            client_infos['client'].send(f"LOGOUT {client_infos['nickname']}".encode())
        except OSError as oserr:
            print('here', oserr)


    def connectionTriggredHandler(self):
        global FLAG
        md = MyDialog()
        result = md.exec()
        if result:
            FLAG = True
            self.ui.textEdit.clear()
            client_thread = threading.Thread(target=client_thread_proc, args=(client_infos['host'], client_infos['port'], client_infos['nickname'], self))
            client_thread.start()



class MyDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ui = Dialogui.Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.lineEditHost.setPlaceholderText('Enter ip adress')
        self.ui.lineEditPort.setPlaceholderText('Enter port number')
        self.ui.lineEditNick.setPlaceholderText('Enter your Nickname')

        self.ui.pushButtonConnect.clicked.connect(self.pushButtonConnectHandler)

    def pushButtonConnectHandler(self):
        try:
            client_infos['host'] = self.ui.lineEditHost.text()
            client_infos['port'] = self.ui.lineEditPort.text()
            nickname = ''.join(self.ui.lineEditNick.text().split())
            client_infos['nickname'] = nickname
            self.done(QDialog.Accepted)

        except Exception as e:
            pass


def client_thread_proc(host, port, nickname, cls):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP) as client_sock:
            client_sock.connect((host, int(port)))
            client_sock.send(f'LOGIN {nickname}'.encode())

            while FLAG:
                process_cmd(client_sock, cls)

    except socket.gaierror as e:
        cls.ui.textEdit.append(f"Yanlış host girişi: <{client_infos['host']}>")
    except ConnectionRefusedError as e:
        cls.ui.textEdit.append(f"Yanlış port girişi: <{client_infos['port']}>")
    except OverflowError as e:
        cls.ui.textEdit.append(f"Yanlış port girişi: <{client_infos['port']}>")
    except TypeError as e:
        cls.ui.textEdit.append(f"Port no integer olmalıdır: <{client_infos['port']}>")
    except ValueError as e:
        cls.ui.textEdit.append(f"Port no integer olmalıdır: <{client_infos['port']}>")


def process_cmd(client_sock, cls):
    global FLAG
    try:
        server_message = client_sock.recv(1024).decode().split()
        if server_message:
            if server_message[0] == 'ERROR':
                FLAG = False
                cls.ui.textEdit.append(f'{server_message[0]} {" ".join(server_message[1:])}')
            elif server_message[0] == 'LOGIN_ACCEPTED':
                return login_accepted(client_sock, cls)
            elif server_message[0] == 'NEW_USER_LOGGED_IN':
                return new_user_logged_in_proc(client_sock, server_message[1], cls)
            elif server_message[0] == 'NEW_MESSAGE':
                return new_message_proc(client_sock, server_message[1], ' '.join(server_message[2:]), cls)
            elif server_message[0] == 'LOGOUT_ACCEPTED':
                return logout_accepted_proc(client_sock, server_message[1], cls)
            elif server_message[0] == 'USER_LOGGED_OUT':
                return user_logged_out_proc(client_sock, server_message[1], cls)
            elif server_message[0] == 'SERVER_CLOSED':
                cls.ui.textEdit.append('Server closed...')
                return logout_accepted_proc(client_sock, '', cls)

    except ConnectionResetError as e:
        cls.ui.textEdit.append('Server closed...')
        return logout_accepted_proc(client_sock, '', cls)


def login_accepted(client_sock, cls):
    global NICKNAMES
    cls.ui.labelNickname.setText(f"Nickname: {client_infos['nickname']}")
    NICKNAMES = pickle.loads(client_sock.recv(1024))
    cls.ui.listWidget.addItems(NICKNAMES)
    client_infos['client'] = client_sock
    cls.ui.actionDisconnect.setEnabled(True)
    cls.ui.actionConnect_to_Chat.setEnabled(False)
    cls.ui.labelConnectionInfo.setText('Connected...')
    cls.ui.textEdit.append('You joined the chat. Say hi to everyone!')

def new_user_logged_in_proc(client_sock, nickname, cls):
    cls.ui.textEdit.append(f'{nickname} joined the chat !')
    cls.ui.textEdit.moveCursor(QTextCursor.End)
    cls.ui.listWidget.addItem(nickname)
    NICKNAMES.append(nickname)


def new_message_proc(client_sock, nickname, message, cls):
    text = f'{nickname} > {message}'
    cls.ui.textEdit.append(text)
    cls.ui.textEdit.moveCursor(QTextCursor.End)


def logout_accepted_proc(client_sock, nickname, cls):
    global FLAG
    cls.ui.listWidget.clear()
    cls.ui.actionConnect_to_Chat.setEnabled(True)
    cls.ui.actionDisconnect.setEnabled(False)
    cls.ui.labelConnectionInfo.setText('Waiting for connection...')
    FLAG = False

def user_logged_out_proc(client_sock, nickname, cls):
    cls.ui.textEdit.append(f'{nickname} left the chat !')
    cls.ui.textEdit.moveCursor(QTextCursor.End)
    NICKNAMES.remove(nickname)
    cls.ui.listWidget.clear()
    cls.ui.listWidget.addItems(NICKNAMES)


app = QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()
app.exec()

