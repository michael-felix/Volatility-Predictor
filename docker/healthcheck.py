"""Container health check.

Succeeds only if the API's own `/health` endpoint returns 200, so
Docker/orchestrators can detect a crashed or unresponsive container
without needing `curl` installed in the slim runtime image. Note this
checks the process is alive and serving requests — it does not fail on
a downstream MongoDB outage (the API itself reports that as "degraded"
in the response body), since restarting the API container wouldn't fix
a database that's down anyway.
"""

import sys
import urllib.request

try:
    # /health itself waits on MongoDB's serverSelectionTimeoutMS (5s) before
    # falling back to "degraded" when the database is unreachable, so this
    # request's own timeout must comfortably exceed 5s or a Mongo outage
    # would make Docker mark the container unhealthy for the wrong reason.
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=8) as response:
        sys.exit(0 if response.status == 200 else 1)
except Exception:
    sys.exit(1)
