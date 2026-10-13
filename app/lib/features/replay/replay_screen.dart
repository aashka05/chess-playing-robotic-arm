import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../shared/chess_board.dart';
import '../../shared/eval.dart';
import '../../shared/fen.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../history/history_providers.dart';

/// Move number and side of the move at [index] (0-based) in a game starting
/// from [initialFen]; a game may start with Black to move.
({int number, bool white}) moveNumber(String initialFen, int index) {
  final parts = initialFen.split(' ');
  final firstNumber = parts.length > 5 ? int.tryParse(parts[5]) ?? 1 : 1;
  final offset = index + (sideToMove(initialFen) == 'white' ? 0 : 1);
  return (number: firstNumber + offset ~/ 2, white: offset.isEven);
}

/// "1. e4 e5" rows of the move list. If Black moved first, row 1 has no White move.
List<({int number, MoveInfo? white, MoveInfo? black})> moveRows(String initialFen, List<MoveInfo> moves) {
  final rows = <({int number, MoveInfo? white, MoveInfo? black})>[];
  for (var i = 0; i < moves.length; i++) {
    final (:number, :white) = moveNumber(initialFen, i);
    if (white || rows.isEmpty) {
      rows.add((number: number, white: white ? moves[i] : null, black: white ? null : moves[i]));
    } else {
      rows.last = (number: rows.last.number, white: rows.last.white, black: moves[i]);
    }
  }
  return rows;
}

/// Step through a finished game. Positions are replayed server-side with python-chess.
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
  int _moveCount = 0;
  final _currentMoveKey = GlobalKey();

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
        child: CallbackShortcuts(
          bindings: {
            const SingleActivator(LogicalKeyboardKey.arrowLeft): () => _go(_ply - 1),
            const SingleActivator(LogicalKeyboardKey.arrowRight): () => _go(_ply + 1),
            const SingleActivator(LogicalKeyboardKey.home): () => _go(0),
            const SingleActivator(LogicalKeyboardKey.end): () => _go(_moveCount),
          },
          child: Focus(
            autofocus: true,
            child: detail.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => ErrorRetry(error: e, onRetry: () => ref.invalidate(gameDetailProvider(widget.gameId))),
              data: (game) {
                _moveCount = game.moves.length;
                if (!_started) {
                  _started = true;
                  _ply = game.moves.length; // open on the final position
                }
                return _content(game);
              },
            ),
          ),
        ),
      ),
    );
  }

  void _go(int ply) {
    final clamped = ply.clamp(0, _moveCount);
    if (clamped == _ply) return;
    setState(() => _ply = clamped);
    // Keep the highlighted move in view once it has been laid out.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final target = _currentMoveKey.currentContext;
      if (target != null && target.mounted) {
        Scrollable.ensureVisible(target, alignment: 0.5, duration: const Duration(milliseconds: 150));
      }
    });
  }

  Widget _content(GameDetail game) {
    final moves = game.moves;
    final current = _ply == 0 ? null : moves[_ply - 1];
    final fen = current?.fenAfter ?? game.initialFen;
    final flipped = game.summary.userColor == 'black';
    final s = game.summary;

    final header = Text(
      '${resultLabel(s.result, s.status)}'
      '${s.terminationReason != null && s.status != 'aborted' ? ' by ${terminationLabel(s.terminationReason)}' : ''}'
      ' · You played ${s.userColor} · ${capitalize(s.difficulty)} · ${s.timeControl}',
      style: Theme.of(context).textTheme.titleSmall,
    );
    // Eval bar + square board, [width] wide in total.
    const evalBarWidth = 18.0, gap = 6.0;
    Widget board(double width) => SizedBox(
          width: width,
          height: width - evalBarWidth - gap,
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            EvalBar(evalCp: current == null ? 0 : (whiteEval(current) ?? 0), flipped: flipped, width: evalBarWidth),
            const SizedBox(width: gap),
            Expanded(child: ChessBoard(fen: fen, flipped: flipped, lastMove: current?.uci)),
          ]),
        );
    String label(MoveInfo m) {
      final (:number, :white) = moveNumber(game.initialFen, m.ply - 1);
      return '$number${white ? '.' : '…'} ${m.san}  (${evalLabel(m)})';
    }

    final nav = Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
      IconButton(
          tooltip: 'First move', onPressed: _ply > 0 ? () => _go(0) : null, icon: const Icon(Icons.first_page)),
      IconButton.filledTonal(
          tooltip: 'Previous move',
          onPressed: _ply > 0 ? () => _go(_ply - 1) : null,
          icon: const Icon(Icons.chevron_left)),
      Flexible(child: Text(current == null ? 'Start' : label(current), textAlign: TextAlign.center)),
      IconButton.filledTonal(
          tooltip: 'Next move',
          onPressed: _ply < moves.length ? () => _go(_ply + 1) : null,
          icon: const Icon(Icons.chevron_right)),
      IconButton(
          tooltip: 'Last move',
          onPressed: _ply < moves.length ? () => _go(moves.length) : null,
          icon: const Icon(Icons.last_page)),
    ]);
    final movesPanel = ListView(padding: EdgeInsets.zero, children: [
      Text('Evaluation', style: Theme.of(context).textTheme.labelLarge),
      const SizedBox(height: 4),
      SizedBox(height: 90, child: EvalGraph(moves: moves, currentPly: _ply, onTapPly: _go)),
      const SizedBox(height: 12),
      Text('Moves', style: Theme.of(context).textTheme.labelLarge),
      const SizedBox(height: 4),
      _MoveList(
        rows: moveRows(game.initialFen, moves),
        currentPly: _ply,
        currentKey: _currentMoveKey,
        onTap: _go,
      ),
    ]);

    return LayoutBuilder(builder: (context, c) {
      const pad = 12.0;
      if (c.maxWidth >= 720) {
        // Desktop/tablet: board on the left, moves alongside.
        final boardWidth = min(c.maxHeight - 120, c.maxWidth * 0.6);
        return Padding(
          padding: const EdgeInsets.all(pad),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(
              width: boardWidth,
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                header,
                const SizedBox(height: 8),
                board(boardWidth),
                const SizedBox(height: 8),
                nav,
              ]),
            ),
            const SizedBox(width: 16),
            Expanded(child: movesPanel),
          ]),
        );
      }
      // Phone: stacked, the board stays put while the moves scroll.
      final boardWidth = min(c.maxWidth - 2 * pad, c.maxHeight * 0.6);
      return Padding(
        padding: const EdgeInsets.all(pad),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          header,
          const SizedBox(height: 8),
          Center(child: board(boardWidth)),
          const SizedBox(height: 4),
          nav,
          const SizedBox(height: 4),
          Expanded(child: movesPanel),
        ]),
      );
    });
  }
}

