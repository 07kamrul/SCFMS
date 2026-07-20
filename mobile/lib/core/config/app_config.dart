/// Compile-time environment configuration, supplied via `--dart-define` or
/// `--dart-define-from-file` (see `mobile/env/*.json`). Never holds secrets —
/// only non-sensitive, per-environment values like the API base URL.
class AppConfig {
  AppConfig._();

  /// Backend base URL, including the `/api/v1` prefix.
  ///
  /// Defaults to the Android-emulator loopback alias so `flutter run` with
  /// no flags behaves exactly as before this config was introduced.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://144.79.249.166:18000/api/v1',
  );
}
