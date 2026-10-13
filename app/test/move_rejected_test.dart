import 'package:chess_robot/features/game/game_controller.dart';
import 'package:flutter_test/flutter_test.dart';

const fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

void main() {
  test('illegal move notice names the move and highlights its squares', () {
    final n = moveRejectedNotice(1, {
      'type': 'move_not_recognized', 'reason': 'no_change', 'fen': fen,
      'message': 'Illegal move: white rook from a1 to a3. The path is blocked by the white pawn on a2.',
      'explanation': {'kind': 'illegal', 'reason': 'blocked', 'from_square': 'a1', 'to_square': 'a3',
        'piece': 'white rook', 'changed_squares': ['a1', 'a3']},
    });
    expect(n.title, 'Illegal move');
    expect(n.message, startsWith('Illegal move: white rook from a1 to a3. The path is blocked'));
    expect(n.message, contains('play a legal move'));
    expect(n.squares, ['a1', 'a3']);
    expect(n.fen, fen);
  });

  test('unclear change lists the differing squares', () {
    final n = moveRejectedNotice(2, {
      'type': 'move_not_recognized', 'reason': 'board_mismatch', 'fen': fen,
      'message': "Couldn't work out which move was played: 3 squares differ ...",
      'explanation': {'kind': 'unclear', 'reason': 'unclear', 'from_square': null, 'to_square': null,
        'piece': null, 'changed_squares': ['e2', 'e4', 'd4']},
    });
    expect(n.title, 'Move not recognized');
    expect(n.squares, ['e2', 'e4', 'd4']);
  });

  test('older backends without an explanation still work', () {
    final n = moveRejectedNotice(3, {'type': 'move_not_recognized', 'reason': 'low_confidence', 'message': 'x'});
    expect(n.title, 'Move not recognized');
    expect(n.squares, isEmpty);
    expect(n.fen, isNull);
  });
}
