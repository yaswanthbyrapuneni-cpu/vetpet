import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/api_client.dart';
import 'pet.dart';
import 'pet_repository.dart';

class PetsScreen extends ConsumerWidget {
  const PetsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pets = ref.watch(petsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('My pets')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await context.push('/pets/new');
          ref.invalidate(petsProvider);
        },
        icon: const Icon(Icons.add),
        label: const Text('Add pet'),
      ),
      body: pets.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => _ErrorView(
          message: error is ApiException ? error.message : 'Unable to load pets.',
          onRetry: () => ref.invalidate(petsProvider),
        ),
        data: (items) => items.isEmpty
            ? const _EmptyPets()
            : RefreshIndicator(
                onRefresh: () => ref.refresh(petsProvider.future),
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, index) => _PetCard(
                    pet: items[index],
                    onEdit: () async {
                      await context.push('/pets/${items[index].id}/edit');
                      ref.invalidate(petsProvider);
                    },
                    onArchive: () => _archive(context, ref, items[index]),
                  ),
                ),
              ),
      ),
    );
  }

  Future<void> _archive(BuildContext context, WidgetRef ref, Pet pet) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Archive ${pet.name}?'),
        content: const Text('The profile will be hidden, but medical history will be preserved.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Archive')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await ref.read(petRepositoryProvider).archive(pet.id);
      ref.invalidate(petsProvider);
    } on ApiException catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }
}

class _PetCard extends StatelessWidget {
  const _PetCard({required this.pet, required this.onEdit, required this.onArchive});

  final Pet pet;
  final VoidCallback onEdit;
  final VoidCallback onArchive;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          contentPadding: const EdgeInsets.all(14),
          leading: const CircleAvatar(child: Icon(Icons.pets_rounded)),
          title: Text(pet.name),
          subtitle: Text([
            pet.species,
            if (pet.breed?.isNotEmpty == true) pet.breed!,
            if (pet.weightKg != null) '${pet.weightKg} kg',
          ].join(' • ')),
          trailing: PopupMenuButton<String>(
            onSelected: (value) => value == 'edit' ? onEdit() : onArchive(),
            itemBuilder: (context) => const [
              PopupMenuItem(value: 'edit', child: Text('Edit')),
              PopupMenuItem(value: 'archive', child: Text('Archive')),
            ],
          ),
        ),
      );
}

class _EmptyPets extends StatelessWidget {
  const _EmptyPets();

  @override
  Widget build(BuildContext context) => const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.pets_outlined, size: 64),
              SizedBox(height: 16),
              Text('No pets yet'),
              Text('Add your first pet to begin managing their care.'),
            ],
          ),
        ),
      );
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              OutlinedButton(onPressed: onRetry, child: const Text('Try again')),
            ],
          ),
        ),
      );
}

