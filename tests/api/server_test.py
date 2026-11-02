from zino.api.server import ZinoServer
from zino.state import ZinoState


def test_zinoserver_should_serve_without_error(running_loop):
    server = ZinoServer(loop=running_loop, state=ZinoState(), polldevs=dict())
    server.serve()
    server.notify_server.close()
    server.api_server.close()
