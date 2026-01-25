from server import app
from config import CFG

if __name__ == "__main__":
    # The background processing thread now starts automatically 
    # when server.py is imported or run.
    app.run(host=CFG.host, port=CFG.port, threaded=True)
