// ignore_for_file: avoid_print
// End-to-end smoke test of the app's API/WebSocket layer against a running
// backend started with DEBUG_ENDPOINTS=true and ARM_MODE=mock:
//   dart run tool/api_smoke.dart http://localhost:8000
import 'dart:async';

import 'package:chess_robot/core/api_client.dart';
import 'package:chess_robot/core/models.dart';
import 'package:chess_robot/core/ws_client.dart';
import 'package:http/http.dart' as http;

Future<void> main(List<String> args) async {
  final base = args.isEmpty ? 'http://localhost:8000' : args.first;
  final email = 'smoke${DateTime.now().millisecondsSinceEpoch}@example.com';
  final session = await ApiClient(baseUrl: base).register('smoke', email, 'secret1');
  final api = ApiClient(baseUrl: base, token: session.token);
  print('logged in as ${session.user.username} (${session.user.role})');

  print('setup: ${(await api.startSetup()).state}');
  try {
    await api.calibrate();
  } on ApiException catch (e) {
    print('calibrate without camera -> ${e.statusCode}: ${e.message}');
  }
  await api.debugSkipSetup();
  final game = await api.startGame(
      const GameOptions(color: 'white', difficulty: 'medium', timeBaseSec: 180, timeIncrementSec: 1));
  print('game ${game.gameId}: ${game.state}, clock ${game.clock!.whiteMs}ms');

  final socket = ReconnectingSocket(api.wsUri('/ws/games/${game.gameId}'))..connect();
  final states = StreamController<LiveGameState>.broadcast();
  var evals = 0;
  socket.messages.listen((m) {
    if (m['type'] == 'state') states.add(LiveGameState.fromJson(m));
    if (m['type'] == 'eval') evals++;
  });
  Future<LiveGameState> until(bool Function(LiveGameState) f) => states.stream.firstWhere(f);

  // Italian opening, played through the dev endpoint (bypasses the camera).
  for (final uci in ['e2e4', 'g1f3', 'f1c4']) {
    final waiting = until((s) => s.state == GamePhase.humanTurn && s.moves.length.isOdd == false && s.moves.isNotEmpty);
    final r = await http.post(Uri.parse('$base/games/${game.gameId}/debug/human-move'),
        headers: {'Authorization': 'Bearer ${session.token}', 'Content-Type': 'application/json'},
        body: '{"uci":"$uci"}');
    if (r.statusCode != 202) throw 'debug move failed: ${r.body}';
    final s = await waiting;
    print('  you ${s.moves[s.moves.length - 2].san}, robot ${s.moves.last.san}; '
        'white ${s.clock!.whiteMs}ms black ${s.clock!.blackMs}ms');
  }

  await api.resign(game.gameId);
  final over = await until((s) => s.isOver);
  print('game over: ${over.result} by ${over.terminationReason}');
  await socket.close();

  await Future<void>.delayed(const Duration(seconds: 1));
  final detail = await api.getGame(game.gameId);
  print('history: ${(await api.listGames()).length} game(s); replay has ${detail.moves.length} moves, '
      'evals ${detail.moves.map((m) => m.evalCp ?? 'M${m.evalMate}').join(', ')}; live eval events: $evals');
  print('PGN:\n${detail.pgn}');
}
