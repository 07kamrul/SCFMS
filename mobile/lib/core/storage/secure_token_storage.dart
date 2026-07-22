import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persists the access/refresh token pair in the platform secure store
/// (Android EncryptedSharedPreferences / Keystore-backed). Everything that
/// needs the current tokens (the [ApiClient] auth interceptor, session
/// bootstrap on app start, logout) goes through this single class rather
/// than touching `FlutterSecureStorage` directly.
class SecureTokenStorage {
  SecureTokenStorage({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  static const _accessTokenKey = 'scfms_access_token';
  static const _refreshTokenKey = 'scfms_refresh_token';

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await Future.wait([
      _storage.write(key: _accessTokenKey, value: accessToken),
      _storage.write(key: _refreshTokenKey, value: refreshToken),
    ]);
  }

  Future<String?> readAccessToken() => _storage.read(key: _accessTokenKey);

  Future<String?> readRefreshToken() => _storage.read(key: _refreshTokenKey);

  Future<void> clear() async {
    await Future.wait([
      _storage.delete(key: _accessTokenKey),
      _storage.delete(key: _refreshTokenKey),
    ]);
  }
}
