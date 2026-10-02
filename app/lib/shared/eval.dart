import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/models.dart';
import 'fen.dart';

const evalClampCp = 1000;

/// Evaluation from White's view in centipawns, mate mapped to +-[evalClampCp].
/// eval_mate == 0 means the side to move in [fenAfter] has been checkmated.
double? whiteEval(MoveInfo m) {
  if (m.evalMate != null) {
    final mate = m.evalMate!;
    if (mate == 0) return sideToMove(m.fenAfter) == 'white' ? -evalClampCp.toDouble() : evalClampCp.toDouble();
    return mate > 0 ? evalClampCp.toDouble() : -evalClampCp.toDouble();
  }
  if (m.evalCp != null) return m.evalCp!.clamp(-evalClampCp, evalClampCp).toDouble();
  return null;
}

String evalLabel(MoveInfo? m) {
  if (m == null) return '0.0';
  if (m.evalMate != null) {
    if (m.evalMate == 0) return '#';
    return m.evalMate! > 0 ? '+M${m.evalMate}' : '-M${-m.evalMate!}';
  }
  if (m.evalCp == null) return '…';
  final pawns = m.evalCp! / 100;
  return '${pawns >= 0 ? '+' : ''}${pawns.toStringAsFixed(1)}';
}

/// Vertical bar: white share grows with White's advantage.
class EvalBar extends StatelessWidget {
  const EvalBar({super.key, required this.evalCp, this.flipped = false, this.width = 18});

  final double evalCp;
  final bool flipped;
  final double width;

  @override
  Widget build(BuildContext context) {
    // Logistic squash so +-4 pawns fills most of the bar.
    final whiteShare = 1 / (1 + math.exp(-evalCp / 250));
    return SizedBox(
      width: width,
      child: LayoutBuilder(builder: (context, c) {
        final whiteHeight = c.maxHeight * whiteShare;
        final white = Container(height: whiteHeight, color: Colors.grey.shade100);
        final black = Container(height: c.maxHeight - whiteHeight, color: Colors.grey.shade900);
        return ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: Column(children: flipped ? [white, black] : [black, white]),
        );
      }),
    );
  }
}

/// Line graph of the evaluation over the game, with the current ply marked.
class EvalGraph extends StatelessWidget {
  const EvalGraph({super.key, required this.moves, required this.currentPly, this.onTapPly});

  final List<MoveInfo> moves;
  final int currentPly;
  final ValueChanged<int>? onTapPly;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      return GestureDetector(
        onTapDown: moves.isEmpty || onTapPly == null
            ? null
            : (d) => onTapPly!(((d.localPosition.dx / c.maxWidth) * moves.length).ceil().clamp(0, moves.length)),
        child: CustomPaint(
          size: Size(c.maxWidth, c.maxHeight),
          painter: _EvalPainter(moves, currentPly, Theme.of(context).colorScheme.primary),
        ),
      );
    });
  }
}

class _EvalPainter extends CustomPainter {
  _EvalPainter(this.moves, this.currentPly, this.accent);

  final List<MoveInfo> moves;
  final int currentPly;
  final Color accent;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = Colors.grey.shade800);
    final mid = size.height / 2;
    canvas.drawLine(Offset(0, mid), Offset(size.width, mid), Paint()..color = Colors.grey.shade500);
    if (moves.isEmpty) return;

    double y(double cp) => mid - (cp / evalClampCp) * mid;
    double x(int ply) => size.width * ply / moves.length;

    final path = Path()..moveTo(0, mid);
    final area = Path()..moveTo(0, size.height)..lineTo(0, mid);
    var last = 0.0;
    for (final m in moves) {
      last = whiteEval(m) ?? last;
      path.lineTo(x(m.ply), y(last));
      area.lineTo(x(m.ply), y(last));
    }
    area..lineTo(x(moves.length), size.height)..close();
    canvas.drawPath(area, Paint()..color = Colors.grey.shade100);
    canvas.drawPath(
      path,
      Paint()
        ..color = accent
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
    final cx = x(currentPly);
    canvas.drawLine(Offset(cx, 0), Offset(cx, size.height), Paint()..color = accent..strokeWidth = 2);
  }

  @override
  bool shouldRepaint(_EvalPainter old) => old.moves != moves || old.currentPly != currentPly;
}
