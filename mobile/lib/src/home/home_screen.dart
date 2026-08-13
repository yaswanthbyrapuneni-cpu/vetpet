import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../auth/auth_controller.dart';
import '../auth/auth_models.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).state.user;
    if (user == null) return const SizedBox.shrink();
    return Scaffold(
      appBar: AppBar(
        title: const Text('VetPet Connect'),
        actions: [
          IconButton(
            tooltip: 'Sign out',
            onPressed: () => ref.read(authControllerProvider).signOut(),
            icon: const Icon(Icons.logout_rounded),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Hello, ${user.fullName}',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 6),
            Text(_subtitle(user.role)),
            const SizedBox(height: 24),
            if (user.role == UserRole.owner) ...[
              _ActionCard(
                icon: Icons.pets_rounded,
                title: 'My pets',
                description: 'Create and manage your pet profiles.',
                onTap: () => context.push('/pets'),
              ),
              const SizedBox(height: 12),
              _ActionCard(
                icon: Icons.medical_services_rounded,
                title: 'Find a veterinarian',
                description: 'Browse veterinarians verified by VetPet Connect.',
                onTap: () => context.push('/doctors'),
              ),
              const SizedBox(height: 12),
              const _ComingSoonCard(
                icon: Icons.calendar_month_rounded,
                title: 'Appointments',
              ),
              const SizedBox(height: 12),
              const _ComingSoonCard(
                icon: Icons.notifications_active_rounded,
                title: 'Reminders',
              ),
            ] else if (user.role == UserRole.doctor) ...[
              const _StatusCard(
                icon: Icons.verified_user_outlined,
                title: 'Professional account',
                description: 'Verification status and bookings are managed securely.',
              ),
              const SizedBox(height: 12),
              const _ComingSoonCard(
                icon: Icons.event_available_rounded,
                title: 'Availability and appointments',
              ),
            ] else ...[
              const _StatusCard(
                icon: Icons.admin_panel_settings_rounded,
                title: 'Administrator',
                description: 'Administrative mobile workflows will be added later.',
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _subtitle(UserRole role) => switch (role) {
        UserRole.owner => 'Keep your pets’ care organized in one place.',
        UserRole.doctor => 'Manage veterinary care securely.',
        UserRole.admin => 'Platform administration overview.',
      };
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.icon,
    required this.title,
    required this.description,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String description;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            children: [
              CircleAvatar(radius: 26, child: Icon(icon)),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text(description),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.icon,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: ListTile(
            contentPadding: EdgeInsets.zero,
            leading: CircleAvatar(child: Icon(icon)),
            title: Text(title),
            subtitle: Text(description),
          ),
        ),
      );
}

class _ComingSoonCard extends StatelessWidget {
  const _ComingSoonCard({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          leading: Icon(icon),
          title: Text(title),
          subtitle: const Text('Mobile screen coming in the next milestone'),
        ),
      );
}
