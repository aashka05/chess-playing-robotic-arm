import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../features/auth/auth_controller.dart';
import 'api_client.dart';

/// Overridden in main() with the loaded instance.
final sharedPrefsProvider = Provider<SharedPreferences>((ref) => throw UnimplementedError());

const _baseUrlKey = 'base_url';
// Override at build time: flutter run --dart-define=BASE_URL=http://localhost:8000
const defaultBaseUrl = String.fromEnvironment('BASE_URL', defaultValue: 'http://192.168.1.10:8000');

class BaseUrlNotifier extends Notifier<String> {
  @override
  String build() => ref.read(sharedPrefsProvider).getString(_baseUrlKey) ?? defaultBaseUrl;

  Future<void> set(String url) async {
    final clean = url.trim().replaceAll(RegExp(r'/+$'), '');
    await ref.read(sharedPrefsProvider).setString(_baseUrlKey, clean);
    state = clean;
  }
}

final baseUrlProvider = NotifierProvider<BaseUrlNotifier, String>(BaseUrlNotifier.new);

final apiClientProvider = Provider<ApiClient>((ref) {
  final token = ref.watch(authProvider.select((s) => s?.token));
  return ApiClient(baseUrl: ref.watch(baseUrlProvider), token: token);
});
