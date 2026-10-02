import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../shared/chess_board.dart';
import '../../shared/eval.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../history/history_providers.dart';

/// Step through a finished game using the stored fen_after of every move.
class ReplayScreen extends ConsumerStatefulWidget {
  const ReplayScreen({super.key, required this.gameId});

  final int gameId;

  @override
  ConsumerState<ReplayScreen> createState() => _ReplayScreenState();
}

class _ReplayScreenState extends ConsumerState<ReplayScreen> {
  /// 0 = initial position, n = after move n.
  int _ply = 0;
  bool _started = false;

  @override
  Widget build(BuildContext context) {
    final detail = ref.watch(gameDetailProvider(widget.gameId));
    return Scaffold(
      appBar: AppBar(
        title: Text('Replay #${widget.gameId}'),
        actions: [
          if (detail.value?.pgn != null)
            IconButton(
              tooltip: 'Copy PGN',
              icon: const Icon(Icons.copy),
              onPressed: () {
                Clipboard.setData(ClipboardData(text: detail.value!.pgn!));
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('PGN copied')));
              },
            ),
        ],
      ),
      body: SafeArea(
        child: detail.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ErrorRetry(error: e, onRetry: () => ref.invalidate(gameDetailProvider(widget.gameId))),
          data: (game) {
            if (!_started) {
              _started = true;
              _ply = game.moves.length; // open on the final position
            }
            return _content(game);
          },
        ),
      ),
    );
  }

  void _go(int ply, int max) => setState(() => _ply = ply.clamp(0, max));

  Widget _content(GameDetail game) {
    final moves = game.moves;
    final current = _ply == 0 ? null : moves[_ply - 1];
    final fen = current?.fenAfter ?? game.initialFen;
    final flipped = game.summary.userColor == 'black';
    final s = game.summary;

    return ListView(padding: const EdgeInsets.all(12), children: [
      Text(
        '${resultLabel(s.result, s.status)}'
        '${s.terminationReason != null && s.status != 'aborted' ? ' by ${terminationLabel(s.terminationReason)}' : ''}'
        ' · You played ${s.userColor} · ${capitalize(s.difficulty)} · ${s.timeControl}',
        style: Theme.of(context).textTheme.titleSmall,
      ),
      const SizedBox(height: 8),
      IntrinsicHeight(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          EvalBar(evalCp: current == null ? 0 : (whiteEval(current) ?? 0), flipped: flipped),
          const SizedBox(width: 6),
          Expanded(child: ChessBoard(fen: fen, flipped: flipped, lastMove: current?.uci)),
        ]),
      ),
      const SizedBox(height: 8),
      Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
        IconButton(onPressed: _ply > 0 ? () => _go(0, moves.length) : null, icon: const Icon(Icons.first_page)),
        IconButton.filledTonal(
            onPressed: _ply > 0 ? () => _go(_ply - 1, moves.length) : null, icon: const Icon(Icons.chevron_left)),
        Text(current == null ? 'Start' : '${(current.ply + 1) ~/ 2}${current.ply.isOdd ? '.' : '…'} ${current.san}  (${evalLabel(current)})'),
        IconButton.filledTonal(
            onPressed: _ply < moves.length ? () => _go(_ply + 1, moves.length) : null,
            icon: const Icon(Icons.chevron_right)),
        IconButton(
            onPressed: _ply < moves.length ? () => _go(moves.length, moves.length) : null,
            icon: const Icon(Icons.last_page)),
      ]),
      const SizedBox(height: 8),
      Text('Evaluation', style: Theme.of(context).textTheme.labelLarge),
      const SizedBox(height: 4),
      SizedBox(
        height: 90,
        child: EvalGraph(moves: moves, currentPly: _ply, onTapPly: (p) => _go(p, moves.length)),
      ),
      const SizedBox(height: 12),
      Text('Moves', style: Theme.of(context).textTheme.labelLarge),
      const SizedBox(height: 4),
      _MoveList(moves: moves, currentPly: _ply, onTap: (p) => _go(p, moves.length)),
    ]);
  }
}

class _MoveList extends StatelessWidget {
  const _MoveList({required this.moves, required this.currentPly, required this.onTap});

  final List<MoveInfo> moves;
  final int currentPly;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    Widget cell(MoveInfo m) => InkWell(
          onTap: () => onTap(m.ply),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            color: m.ply == currentPly ? scheme.primaryContainer : null,
            child: Row(children: [
              Icon(m.player == 'robot' ? Icons.precision_manufacturing : Icons.person, size: 14),
              const SizedBox(width: 4),
              Text(m.san, style: const TextStyle(fontWeight: FontWeight.w600)),
              const Spacer(),
              Text(evalLabel(m), style: Theme.of(context).textTheme.bodySmall),
            ]),
          ),
        );

    // The first move may be Black's if the game started from a custom FEN; pair by ply parity.
    final rows = <Widget>[];
    for (var i = 0; i < moves.length; i += 2) {
      rows.add(Row(children: [
        SizedBox(width: 32, child: Text('${i ~/ 2 + 1}.')),
        Expanded(child: cell(moves[i])),
        Expanded(child: i + 1 < moves.length ? cell(moves[i + 1]) : const SizedBox()),
      ]));
    }
    return Column(children: rows);
  }
}
