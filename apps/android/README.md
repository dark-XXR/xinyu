# Android client

The Android P0 client contains SMS login, server-authoritative entitlements,
generation quotes, generation polling, analysis, and the three reply strategies.
OCR, profiles, payments, history, and knowledge entry points remain disabled.

## Build and test

Set `sdk.dir` in an ignored `local.properties`, then run:

```powershell
.\gradlew.bat :app:testDebugUnitTest :app:assembleDebug
.\gradlew.bat :app:connectedDebugAndroidTest
```

The emulator connects to the API at `http://10.0.2.2:8000/`. For local-only SMS
testing, start the development launcher from the repository root:

```powershell
$env:PYTHONPATH = "services/api/src"
python apps/android/tools/run_local_api.py
```

The launcher refuses to run outside the `development` environment and prints the
generated code to its console. Production continues to use the fail-closed SMS
adapter until a real provider is configured.
