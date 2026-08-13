class Pet {
  const Pet({
    required this.id,
    required this.name,
    required this.species,
    this.breed,
    this.sex,
    this.dateOfBirth,
    this.weightKg,
  });

  final String id;
  final String name;
  final String species;
  final String? breed;
  final String? sex;
  final DateTime? dateOfBirth;
  final double? weightKg;

  factory Pet.fromJson(Map<String, dynamic> json) => Pet(
        id: json['id'] as String,
        name: json['name'] as String,
        species: json['species'] as String,
        breed: json['breed'] as String?,
        sex: json['sex'] as String?,
        dateOfBirth: json['date_of_birth'] == null
            ? null
            : DateTime.parse(json['date_of_birth'] as String),
        weightKg: (json['weight_kg'] as num?)?.toDouble(),
      );
}

