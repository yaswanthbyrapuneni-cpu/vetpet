import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import '../core/api_client.dart';
import 'pet.dart';

final petRepositoryProvider = Provider<PetRepository>(
  (ref) => PetRepository(ref.watch(apiClientProvider)),
);

final petsProvider = FutureProvider.autoDispose<List<Pet>>(
  (ref) => ref.watch(petRepositoryProvider).list(),
);

class PetRepository {
  PetRepository(this._api);

  final ApiClient _api;

  Future<List<Pet>> list() async {
    final response = await _api.get('/pets') as List<dynamic>;
    return response
        .map((item) => Pet.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Pet> get(String id) async {
    final response = await _api.get('/pets/$id') as Map<String, dynamic>;
    return Pet.fromJson(response);
  }

  Future<void> create(Map<String, dynamic> body) =>
      _api.post('/pets', body: body);

  Future<void> update(String id, Map<String, dynamic> body) =>
      _api.patch('/pets/$id', body: body);

  Future<void> archive(String id) => _api.delete('/pets/$id');
}

