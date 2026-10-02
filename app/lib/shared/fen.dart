// Minimal FEN helpers: enough to draw a position.

const files = 'abcdefgh';

/// Square name ("e4") -> FEN piece symbol, for the placement field of [fen].
Map<String, String> piecesFromFen(String fen) {
  final placement = fen.split(' ').first;
  final pieces = <String, String>{};
  final ranks = placement.split('/');
  for (var r = 0; r < ranks.length && r < 8; r++) {
    var file = 0;
    for (final ch in ranks[r].split('')) {
      final skip = int.tryParse(ch);
      if (skip != null) {
        file += skip;
      } else {
        if (file < 8) pieces['${files[file]}${8 - r}'] = ch;
        file++;
      }
    }
  }
  return pieces;
}

String sideToMove(String fen) {
  final parts = fen.split(' ');
  return parts.length > 1 && parts[1] == 'b' ? 'black' : 'white';
}

const _names = {'p': 'pawn', 'n': 'knight', 'b': 'bishop', 'r': 'rook', 'q': 'queen', 'k': 'king'};

/// "P" -> "white pawn", null -> "empty".
String pieceName(String? symbol) {
  if (symbol == null) return 'empty';
  final color = symbol == symbol.toUpperCase() ? 'white' : 'black';
  return '$color ${_names[symbol.toLowerCase()] ?? symbol}';
}
