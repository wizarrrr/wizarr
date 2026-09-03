"""Run the API-check mock as a standalone server for manual testing.

    uv run python -m tests.external.api_check.run_mock_api --port 8899

Point a wizard step's API Gate at ``http://127.0.0.1:8899/check`` and drive the
answer from ``http://127.0.0.1:8899/_control/`` while you click through the
wizard. Every request is listed there, including whether its Wizarr signature
verified.
"""

import argparse
import threading

from tests.external.api_check.mock_api_server import MockApiServer, _Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument(
        "--status", type=int, default=403, help="initial answer for /check"
    )
    parser.add_argument(
        "--secret", default=None, help="verify Wizarr's HMAC with this key"
    )
    parser.add_argument(
        "--expect-code", default=None, help="only accept this invite code"
    )
    parser.add_argument("--expect-username", default=None)
    parser.add_argument("--expect-email", default=None)
    args = parser.parse_args()

    server = MockApiServer(
        status=args.status,
        hmac_secret=args.secret,
        expect_code=args.expect_code,
        expect_username=args.expect_username,
        expect_email=args.expect_email,
        control_enabled=True,
    )
    server._server = MockApiServer._Server(("127.0.0.1", args.port), _Handler, server)

    thread = threading.Thread(target=server._server.serve_forever, daemon=True)
    thread.start()

    print(f"mock API      : {server.url}/check")
    print(f"control panel : {server.url}/_control/")
    print(f"answering     : {args.status}")
    print("Ctrl-C to stop")
    try:
        thread.join()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
