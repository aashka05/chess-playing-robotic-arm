import 'package:flutter/material.dart';

import 'fen.dart';

const _glyphs = {'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'};

// Variation selector 15 = "draw as text". Without it iOS/Android render ♟
// (the only chess symbol with a default emoji form) as a black emoji that
// ignores the text colour, so white pawns looked black.
const _textPresentation = '\uFE0E';

/// FEN symbol -> glyph to draw and its colour (uppercase = white).
({String glyph, bool white}) pieceGlyph(String symbol) => (
      glyph: '${_glyphs[symbol.toLowerCase()] ?? '?'}$_textPresentation',
      white: symbol == symbol.toUpperCase(),
    );

/// Draws a position from a FEN string. Pure display, no interaction.
class ChessBoard extends StatelessWidget {
  const ChessBoard({
    super.key,
    required this.fen,
    this.flipped = false,
    this.highlights = const {},
    this.lastMove,
    this.showCoordinates = true,
  });

  final String fen;

  /// Draw from Black's side.
  final bool flipped;

  /// Square name -> overlay colour (e.g. wrong squares in setup).
  final Map<String, Color> highlights;

  /// UCI of the last move, highlighted in yellow.
  final String? lastMove;
  final bool showCoordinates;

  static const light = Color(0xFFEEDDBB);
  static const dark = Color(0xFFB58863);

  @override
  Widget build(BuildContext context) {
    final pieces = piecesFromFen(fen);
    final lastSquares = lastMove == null || lastMove!.length < 4
        ? const <String>{}
        : {lastMove!.substring(0, 2), lastMove!.substring(2, 4)};

    return AspectRatio(
      aspectRatio: 1,
      child: LayoutBuilder(builder: (context, constraints) {
        final size = constraints.maxWidth / 8;
        return Column(
          children: [
            for (var row = 0; row < 8; row++)
              Row(
                children: [
                  for (var col = 0; col < 8; col++)
                    _square(
                      name: flipped ? '${files[7 - col]}${row + 1}' : '${files[col]}${8 - row}',
                      isLight: (row + col).isEven,
                      size: size,
                      pieces: pieces,
                      lastSquares: lastSquares,
                      rankLabel: col == 0,
                      fileLabel: row == 7,
                    ),
                ],
              ),
          ],
        );
      }),
    );
  }

  Widget _square({
    required String name,
    required bool isLight,
    required double size,
    required Map<String, String> pieces,
    required Set<String> lastSquares,
    required bool rankLabel,
    required bool fileLabel,
  }) {
    final piece = pieces[name];
    final labelStyle = TextStyle(fontSize: size * 0.18, color: isLight ? dark : light, fontWeight: FontWeight.w600);
    return Container(
      width: size,
      height: size,
      color: isLight ? light : dark,
      child: Stack(
        children: [
          if (lastSquares.contains(name)) Positioned.fill(child: Container(color: const Color(0x66F6F669))),
          if (highlights[name] != null) Positioned.fill(child: Container(color: highlights[name])),
          if (showCoordinates && rankLabel) Positioned(left: 2, top: 1, child: Text(name[1], style: labelStyle)),
          if (showCoordinates && fileLabel) Positioned(right: 2, bottom: 0, child: Text(name[0], style: labelStyle)),
          if (piece != null) Center(child: _piece(piece, size)),
        ],
      ),
    );
  }

  Widget _piece(String symbol, double size) {
    final (:glyph, :white) = pieceGlyph(symbol);
    final fontSize = size * 0.78;
    // Solid glyph filled with the piece colour, outlined for contrast.
    return Stack(
      alignment: Alignment.center,
      children: [
        Text(
          glyph,
          style: TextStyle(
            fontSize: fontSize,
            height: 1,
            foreground: Paint()
              ..style = PaintingStyle.stroke
              ..strokeWidth = size * 0.05
              ..color = white ? Colors.black : Colors.white70,
          ),
        ),
        Text(glyph, style: TextStyle(fontSize: fontSize, height: 1, color: white ? Colors.white : Colors.black)),
      ],
    );
  }
}
