import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/api_client.dart';
import '../core/config.dart';
import 'auth_models.dart';
import 'auth_repository.dart';

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(baseUrl: AppConfig.apiBaseUrl),
);

final secureStorageProvider = Provider<FlutterSecureStorage>(
  (ref) => const FlutterSecureStorage(),
);

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(secureStorageProvider),
  ),
);

final authControllerProvider = ChangeNotifierProvider<AuthController>(
  (ref) => AuthController(ref.watch(authRepositoryProvider))..restore(),
);

class AuthController extends ChangeNotifier {
  AuthController(this._repository);

  final AuthRepository _repository;
  AuthState state = const AuthState.loading();

  Future<void> restore() async {
    try {
      final user = await _repository.restoreSession();
      state = user == null
          ? const AuthState.signedOut()
          : AuthState(status: AuthStatus.signedIn, user: user);
    } catch (_) {
      state = const AuthState.signedOut(
        error: 'Session check failed. You can still sign in again.',
      );
    }
    notifyListeners();
  }

  Future<bool> login(String email, String password) async {
    state = const AuthState(status: AuthStatus.signedOut, busy: true);
    notifyListeners();
    try {
      final user = await _repository.login(email, password);
      state = AuthState(status: AuthStatus.signedIn, user: user);
      notifyListeners();
      return true;
    } on ApiException catch (error) {
      state = AuthState.signedOut(error: error.message);
      notifyListeners();
      return false;
    }
  }

  Future<void> signOut() async {
    await _repository.signOut();
    state = const AuthState.signedOut();
    notifyListeners();
  }
}
