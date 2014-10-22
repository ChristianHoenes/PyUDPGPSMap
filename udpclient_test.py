import socket
import select
import sys
import threading
import gobject

try:
    import pygtk
    pygtk.require("2.0")
except:
    pass
try:
    import gtk
except:
    print("GTK not available!")
    sys.exit(1)

gobject.threads_init()

class GUI:
    def __init__(self, UDPClient):
        self.udpClient = UDPClient

        self.builder = gtk.Builder()
        self.builder.add_from_file("TestUDPListenerREORG.ui")
        dic = {"on_mainWindow_destroy" : self.quit,
             "on_listenButton_clicked" : self.startThread,
         "on_stopListenButton_clicked" : self.stopListening}
        self.builder.connect_signals(dic)

        self.textView = self.builder.get_object("messagesReceivedEntry").get_buffer()
        self.textViewText = self.textView.get_text(self.textView.get_start_iter(),self.textView.get_end_iter())

        self.listening = False
        self.listenerThread = threading.Thread(target = self.listen)

    def startThread(self, widget):
        self.listenerThread.start()
        pass

    def listen(self):
        try:
            self.udpClient.connect()
        except:
            print "Cannot connect."
        try:
            while True:
                result = select.select([self.udpClient.client],[],[])
                message = result[0][0].recv(1024)
                print message
                gobject.idle_add(self.updateGUI, message)
        except:
            print "Cannot receive message"

    def updateGUI(self, message):
        print "updating..."
        self.textView.set_text(self.textViewText + "\n" + message)
        print message

    def quit(self, widget):
        self.udpClient.close()
        sys.exit(0)

    def stopListening(self, widget):
        pass



class UDPClient:
    def __init__(self, IPAddress, portNumber):
        self.IPAddress = IPAddress
        self.portNumber = portNumber
        self.bufferSize = 32

        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def connect(self):
        try:
            self.client.bind((self.IPAddress, self.portNumber))
            self.client.setblocking(0)
        except: print "Cannot connect."

    def close(self):
        try:
            self.client.close()
        except:
            pass

udpClient = UDPClient("192.168.1.13", 1313)
gui = GUI(udpClient)
gtk.main() 
