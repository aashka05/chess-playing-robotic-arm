import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../core/providers.dart';
import '../../core/ws_client.dart';

/// A one-off message for the user (e.g. "move not recognized").
class GameNotice {
  const GameNotice(this.id, this.title, this.message);

  final int id;
  final String title;
  final String message;
}

class GameView {
  const GameView({this.live, required this.receivedAt, this.connected = false, this.notice, this.error});

  /// Latest authoritative snapshot from the backend.
  final LiveGameState? live;

  /// When [live] arrived; running clocks are interpolated from here.
  final DateTime receivedAt;
  final bool connected;
  final GameNotice? notice;
  final String? error;

  GameView copyWith({LiveGameState? live, DateTime? receivedAt, bool? connected, GameNotice? notice, String? error}) =>
      GameView(
        live: live ?? this.live,
        receivedAt: receivedAt ?? this.receivedAt,
        connected: connected ?? this.connected,
        notice: notice ?? this.notice,
        error: error,
      );

  /// Remaining time for [color] right now.
  int clockMs(String color) {
    final clock = live?.clock;
    if (clock == null) return 0;
    final ms = clock.msFor(color);
    if (clock.running != color) return ms;
    return ms - DateTime.now().difference(receivedAt).inMilliseconds;
  }
}

/// Renders the backend's game state from /ws/games/{id}; sends intents over REST.
class GameController extends Notifier<GameView> {
  GameController(this.gameId);

  final int gameId;
  int _noticeCounter = 0;

  @override
  GameView build() {
    final api = ref.watch(apiClientProvider);
    final socket = ReconnectingSocket(
      api.wsUri('/ws/games/$gameId'),
      onConnectionChange: (c) {
        if (ref.mounted) state = state.copyWith(connected: c);
      },
    );
    final sub = socket.messages.listen(_onMessage);
    socket.connect();
    ref.onDispose(() {
      sub.cancel();
      socket.close();
    });
    return GameView(receivedAt: DateTime.now());
  }

  void _onMessage(Json m) {
    switch (m['type']) {
      case 'state':
        state = state.copyWith(live: LiveGameState.fromJson(m), receivedAt: DateTime.now());
      case 'eval':
        final live = state.live;
        if (live == null) return;
        final ply = m['ply'] as int;
        state = state.copyWith(live: live.withMoves([
          for (final mv in live.moves) mv.ply == ply ? mv.withEval(m['eval_cp'] as int?, m['eval_mate'] as int?) : mv,
        ]));
      case 'move_not_recognized':
        _notice('Move not recognized', [
          if ((m['message'] as String?)?.isNotEmpty ?? false) m['message'] as String,
          'Restore the position, make your move clearly and press your clock again.',
        ].join('\n\n'));
      case 'error':
        state = state.copyWith(error: m['message'] as String?);
    }
  }

  void _notice(String title, String message) =>
      state = state.copyWith(notice: GameNotice(++_noticeCounter, title, message));

  Future<void> pressClock() => ref.read(apiClientProvider).pressClock(gameId);

  Future<void> resign() => ref.read(apiClientProvider).resign(gameId);

  Future<void> abort() => ref.read(apiClientProvider).abort(gameId);

  Future<void> manualDone() => ref.read(apiClientProvider).manualDone(gameId);
}

final gameControllerProvider =
    NotifierProvider.autoDispose.family<GameController, GameView, int>(GameController.new);
