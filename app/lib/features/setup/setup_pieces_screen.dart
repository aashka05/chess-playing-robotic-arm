import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../core/providers.dart';
import '../../shared/chess_board.dart';
import '../../shared/fen.dart';
import '../../shared/widgets.dart';
import 'game_options_screen.dart';
import 'setup_step.dart';

const _startFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

/// Setup 2: set up the pieces; loop until the camera sees the correct position.
class SetupPiecesScreen extends ConsumerStatefulWidget {
  const SetupPiecesScreen({super.key});

  @override
  ConsumerState<SetupPiecesScreen> createState() => _SetupPiecesScreenState();
}

class _SetupPiecesScreenState extends ConsumerState<SetupPiecesScreen> {
  bool _busy = false;
  VerifyResult? _last;

  Future<void> _verify() async {
    setState(() => _busy = true);
    try {
      final result = await ref.read(apiClientProvider).verifyPieces();
      setState(() => _last = result);
      if (result.correct && mounted) {
        final gameId = await Navigator.push<int>(context, MaterialPageRoute(builder: (_) => const GameOptionsScreen()));
        if (gameId != null && mounted) Navigator.pop(context, gameId);
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final wrong = _last != null && !_last!.correct;
    return SetupStep(
      step: 2,
      title: wrong ? 'Some pieces are wrong' : 'Set up the pieces',
      instructions: wrong
          ? 'Fix the squares highlighted in red so the board matches the position below, then press OK.'
          : 'Set up the pieces in the starting position, then press OK.',
      busy: _busy,
      onOk: _verify,
      okLabel: wrong ? 'OK, check again' : 'OK',
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        ChessBoard(
          fen: _last?.expectedFen ?? _startFen,
          highlights: {
            for (final m in _last?.mismatches ?? const <Mismatch>[]) m.square: const Color(0x99E53935),
          },
        ),
        if (wrong) ...[
          const SizedBox(height: 12),
          for (final m in _last!.mismatches)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Text('${m.square}: should be ${pieceName(m.expected)}, camera sees ${pieceName(m.detected)}'),
            ),
        ],
      ]),
    );
  }
}
