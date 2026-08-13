import 'package:flutter_test/flutter_test.dart';
import 'package:vetpet_connect/src/auth/auth_models.dart';
import 'package:vetpet_connect/src/doctors/doctor.dart';
import 'package:vetpet_connect/src/pets/pet.dart';

void main() {
  test('parses authenticated owner', () {
    final user = AuthUser.fromJson({
      'id': 'user-1',
      'email': 'owner@example.com',
      'full_name': 'Pet Owner',
      'role': 'owner',
    });
    expect(user.role, UserRole.owner);
    expect(user.fullName, 'Pet Owner');
  });

  test('parses pet numeric weight', () {
    final pet = Pet.fromJson({
      'id': 'pet-1',
      'name': 'Milo',
      'species': 'Dog',
      'weight_kg': 18,
      'breed': null,
      'sex': null,
      'date_of_birth': '2022-04-10',
    });
    expect(pet.weightKg, 18.0);
    expect(pet.dateOfBirth, DateTime(2022, 4, 10));
  });

  test('parses verified doctor response', () {
    final doctor = Doctor.fromJson({
      'id': 'doctor-1',
      'user': {'full_name': 'Dr Vet'},
      'qualification': 'BVSc',
      'specialization': 'Small animals',
      'hospital_name': null,
      'experience_years': 5,
    });
    expect(doctor.name, 'Dr Vet');
    expect(doctor.experienceYears, 5);
  });
}
