enum UserRole { owner, doctor, admin }

class AuthUser {
  const AuthUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
  });

  final String id;
  final String email;
  final String fullName;
  final UserRole role;

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] as String,
      email: json['email'] as String,
      fullName: json['full_name'] as String,
      role: UserRole.values.byName(json['role'] as String),
    );
  }
}

enum AuthStatus { loading, signedOut, signedIn }

class AuthState {
  const AuthState({required this.status, this.user, this.error, this.busy = false});

  const AuthState.loading() : this(status: AuthStatus.loading);
  const AuthState.signedOut({String? error})
      : this(status: AuthStatus.signedOut, error: error);

  final AuthStatus status;
  final AuthUser? user;
  final String? error;
  final bool busy;

  AuthState copyWith({
    AuthStatus? status,
    AuthUser? user,
    String? error,
    bool? busy,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      error: error,
      busy: busy ?? this.busy,
    );
  }
}

