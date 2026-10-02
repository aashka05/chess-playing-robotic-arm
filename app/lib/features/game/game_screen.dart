import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../shared/chess_board.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../replay/replay_screen.dart';
import 'game_controller.dart';

/// The chess clock screen. Everything shown comes from the backend's state.
class GameScreen extends ConsumerStatefulWidget {
  const GameScreen({super.key, required this.gameId});

  final int gameId;

  @override
  ConsumerState<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends ConsumerState<GameScreen> {
  Timer? _ticker;
  bool _pressing = false;

  @override
  void initState() {
    super.initState();
    // Repaint the running clock between server updates.
    _ticker = Timer.periodic(const Duration(milliseconds: 100), (_) => setState(() {}));
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  GameController get _controller => ref.read(gameControllerProvider(widget.gameId).notifier);

  Future<void> _run(Future<void> Function() action) async {
    try {
      await action();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _pressClock() async {
    if (_pressing) return;
    setState(() => _pressing = true);
    await _run(_controller.pressClock);
    if (mounted) setState(() => _pressing = false);
  }

  Future<void> _confirm(String title, String message, String action, Future<void> Function() onYes) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(action)),
        ],
      ),
    );
    if (ok == true) await _run(onYes);
  }

  @override
  Widget build(BuildContext context) {
    final view = ref.watch(gameControllerProvider(widget.gameId));
    ref.listen(gameControllerProvider(widget.gameId).select((v) => v.notice), (_, notice) {
      if (notice == null) return;
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          icon: const Icon(Icons.help_outline, size: 40),
          title: Text(notice.title),
          content: Text(notice.message),
          actions: [FilledButton(onPressed: () => Navigator.pop(context), child: const Text('OK'))],
        ),
      );
    });

    final live = view.live;
    return Scaffold(
      appBar: AppBar(
        title: Text(live == null ? 'Game' : 'Game #${live.gameId} · ${capitalize(live.difficulty)}'),
        actions: [
          if (live != null && !live.isOver) ...[
            TextButton.icon(
              icon: const Icon(Icons.flag),
              label: const Text('Resign'),
              onPressed: () => _confirm('Resign?', 'The game will be recorded as a loss.', 'Resign', _controller.resign),
            ),
            PopupMenuButton<String>(
              onSelected: (_) => _confirm('Abort game?', 'The game will be stopped without a result.', 'Abort',
                  _controller.abort),
              itemBuilder: (_) => const [PopupMenuItem(value: 'abort', child: Text('Abort game'))],
            ),
          ],
        ],
      ),
      body: SafeArea(
        child: live == null
            ? Center(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const CircularProgressIndicator(),
                  const SizedBox(height: 12),
                  Text(view.error ?? 'Connecting…'),
                ]),
              )
            : _body(view, live),
      ),
    );
  }

  Widget _body(GameView view, LiveGameState live) {
    final humanTurn = live.state == GamePhase.humanTurn;
    return Column(children: [
      if (!view.connected)
        Container(
          width: double.infinity,
          color: Colors.orange.shade800,
          padding: const EdgeInsets.all(4),
          child: const Text('Reconnecting to the backend…', textAlign: TextAlign.center),
        ),
      _ClockPanel(
        label: 'Robot (${live.robotColor})',
        ms: view.clockMs(live.robotColor),
        running: live.clock?.running == live.robotColor,
        status: _robotStatus(live),
        compact: true,
      ),
      Expanded(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Column(children: [
            Expanded(
              child: Center(
                child: ChessBoard(fen: live.fen, flipped: live.userColor == 'black', lastMove: live.lastMove),
              ),
            ),
            const SizedBox(height: 8),
            if (live.manualAction != null)
              _ManualActionCard(action: live.manualAction!, onDone: () => _run(_controller.manualDone))
            else if (live.isOver)
              _GameOverCard(live: live, onReplay: () {
                Navigator.pushReplacement(
                    context, MaterialPageRoute(builder: (_) => ReplayScreen(gameId: live.gameId)));
              })
            else
              Text(live.message ?? '', textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleMedium),
            if (!live.cameraConnected && !live.isOver)
              const Padding(padding: EdgeInsets.only(top: 4), child: CameraStatusChip(connected: false)),
          ]),
        ),
      ),
      _ClockPanel(
        label: 'You (${live.userColor})',
        ms: view.clockMs(live.userColor),
        running: live.clock?.running == live.userColor,
        status: humanTurn ? 'Tap here after your move' : null,
        onTap: humanTurn && !_pressing ? _pressClock : null,
        busy: _pressing || live.state == GamePhase.detecting,
      ),
    ]);
  }

  String? _robotStatus(LiveGameState live) => switch (live.state) {
        GamePhase.detecting => 'Checking your move…',
        GamePhase.engineThinking => 'Thinking…',
        GamePhase.armExecuting => live.manualAction == null ? 'Arm moving: ${live.moves.lastOrNull?.san ?? ''}' : 'Waiting for you',
        _ => null,
      };
}

class _ClockPanel extends StatelessWidget {
  const _ClockPanel({
    required this.label,
    required this.ms,
    required this.running,
    this.status,
    this.onTap,
    this.busy = false,
    this.compact = false,
  });

  final String label;
  final int ms;
  final bool running;
  final String? status;
  final VoidCallback? onTap;
  final bool busy;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final low = ms < 20000;
    final bg = running ? (low ? Colors.red.shade700 : Colors.green.shade700) : Colors.grey.shade800;
    return Material(
      color: bg,
      child: InkWell(
        onTap: onTap,
        child: Container(
          width: double.infinity,
          padding: EdgeInsets.symmetric(vertical: compact ? 10 : 22, horizontal: 16),
          child: Column(children: [
            Text(label, style: const TextStyle(color: Colors.white70)),
            Text(
              formatClock(ms),
              style: TextStyle(
                color: Colors.white,
                fontSize: compact ? 40 : 64,
                fontWeight: FontWeight.bold,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
            if (busy)
              const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            else if (status != null)
              Text(status!, style: const TextStyle(color: Colors.white)),
          ]),
        ),
      ),
    );
  }
}

class _ManualActionCard extends StatelessWidget {
  const _ManualActionCard({required this.action, required this.onDone});

  final ManualAction action;
  final VoidCallback onDone;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.amber.shade100,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(children: [
          Row(children: [
            Icon(action.kind == 'arm_error' ? Icons.warning_amber : Icons.pan_tool, color: Colors.brown),
            const SizedBox(width: 8),
            Expanded(child: Text(action.message, style: const TextStyle(color: Colors.black))),
          ]),
          const SizedBox(height: 8),
          FilledButton(onPressed: onDone, child: const Text('Done, OK')),
          const Text('Clocks are paused.', style: TextStyle(color: Colors.black54, fontSize: 12)),
        ]),
      ),
    );
  }
}

class _GameOverCard extends StatelessWidget {
  const _GameOverCard({required this.live, required this.onReplay});

  final LiveGameState live;
  final VoidCallback onReplay;

  @override
  Widget build(BuildContext context) {
    final title = switch (live.result) {
      'win' => 'You won!',
      'loss' => 'You lost',
      'draw' => 'Draw',
      _ => 'Game aborted',
    };
    return Column(children: [
      Text(title, style: Theme.of(context).textTheme.headlineSmall),
      if (live.message != null) Text(live.message!),
      const SizedBox(height: 8),
      Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        OutlinedButton(onPressed: () => Navigator.pop(context), child: const Text('Home')),
        const SizedBox(width: 12),
        FilledButton(onPressed: onReplay, child: const Text('Replay')),
      ]),
    ]);
  }
}
