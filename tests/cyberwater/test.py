import pytest
import uvicorn
import threading
import time
import contextlib

from ModelDataExchange.clients.cyberwater.high_level_api import set_server_url, start_session, SessionData
from ModelDataExchange.server.exchange_server import app 


# Server class allows the uvicorn server to be run while testing
#
# See link below for source of the Server class
# https://github.com/encode/uvicorn/issues/742#issuecomment-674411676
class Server(uvicorn.Server):

    def signal_handler(self):
        pass
    
    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()

        try:
            while not self.started:
                # Startup is not instantaneous. Client will fail to connect
                # if we don't wait for the server to start.
                time.sleep(1e-3)
            yield
        finally: # This is called when start_server is finished yielding
            self.should_exit = True
            thread.join()
    

class Test:

    @pytest.fixture(autouse=True)
    def setUp(self):
        # Set the server URL before each test
        set_server_url("http://0.0.0.0:8000")
        self.session_data = SessionData(
            source_model_id=2001,
            destination_model_id=2005,
            initiator_id=35,
            invitee_id=38,
            input_variables_id=[1],
            input_variables_size=[50],
            output_variables_id=[4],
            output_variables_size=[50]
        )

    @pytest.fixture(autouse=True, scope="session")
    def start_server(self):
        """
        Server fixture for each test. Every test will start on a fresh server instance
        """

        config = uvicorn.Config(app=app, host="0.0.0.0", port=8000)
        server = Server(config)

        # Tests are run in this context
        with server.run_in_thread():
            yield

    def test_start_session_success(self):
        """ Test successful start of a session """
        # Assuming `start_session` returns some status or None if successful
        result = start_session(self.session_data)
        
        if result is not None:
            assert result.get("status") == "created", "Session should start successfully without any errors."
        else:
            assert False, "Session should start successfully without any errors."

    def test_start_session_without_url(self):
        """ Test starting a session without setting server URL """
        
        with pytest.raises(Exception) as context:
            set_server_url("")  # Clearing the server URL
            assert str(context) in "Error: Invalid server URL provided." 
        
        # Server should not start without resetting URL
        assert True if start_session(self.session_data) is None else False

        
    def test_start_session_invalid_data(self):
        """ Test starting a session with invalid session data """
        
        # Invalid source model ID
        self.session_data.source_model_id = None # type: ignore  
        
        with pytest.raises(Exception) as context:
            start_session(self.session_data)
            assert "invalid input" in str(context).lower()