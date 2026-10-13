import 'dart:io';
import 'dart:ui' as ui;

import 'package:chess_robot/shared/chess_board.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// Renders every piece in both colours with the real bundled font and checks
/// actual pixels, so a glyph drawn in the wrong colour (e.g. an emoji
/// fallback) can't pass by only looking at widget properties.
void main() {
  setUpAll(() async {
    final bytes = File('assets/fonts/ChessPieces.ttf').readAsBytesSync();
    await (FontLoader(pieceFontFamily)..addFont(Future.value(ByteData.sublistView(bytes)))).load();
  });

  // Rank 8 black pieces, rank 7 black pawns, rank 2 white pawns, rank 1 white pieces.
  const fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1';

  testWidgets('every piece is filled with its own colour', (tester) async {
    final key = GlobalKey();
    await tester.pumpWidget(MaterialApp(
      home: Center(
        child: RepaintBoundary(
          key: key,
          child: const SizedBox(width: 400, child: ChessBoard(fen: fen, showCoordinates: false)),
        ),
      ),
    ));
    final boundary = key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
    final image = await tester.runAsync(() => boundary.toImage());
    final data = (await tester.runAsync(() => image!.toByteData(format: ui.ImageByteFormat.rawRgba)))!;
    final width = image!.width;
    final square = width / 8;

    /// Counts near-white and near-black pixels in the middle of a square.
    ({int white, int black}) inks(int file, int rankFromTop) {
      var white = 0, black = 0;
      for (var dy = -0.25; dy <= 0.25; dy += 0.02) {
        for (var dx = -0.25; dx <= 0.25; dx += 0.02) {
          final x = ((file + 0.5 + dx) * square).round();
          final y = ((rankFromTop + 0.5 + dy) * square).round();
          final i = (y * width + x) * 4;
          final r = data.getUint8(i), g = data.getUint8(i + 1), b = data.getUint8(i + 2);
          if (r > 235 && g > 235 && b > 235) white++;
          if (r < 30 && g < 30 && b < 30) black++;
        }
      }
      return (white: white, black: black);
    }

    const names = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook'];
    for (var file = 0; file < 8; file++) {
      for (final (row, white, label) in [
        (0, false, 'black ${names[file]}'),
        (1, false, 'black pawn'),
        (6, true, 'white pawn'),
        (7, true, 'white ${names[file]}'),
      ]) {
        final ink = inks(file, row);
        if (white) {
          expect(ink.white, greaterThan(ink.black * 2), reason: '$label on file $file: $ink');
        } else {
          expect(ink.black, greaterThan(ink.white * 2), reason: '$label on file $file: $ink');
        }
      }
    }
  });
}
