import 'package:mobile/core/di/injection.dart';

import 'bloc/auth_bloc.dart';
import 'data/auth_repository.dart';

/// Registers this feature's repository and bloc with [getIt].
///
/// [AuthBloc] is a singleton (not a factory) — the router's
/// `GoRouterRefreshStream` and every page that gates on auth state must all
/// observe the same instance.
void registerAuthDependencies() {
  getIt.registerLazySingleton(() => AuthRepository(getIt(), getIt()));
  getIt.registerLazySingleton(() => AuthBloc(getIt()));
}
