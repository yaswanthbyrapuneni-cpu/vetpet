import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import '../core/api_client.dart';
import 'doctor.dart';

final doctorRepositoryProvider = Provider<DoctorRepository>(
  (ref) => DoctorRepository(ref.watch(apiClientProvider)),
);

final doctorsProvider = FutureProvider.autoDispose<List<Doctor>>(
  (ref) => ref.watch(doctorRepositoryProvider).listVerified(),
);

class DoctorRepository {
  DoctorRepository(this._api);
  final ApiClient _api;

  Future<List<Doctor>> listVerified() async {
    final response = await _api.get('/doctors') as List<dynamic>;
    return response
        .map((item) => Doctor.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}

