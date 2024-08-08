from zino.api.server import ZinoServer
from zino.state import ZinoState


def test_zinoserver_should_serve_without_error(event_loop):
    server = ZinoServer(loop=event_loop, state=ZinoState(), polldevs=dict())
    server.serve()
    server.notify_server.close()
    server.api_server.close()
