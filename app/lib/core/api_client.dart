import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'models.dart';

class ApiException implements Exception {
  ApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  bool get isUnauthorized => statusCode == 401;

  @override
  String toString() => message;
}

/// Typed client for the FastAPI backend.
class ApiClient {
  ApiClient({required this.baseUrl, this.token, http.Client? httpClient})
      : _http = httpClient ?? http.Client();

  final String baseUrl;
  final String? token;
  final http.Client _http;

  static const _timeout = Duration(seconds: 60);

  Uri _uri(String path) => Uri.parse('${baseUrl.replaceAll(RegExp(r'/+$'), '')}$path');

  /// ws:// URL for a path, carrying the token as a query parameter.
  Uri wsUri(String path) {
    final http = _uri(path);
    return http.replace(
      scheme: http.scheme == 'https' ? 'wss' : 'ws',
      queryParameters: {'token': ?token},
    );
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<dynamic> _send(String method, String path, [Object? body]) async {
    final request = http.Request(method, _uri(path))..headers.addAll(_headers);
    if (body != null) request.body = jsonEncode(body);
    final http.Response response;
    try {
      response = await http.Response.fromStream(await _http.send(request).timeout(_timeout));
    } on Exception catch (e) {
      throw ApiException(0, 'Cannot reach the server at $baseUrl ($e)');
    }
    return _decode(response);
  }

  dynamic _decode(http.Response response) {
    final text = utf8.decode(response.bodyBytes);
    final data = text.isEmpty ? null : jsonDecode(text);
    if (response.statusCode >= 200 && response.statusCode < 300) return data;
    throw ApiException(response.statusCode, _errorMessage(data, response.statusCode));
  }

  static String _errorMessage(dynamic data, int status) {
    final detail = data is Map ? data['detail'] : null;
    if (detail is String) return detail;
    if (detail is List && detail.isNotEmpty) {
      return detail.map((e) => e is Map ? e['msg'] ?? e.toString() : e.toString()).join('\n');
    }
    return 'Request failed ($status)';
  }

  // ---- auth ----

  Future<AuthSession> login(String email, String password) async =>
      AuthSession.fromJson(await _send('POST', '/auth/login', {'email': email, 'password': password}) as Json);

  Future<AuthSession> register(String username, String email, String password) async => AuthSession.fromJson(
      await _send('POST', '/auth/register', {'username': username, 'email': email, 'password': password}) as Json);

  Future<User> me() async => User.fromJson(await _send('GET', '/auth/me') as Json);

  /// Emails a reset code (the server answers the same way for unknown emails).
  Future<void> forgotPassword(String email) async => _send('POST', '/auth/forgot-password', {'email': email});

  Future<void> resetPassword(String token, String newPassword) async =>
      _send('POST', '/auth/reset-password', {'token': token, 'new_password': newPassword});

  // ---- setup ----

  Future<SetupStatus> startSetup() async => SetupStatus.fromJson(await _send('POST', '/setup/start') as Json);

  Future<void> cancelSetup() async => _send('DELETE', '/setup');

  Future<CalibrationResult> calibrate() async =>
      CalibrationResult.fromJson(await _send('POST', '/setup/calibrate') as Json);

  Future<VerifyResult> verifyPieces() async => VerifyResult.fromJson(await _send('POST', '/setup/verify') as Json);

  Future<SetupStatus> debugSkipSetup() async =>
      SetupStatus.fromJson(await _send('POST', '/setup/debug/skip') as Json);

  // ---- games ----

  Future<LiveGameState> startGame(GameOptions options) async =>
      LiveGameState.fromJson(await _send('POST', '/games', options.toJson()) as Json);

  Future<LiveGameState?> activeGame() async {
    try {
      return LiveGameState.fromJson(await _send('GET', '/games/active') as Json);
    } on ApiException catch (e) {
      if (e.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<List<GameSummary>> listGames() async =>
      [for (final g in await _send('GET', '/games') as List) GameSummary.fromJson(g as Json)];

  Future<GameDetail> getGame(int id) async => GameDetail.fromJson(await _send('GET', '/games/$id') as Json);

  Future<void> pressClock(int gameId) async => _send('POST', '/games/$gameId/press-clock');

  Future<void> resign(int gameId) async => _send('POST', '/games/$gameId/resign');

  Future<void> abort(int gameId) async => _send('POST', '/games/$gameId/abort');

  Future<void> manualDone(int gameId) async => _send('POST', '/games/$gameId/manual-done');

  // ---- camera (phone A) ----

  Future<bool> cameraConnected() async =>
      ((await _send('GET', '/camera/status') as Json)['connected'] ?? false) as bool;

  Future<void> uploadCapture(String requestId, Uint8List jpeg) async {
    final request = http.MultipartRequest('POST', _uri('/camera/upload/$requestId'))
      ..headers.addAll({if (token != null) 'Authorization': 'Bearer $token'})
      ..files.add(http.MultipartFile.fromBytes('file', jpeg, filename: 'board.jpg'));
    final response = await http.Response.fromStream(await _http.send(request).timeout(_timeout));
    _decode(response);
  }
}
