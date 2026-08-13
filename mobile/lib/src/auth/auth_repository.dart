import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/api_client.dart';
import 'auth_models.dart';

class AuthRepository {
  AuthRepository(this._api, this._storage);

  static const _tokenKey = 'vetpet_access_token';
  final ApiClient _api;
  final FlutterSecureStorage _storage;

  Future<AuthUser?> restoreSession() async {
    final token = await _storage.read(key: _tokenKey);
    if (token == null) return null;
    _api.accessToken = token;
    try {
      return await currentUser();
    } on ApiException catch (error) {
      if (error.statusCode == 401) {
        await signOut();
        return null;
      }
      rethrow;
    }
  }

  Future<AuthUser> login(String email, String password) async {
    final response = await _api.post(
      '/auth/login',
      body: {'email': email.trim(), 'password': password},
    ) as Map<String, dynamic>;
    final token = response['access_token'] as String;
    _api.accessToken = token;
    await _storage.write(key: _tokenKey, value: token);
    return currentUser();
  }

  Future<void> registerOwner({
    required String name,
    required String email,
    required String password,
    String? phone,
  }) async {
    await _api.post('/auth/register/owner', body: {
      'full_name': name.trim(),
      'email': email.trim(),
      'password': password,
      if (phone?.trim().isNotEmpty == true) 'phone': phone!.trim(),
    });
  }

  Future<void> registerDoctor({
    required String name,
    required String email,
    required String password,
    required String licenseNumber,
    required String qualification,
    String? specialization,
  }) async {
    await _api.post('/auth/register/doctor', body: {
      'full_name': name.trim(),
      'email': email.trim(),
      'password': password,
      'license_number': licenseNumber.trim(),
      'qualification': qualification.trim(),
      if (specialization?.trim().isNotEmpty == true)
        'specialization': specialization!.trim(),
    });
  }

  Future<AuthUser> currentUser() async {
    final response = await _api.get('/auth/me') as Map<String, dynamic>;
    return AuthUser.fromJson(response);
  }

  Future<void> signOut() async {
    _api.accessToken = null;
    await _storage.delete(key: _tokenKey);
  }
}

