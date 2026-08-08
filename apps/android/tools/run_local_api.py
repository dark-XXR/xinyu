"""Run the API with a console SMS sender for local Android emulator testing only."""

import uvicorn
from love_reply_api.main import app, settings


class ConsoleSmsSender:
    async def send_login_code(self, *, phone_e164: str, code: str) -> None:
        print(f"LOCAL_SMS {phone_e164} {code}", flush=True)


if __name__ == "__main__":
    if settings.app_env != "development":
        raise RuntimeError("The console SMS sender is restricted to development.")
    app.state.sms_sender = ConsoleSmsSender()
    uvicorn.run(app, host="0.0.0.0", port=8000)
