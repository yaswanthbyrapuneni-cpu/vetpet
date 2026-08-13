class AppConfig {
  const AppConfig._();

  static const apiBaseUrl = String.fromEnvironment(
    'VETPET_API_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );
}

