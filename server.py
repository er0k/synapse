#!/usr/bin/env python

import sys

from twisted.internet import reactor, ssl
from twisted.python import log
from twisted.web.static import File
from twisted.web.server import Site

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol, \
    listenWS

from autobahn.twisted.resource import WebSocketResource


class BroadcastServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
        self.factory.register(self)

    def onMessage(self, payload, isBinary):
        if not isBinary:
            msg = "{} from {}".format(payload.decode('utf8'), self.peer)
            self.factory.broadcast(msg)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class BroadcastServerFactory(WebSocketServerFactory):

    """
    Simple broadcast server broadcasting any message it receives to all
    currently connected clients.
    """

    def __init__(self, url):
        WebSocketServerFactory.__init__(self, url)
        self.clients = []
        self.tickcount = 0
        self.tick()

    def tick(self):
        self.tickcount += 1
        self.broadcast("tick %d from server" % self.tickcount)
        reactor.callLater(10, self.tick)

    def register(self, client):
        if client not in self.clients:
            print("registered client {}".format(client.peer))
            self.clients.append(client)
            self.broadcast("{} joined".format(client.peer))

    def unregister(self, client):
        if client in self.clients:
            print("unregistered client {}".format(client.peer))
            self.clients.remove(client)
            self.broadcast("{} left".format(client.peer))

    def broadcast(self, msg):
        print("broadcasting message '{}' ..".format(msg))
        for c in self.clients:
            c.sendMessage(msg.encode('utf8'))
            print("message sent to {}".format(c.peer))


class BroadcastPreparedServerFactory(BroadcastServerFactory):

    """
    Functionally same as above, but optimized broadcast using
    prepareMessage and sendPreparedMessage.
    """

    def broadcast(self, msg):
        print("broadcasting prepared message '{}' ..".format(msg))
        preparedMsg = self.prepareMessage(msg)
        for c in self.clients:
            c.sendPreparedMessage(preparedMsg)
            print("prepared message sent to {}".format(c.peer))


if __name__ == "__main__":
    log.startLogging(sys.stdout)

    # SSL server context: load server key and cert
    # used for both ws and http
    contextFactory = ssl.DefaultOpenSSLContextFactory('keys/server.key', 'keys/server.crt')

    factory = BroadcastPreparedServerFactory(u"wss://127.0.0.1:9000")

    factory.setProtocolOptions(
        allowedOrigins=[
            "https://127.0.0.1:8080",
            "https://localhost:8080",
            "https://er0k.org:8080",
        ]
    )
    factory.protocol = BroadcastServerProtocol
    listenWS(factory, contextFactory)

    webdir = File('www')
    webdir.contentTypes['.crt'] = 'application/x-x509-ca-cert'
    web = Site(webdir)
    reactor.listenSSL(8080, web, contextFactory)

    reactor.run()
