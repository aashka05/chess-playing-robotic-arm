import 'package:chess_robot/core/models.dart';
import 'package:chess_robot/features/home/home_screen.dart';
import 'package:chess_robot/shared/chess_board.dart';
import 'package:chess_robot/shared/eval.dart';
import 'package:chess_robot/shared/fen.dart';
import 'package:chess_robot/shared/format.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const startFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

MoveInfo move({int? cp, int? mate, String fen = startFen}) =>
    MoveInfo(ply: 1, san: 'e4', uci: 'e2e4', player: 'human', fenAfter: fen, timeTakenMs: 0, evalCp: cp, evalMate: mate);

void main() {
  test('parses FEN placement', () {
    final pieces = piecesFromFen(startFen);
    expect(pieces.length, 32);
    expect(pieces['e1'], 'K');
    expect(pieces['d8'], 'q');
    expect(pieces['e4'], isNull);
    expect(sideToMove('8/8/8/8/8/8/8/8 b - - 0 1'), 'black');
    expect(pieceName('n'), 'black knight');
    expect(pieceName(null), 'empty');
  });

  test('clock formatting', () {
    expect(formatClock(300000), '5:00');
    expect(formatClock(9500), '0:09.5');
    expect(formatClock(-5), '0:00.0');
    expect(formatClock(3723000), '1:02:03');
  });

  test('evaluation from White\'s view', () {
    expect(whiteEval(move(cp: 35)), 35);
    expect(whiteEval(move(cp: 5000)), evalClampCp);
    expect(whiteEval(move(mate: -3)), -evalClampCp);
    // mate 0: side to move (white here) is checkmated -> Black won.
    expect(whiteEval(move(mate: 0)), -evalClampCp);
    expect(whiteEval(move()), isNull);
    expect(evalLabel(move(cp: -120)), '-1.2');
    expect(evalLabel(move(mate: 2)), '+M2');
  });

  test('parses a live state snapshot', () {
    final s = LiveGameState.fromJson({
      'type': 'state', 'game_id': 3, 'state': 'HUMAN_TURN', 'fen': startFen, 'turn': 'white',
      'in_check': false, 'user_color': 'black', 'difficulty': 'easy',
      'clock': {'white_ms': 1000, 'black_ms': 2000, 'running': 'black', 'base_ms': 60000, 'increment_ms': 0},
      'moves': [
        {'ply': 1, 'san': 'e4', 'uci': 'e2e4', 'player': 'robot', 'fen_after': startFen, 'time_taken_ms': 5,
         'detection_confidence': null, 'eval_cp': 30, 'eval_mate': null, 'move_id': 9},
      ],
      'last_move': 'e2e4', 'message': 'Your move', 'manual_action': null, 'status': 'in_progress',
      'result': null, 'termination_reason': null, 'camera_connected': true,
    });
    expect(s.robotColor, 'white');
    expect(s.clock!.msFor('black'), 2000);
    expect(s.moves.single.evalCp, 30);
  });

  testWidgets('board renders pieces and highlights', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: SizedBox(width: 400, child: ChessBoard(fen: startFen, highlights: {'e2': Colors.red}))),
    ));
    // Each piece is drawn twice (outline + fill).
    expect(find.text('♚\uFE0E'), findsNWidgets(4));
    expect(find.text('♟\uFE0E'), findsNWidgets(32));
  });

  test('piece colours follow FEN case', () {
    for (final s in 'KQRBNP'.split('')) {
      expect(pieceGlyph(s).white, isTrue, reason: s);
      expect(pieceGlyph(s.toLowerCase()).white, isFalse, reason: s.toLowerCase());
      // Same glyph for both colours, always forced to text (not emoji) style.
      expect(pieceGlyph(s).glyph, pieceGlyph(s.toLowerCase()).glyph);
      expect(pieceGlyph(s).glyph, endsWith('\uFE0E'));
    }
    expect(pieceGlyph('P').glyph, '♟\uFE0E');
    expect(pieceName('P'), 'white pawn');
    expect(pieceName('p'), 'black pawn');
  });

  testWidgets('starting position: white pawns are drawn white, black pawns black', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: SizedBox(width: 400, child: ChessBoard(fen: startFen))),
    ));
    // The fill layer is the Text with a plain colour (the outline uses a foreground Paint).
    Iterable<Color?> fills(String glyph) => tester
        .widgetList<Text>(find.text(glyph))
        .where((t) => t.style?.foreground == null)
        .map((t) => t.style?.color);
    expect(fills('♟\uFE0E').where((c) => c == Colors.white).length, 8);
    expect(fills('♟\uFE0E').where((c) => c == Colors.black).length, 8);
    expect(fills('♚\uFE0E'), unorderedEquals([Colors.white, Colors.black]));
  });

  test('logout label depends on the role, not the username', () {
    User user(String name, String role) =>
        User.fromJson({'user_id': 1, 'username': name, 'email': 'a@b.c', 'role': role});
    expect(logoutLabel(user('alice', 'admin')), 'Log out admin');
    expect(logoutLabel(user('admin', 'client')), 'Log out');
    expect(logoutLabel(user('bob', 'client')), 'Log out');
    expect(logoutLabel(null), 'Log out');
  });
}
