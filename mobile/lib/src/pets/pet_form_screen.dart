import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../core/api_client.dart';
import 'pet.dart';
import 'pet_repository.dart';

class PetFormScreen extends ConsumerStatefulWidget {
  const PetFormScreen({super.key, this.petId});

  final String? petId;

  @override
  ConsumerState<PetFormScreen> createState() => _PetFormScreenState();
}

class _PetFormScreenState extends ConsumerState<PetFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _species = TextEditingController();
  final _breed = TextEditingController();
  final _weight = TextEditingController();
  String? _sex;
  DateTime? _birthDate;
  bool _loading = false;
  bool _saving = false;
  String? _error;

  bool get _editing => widget.petId != null;

  @override
  void initState() {
    super.initState();
    if (_editing) _loadPet();
  }

  Future<void> _loadPet() async {
    setState(() => _loading = true);
    try {
      final pet = await ref.read(petRepositoryProvider).get(widget.petId!);
      _populate(pet);
    } on ApiException catch (error) {
      _error = error.message;
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _populate(Pet pet) {
    _name.text = pet.name;
    _species.text = pet.species;
    _breed.text = pet.breed ?? '';
    _weight.text = pet.weightKg?.toString() ?? '';
    _sex = pet.sex;
    _birthDate = pet.dateOfBirth;
  }

  @override
  void dispose() {
    _name.dispose();
    _species.dispose();
    _breed.dispose();
    _weight.dispose();
    super.dispose();
  }

  Future<void> _pickBirthDate() async {
    final selected = await showDatePicker(
      context: context,
      firstDate: DateTime(1990),
      lastDate: DateTime.now(),
      initialDate: _birthDate ?? DateTime.now(),
    );
    if (selected != null) setState(() => _birthDate = selected);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    final body = <String, dynamic>{
      'name': _name.text.trim(),
      'species': _species.text.trim(),
      'breed': _breed.text.trim().isEmpty ? null : _breed.text.trim(),
      'sex': _sex,
      'date_of_birth': _birthDate == null ? null : DateFormat('yyyy-MM-dd').format(_birthDate!),
      'weight_kg': _weight.text.trim().isEmpty ? null : double.parse(_weight.text.trim()),
    };
    try {
      final repository = ref.read(petRepositoryProvider);
      if (_editing) {
        await repository.update(widget.petId!, body);
      } else {
        await repository.create(body);
      }
      ref.invalidate(petsProvider);
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  String? _required(String? value) =>
      value == null || value.trim().isEmpty ? 'This field is required' : null;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_editing ? 'Edit pet' : 'Add pet')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextFormField(
                        controller: _name,
                        decoration: const InputDecoration(labelText: 'Pet name'),
                        validator: _required,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _species,
                        decoration: const InputDecoration(labelText: 'Species'),
                        validator: _required,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _breed,
                        decoration: const InputDecoration(labelText: 'Breed (optional)'),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<String>(
                        initialValue: _sex,
                        decoration: const InputDecoration(labelText: 'Sex (optional)'),
                        items: const [
                          DropdownMenuItem(value: 'male', child: Text('Male')),
                          DropdownMenuItem(value: 'female', child: Text('Female')),
                          DropdownMenuItem(value: 'unknown', child: Text('Unknown')),
                        ],
                        onChanged: (value) => setState(() => _sex = value),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _weight,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(labelText: 'Weight in kg (optional)'),
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) return null;
                          final weight = double.tryParse(value);
                          return weight == null || weight <= 0 ? 'Enter a valid weight' : null;
                        },
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        onPressed: _pickBirthDate,
                        icon: const Icon(Icons.cake_outlined),
                        label: Text(
                          _birthDate == null
                              ? 'Choose date of birth'
                              : DateFormat.yMMMd().format(_birthDate!),
                        ),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 12),
                        Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                      ],
                      const SizedBox(height: 24),
                      FilledButton(
                        onPressed: _saving ? null : _save,
                        child: _saving
                            ? const CircularProgressIndicator()
                            : Text(_editing ? 'Save changes' : 'Add pet'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}

