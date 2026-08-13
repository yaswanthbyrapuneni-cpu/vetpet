import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../auth/auth_controller.dart';
import '../auth/auth_models.dart';
import '../auth/login_screen.dart';
import '../auth/register_screen.dart';
import '../doctors/doctors_screen.dart';
import '../home/home_screen.dart';
import '../pets/pet_form_screen.dart';
import '../pets/pets_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final auth = ref.read(authControllerProvider);
  final router = GoRouter(
    initialLocation: '/loading',
    refreshListenable: auth,
    redirect: (context, state) {
      final status = auth.state.status;
      final authRoute = state.matchedLocation == '/login' ||
          state.matchedLocation == '/register';
      if (status == AuthStatus.loading) {
        return state.matchedLocation == '/loading' ? null : '/loading';
      }
      if (status == AuthStatus.signedOut) return authRoute ? null : '/login';
      if (authRoute || state.matchedLocation == '/loading') return '/home';
      if (state.matchedLocation.startsWith('/pets') &&
          auth.state.user?.role != UserRole.owner) {
        return '/home';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/loading',
        builder: (context, state) => const _LoadingScreen(),
      ),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(path: '/home', builder: (context, state) => const HomeScreen()),
      GoRoute(path: '/pets', builder: (context, state) => const PetsScreen()),
      GoRoute(
        path: '/pets/new',
        builder: (context, state) => const PetFormScreen(),
      ),
      GoRoute(
        path: '/pets/:petId/edit',
        builder: (context, state) => PetFormScreen(
          petId: state.pathParameters['petId'],
        ),
      ),
      GoRoute(
        path: '/doctors',
        builder: (context, state) => const DoctorsScreen(),
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});

class _LoadingScreen extends StatelessWidget {
  const _LoadingScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
