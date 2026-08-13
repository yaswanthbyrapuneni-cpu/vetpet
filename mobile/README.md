# VetPet Connect mobile client

The Flutter source currently includes:

- secure JWT persistence and session restoration
- pet-owner and veterinarian registration
- role-aware home screens
- owner pet listing, creation, editing, and archival
- public verified-veterinarian directory
- API error, loading, empty, and retry states

## Prerequisites

Flutter is installed at `C:\src\flutter` and its `bin` directory is included in
the user `PATH`. Android, iOS, and web runner folders have been generated.

```powershell
cd mobile
flutter pub get
flutter analyze
flutter test
```

Close and reopen PowerShell or VS Code after a PATH change. The application can
run immediately in Chrome with `flutter run -d chrome`. Android execution still
requires Android SDK command-line tools and an emulator or physical device.

## API address

The default API URL is suitable for an Android emulator:

```text
http://10.0.2.2:8000/api/v1
```

Override it for another device or platform:

```powershell
flutter run --dart-define=VETPET_API_URL=http://127.0.0.1:8000/api/v1
```

A physical device must use the development computer's LAN address and both
devices must be on the same network. Production builds must use HTTPS. If an
Android development build connects to a local HTTP server, explicitly allow
cleartext traffic only in the debug manifest—never in the release manifest.
