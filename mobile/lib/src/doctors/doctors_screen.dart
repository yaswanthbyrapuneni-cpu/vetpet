import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import 'doctor_repository.dart';

class DoctorsScreen extends ConsumerWidget {
  const DoctorsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final doctors = ref.watch(doctorsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Verified veterinarians')),
      body: doctors.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  error is ApiException ? error.message : 'Unable to load veterinarians.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: () => ref.invalidate(doctorsProvider),
                  child: const Text('Try again'),
                ),
              ],
            ),
          ),
        ),
        data: (items) => items.isEmpty
            ? const Center(child: Text('No verified veterinarians are available yet.'))
            : RefreshIndicator(
                onRefresh: () => ref.refresh(doctorsProvider.future),
                child: ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, index) {
                    final doctor = items[index];
                    return Card(
                      child: ListTile(
                        contentPadding: const EdgeInsets.all(16),
                        leading: const CircleAvatar(
                          child: Icon(Icons.medical_services_outlined),
                        ),
                        title: Text(doctor.name),
                        subtitle: Text([
                          doctor.qualification,
                          if (doctor.specialization != null) doctor.specialization!,
                          '${doctor.experienceYears} years experience',
                          if (doctor.hospitalName != null) doctor.hospitalName!,
                        ].join('\n')),
                        isThreeLine: true,
                      ),
                    );
                  },
                ),
              ),
      ),
    );
  }
}

