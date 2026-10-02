import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/providers.dart';

const _sessionKey = 'auth_session';

/// The logged-in session (null = logged out), persisted across restarts.
class AuthController extends Notifier<AuthSession?> {
  @override
  AuthSession? build() {
    final raw = ref.read(sharedPrefsProvider).getString(_sessionKey);
    if (raw == null) return null;
    try {
      final j = jsonDecode(raw) as Json;
      return AuthSession(token: j['token'] as String, user: User.fromJson(j['user'] as Json));
    } catch (_) {
      return null;
    }
  }

  ApiClient get _anonymous => ApiClient(baseUrl: ref.read(baseUrlProvider));

  Future<void> login(String email, String password) async => _save(await _anonymous.login(email, password));

  Future<void> register(String username, String email, String password) async =>
      _save(await _anonymous.register(username, email, password));

  Future<void> logout() async {
    await ref.read(sharedPrefsProvider).remove(_sessionKey);
    state = null;
  }

  Future<void> _save(AuthSession session) async {
    await ref
        .read(sharedPrefsProvider)
        .setString(_sessionKey, jsonEncode({'token': session.token, 'user': session.user.toJson()}));
    state = session;
  }
}

final authProvider = NotifierProvider<AuthController, AuthSession?>(AuthController.new);
