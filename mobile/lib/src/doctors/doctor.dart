class Doctor {
  const Doctor({
    required this.id,
    required this.name,
    required this.qualification,
    this.specialization,
    this.hospitalName,
    required this.experienceYears,
  });

  final String id;
  final String name;
  final String qualification;
  final String? specialization;
  final String? hospitalName;
  final int experienceYears;

  factory Doctor.fromJson(Map<String, dynamic> json) {
    final user = json['user'] as Map<String, dynamic>;
    return Doctor(
      id: json['id'] as String,
      name: user['full_name'] as String,
      qualification: json['qualification'] as String,
      specialization: json['specialization'] as String?,
      hospitalName: json['hospital_name'] as String?,
      experienceYears: json['experience_years'] as int,
    );
  }
}

