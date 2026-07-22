import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:mobile/core/network/api_exception.dart';

import '../data/auth_repository.dart';
import 'auth_event.dart';
import 'auth_state.dart';

/// Owns session state for the whole app: startup bootstrap, login, logout,
/// and forced logout on session expiry.
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  AuthBloc(this._authRepository) : super(const AuthInitial()) {
    on<AuthSessionRequested>(_onSessionRequested);
    on<AuthLoginRequested>(_onLoginRequested);
    on<AuthLogoutRequested>(_onLogoutRequested);
    on<AuthSessionExpired>(_onSessionExpired);
  }

  final AuthRepository _authRepository;

  Future<void> _onSessionRequested(
    AuthSessionRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());

    final hasSession = await _authRepository.hasSession();
    if (!hasSession) {
      emit(const AuthUnauthenticated());
      return;
    }

    try {
      final user = await _authRepository.fetchMe();
      emit(AuthAuthenticated(user));
    } on ApiException {
      // ApiClient already attempted a silent refresh internally on a 401;
      // reaching here means that refresh also failed, so the session is
      // gone regardless of the specific error code.
      emit(const AuthUnauthenticated());
    }
  }

  Future<void> _onLoginRequested(
    AuthLoginRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());
    try {
      final response = await _authRepository.login(
        email: event.isEmail ? event.emailOrPhone : null,
        phone: event.isEmail ? null : event.emailOrPhone,
        password: event.password,
      );
      emit(AuthAuthenticated(response.user));
    } on ApiException catch (e) {
      final message = e.isAccountLocked
          ? 'Too many failed attempts — try again in 15 minutes.'
          : e.message;
      // AuthFailure is transient: the UI shows it once via BlocListener,
      // then the bloc falls back to AuthUnauthenticated so the login form
      // stays interactive.
      emit(AuthFailure(message, isAccountLocked: e.isAccountLocked));
      emit(const AuthUnauthenticated());
    }
  }

  Future<void> _onLogoutRequested(
    AuthLogoutRequested event,
    Emitter<AuthState> emit,
  ) async {
    // AuthRepository.logout() never throws — it always clears the local
    // session even if the network call failed.
    await _authRepository.logout();
    emit(const AuthUnauthenticated());
  }

  Future<void> _onSessionExpired(
    AuthSessionExpired event,
    Emitter<AuthState> emit,
  ) async {
    emit(
      const AuthUnauthenticated(
        'Your session expired — please log in again.',
      ),
    );
  }
}
