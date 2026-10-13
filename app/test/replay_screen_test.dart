import 'package:chess_robot/core/models.dart';
import 'package:chess_robot/features/history/history_providers.dart';
import 'package:chess_robot/features/replay/replay_screen.dart';
import 'package:chess_robot/shared/chess_board.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const startFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const afterE4 = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';
const afterE5 = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2';
const afterNf3 = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2';

Map<String, Object?> mv(int ply, String san, String uci, String fen) => {
      'move_id': ply, 'move_number': ply, 'move': san, 'uci': uci, 'fen_after': fen,
      'player': ply.isOdd ? 'human' : 'robot', 'time_taken_ms': 0,
      'eval_cp': null, 'eval_mate': null, 'detection_confidence': null,
    };

GameDetail game({String initialFen = startFen, List<Map<String, Object?>>? moves}) => GameDetail.fromJson({
      'game_id': 7, 'user_id': 1, 'start_time': '2026-01-01T10:00:00', 'end_time': null,
      'difficulty': 'easy', 'result': 'win', 'status': 'finished', 'termination_reason': 'resignation',
      'user_color': 'white', 'time_base_sec': 600, 'time_increment_sec': 0, 'move_count': 3,
      'initial_fen': initialFen, 'final_fen': afterNf3, 'pgn': null,
      'moves': moves ??
          [mv(1, 'e4', 'e2e4', afterE4), mv(2, 'e5', 'e7e5', afterE5), mv(3, 'Nf3', 'g1f3', afterNf3)],
    });

Future<void> pumpReplay(WidgetTester tester, GameDetail detail, {Size size = const Size(400, 800)}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(ProviderScope(
    overrides: [gameDetailProvider.overrideWith((ref, id) async => detail)],
    child: const MaterialApp(home: ReplayScreen(gameId: 7)),
  ));
  await tester.pumpAndSettle();
}

ChessBoard board(WidgetTester tester) => tester.widget<ChessBoard>(find.byType(ChessBoard));

bool enabled(WidgetTester tester, String tooltip) =>
    tester.widget<IconButton>(find.widgetWithIcon(IconButton, switch (tooltip) {
      'First move' => Icons.first_page,
      'Previous move' => Icons.chevron_left,
      'Next move' => Icons.chevron_right,
      _ => Icons.last_page,
    })).onPressed != null;

void main() {
  test('move numbers and rows, White first', () {
    final rows = moveRows(startFen, game().moves);
    expect(rows.map((r) => '${r.number}. ${r.white?.san ?? '…'} ${r.black?.san ?? ''}'.trim()),
        ['1. e4 e5', '2. Nf3']);
  });

  test('move numbers and rows when Black moves first', () {
    const fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1';
    expect(moveNumber(fen, 0), (number: 1, white: false));
    expect(moveNumber(fen, 1), (number: 2, white: true));
    final rows = moveRows(fen, [
      MoveInfo.fromJson(mv(1, 'e5', 'e7e5', afterE5)),
      MoveInfo.fromJson(mv(2, 'Nf3', 'g1f3', afterNf3)),
    ]);
    expect(rows.map((r) => '${r.number}. ${r.white?.san ?? '…'} ${r.black?.san ?? ''}'.trim()),
        ['1. … e5', '2. Nf3']);
  });

  testWidgets('buttons step through the game and are disabled at the ends', (tester) async {
    await pumpReplay(tester, game());
    // Opens on the final position with the last move highlighted.
    expect(board(tester).fen, afterNf3);
    expect(board(tester).lastMove, 'g1f3');
    expect(enabled(tester, 'Next move'), isFalse);
    expect(enabled(tester, 'Last move'), isFalse);

    await tester.tap(find.byTooltip('Previous move'));
    await tester.pumpAndSettle();
    expect(board(tester).fen, afterE5);
    expect(board(tester).lastMove, 'e7e5');

    await tester.tap(find.byTooltip('First move'));
    await tester.pumpAndSettle();
    expect(board(tester).fen, startFen);
    expect(board(tester).lastMove, isNull);
    expect(enabled(tester, 'Previous move'), isFalse);
    expect(enabled(tester, 'First move'), isFalse);

    await tester.tap(find.byTooltip('Next move'));
    await tester.pumpAndSettle();
    expect(board(tester).fen, afterE4);

    await tester.tap(find.byTooltip('Last move'));
    await tester.pumpAndSettle();
    expect(board(tester).fen, afterNf3);
  });

  testWidgets('keyboard arrows, Home and End navigate', (tester) async {
    await pumpReplay(tester, game());
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowLeft);
    await tester.pumpAndSettle();
    expect(board(tester).fen, afterE5);
    await tester.sendKeyEvent(LogicalKeyboardKey.home);
    await tester.pumpAndSettle();
    expect(board(tester).fen, startFen);
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowLeft); // already at the start
    await tester.pumpAndSettle();
    expect(board(tester).fen, startFen);
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
    await tester.pumpAndSettle();
    expect(board(tester).fen, afterE4);
    await tester.sendKeyEvent(LogicalKeyboardKey.end);
    await tester.pumpAndSettle();
    expect(board(tester).fen, afterNf3);
  });

  testWidgets('clicking a move jumps to it and highlights it', (tester) async {
    await pumpReplay(tester, game());
    await tester.tap(find.text('e4'));
    await tester.pumpAndSettle();
    expect(board(tester).fen, afterE4);
    expect(find.text('1. e4  (–)'), findsNothing); // nav label uses move number
    expect(find.textContaining('1. e4'), findsOneWidget);
  });

  testWidgets('wide screens put the moves beside the board', (tester) async {
    await pumpReplay(tester, game(), size: const Size(1200, 800));
    final boardBox = tester.getRect(find.byType(ChessBoard));
    final movesBox = tester.getRect(find.text('Moves'));
    expect(movesBox.left, greaterThan(boardBox.right));

    await pumpReplay(tester, game(), size: const Size(400, 800));
    expect(tester.getRect(find.text('Moves')).top, greaterThan(tester.getRect(find.byType(ChessBoard)).bottom));
  });
}