class _MoveList extends StatelessWidget {
  const _MoveList({required this.rows, required this.currentPly, required this.currentKey, required this.onTap});

  final List<({int number, MoveInfo? white, MoveInfo? black})> rows;
  final int currentPly;
  final GlobalKey currentKey;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    Widget cell(MoveInfo? m) {
      if (m == null) return const SizedBox();
      final selected = m.ply == currentPly;
      return InkWell(
        key: selected ? currentKey : null,
        onTap: () => onTap(m.ply),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
          decoration: BoxDecoration(
            color: selected ? scheme.primaryContainer : null,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Row(children: [
            Icon(m.player == 'robot' ? Icons.precision_manufacturing : Icons.person, size: 14),
            const SizedBox(width: 4),
            Text(m.san, style: TextStyle(fontWeight: selected ? FontWeight.bold : FontWeight.w600)),
            const Spacer(),
            Text(evalLabel(m), style: Theme.of(context).textTheme.bodySmall),
          ]),
        ),
      );
    }

    return Column(children: [
      for (final (i, row) in rows.indexed)
        Container(
          color: i.isOdd ? scheme.surfaceContainerHighest.withValues(alpha: 0.5) : null,
          child: Row(children: [
            SizedBox(width: 36, child: Text('${row.number}.', style: TextStyle(color: scheme.onSurfaceVariant))),
            Expanded(child: cell(row.white)),
            Expanded(child: cell(row.black)),
          ]),
        ),
    ]);
  }
}
