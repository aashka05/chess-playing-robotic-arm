import 'dart:convert';
import 'dart:math';

import 'package:chess_robot/core/providers.dart';
import 'package:chess_robot/shared/board_theme.dart';
import 'package:chess_robot/shared/chess_board.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

double contrast(Color a, Color b) {
  final la = a.computeLuminance(), lb = b.computeLuminance();
  return (max(la, lb) + 0.05) / (min(la, lb) + 0.05);
}

Future<ProviderContainer> container(Map<String, Object> prefs) async {
  SharedPreferences.setMockInitialValues(prefs);
  final instance = await SharedPreferences.getInstance();
  return ProviderContainer(overrides: [sharedPrefsProvider.overrideWithValue(instance)]);
}

String session(int userId) => jsonEncode({
      'token': 't',
      'user': {'user_id': userId, 'username': 'u$userId', 'email': 'u@x.y', 'role': 'client'},
    });

void main() {
  test('five board themes, Brown first and the default', () {
    expect(boardThemes.map((t) => t.name), ['Brown', 'Wood', 'Blue', 'Green', 'Maple']);
    expect(boardThemes.map((t) => t.id).toSet().length, 5);
    expect(boardThemeById(null), brownTheme);
    expect(boardThemeById('nope'), brownTheme);
    // Brown keeps the original look.
    expect(brownTheme.light, const Color(0xFFEEDDBB));
    expect(brownTheme.dark, const Color(0xFFB58863));
  });

  test('wood and maple are textured; the flat themes are not', () {
    for (final t in boardThemes) {
      final textured = t.square(isLight: true).gradient != null;
      expect(textured, ['wood', 'maple'].contains(t.id), reason: t.id);
    }
  });

  test('squares, labels and pieces stay readable on every theme', () {
    for (final t in boardThemes) {
      expect(contrast(t.light, t.dark), greaterThan(1.6), reason: '${t.id} squares');
      expect(contrast(t.coordinateOn(lightSquare: true), t.light), greaterThan(1.6), reason: '${t.id} labels');
      for (final sq in [t.light, t.dark, ...[t.lightGrain, t.darkGrain].nonNulls]) {
        // White pieces: white fill + black outline. Black pieces: black fill + light outline.
        final whitePiece = max(contrast(Colors.white, sq), contrast(Colors.black, sq));
        final blackPiece = max(contrast(Colors.black, sq), contrast(Colors.white70, sq));
        expect(whitePiece, greaterThan(3), reason: '${t.id} white piece on $sq');
        expect(blackPiece, greaterThan(3), reason: '${t.id} black piece on $sq');
      }
    }
  });

  test('selection is persisted per user', () async {
    var c = await container({'auth_session': session(1)});
    expect(c.read(boardThemeProvider), brownTheme);
    await c.read(boardThemeProvider.notifier).select(boardThemeById('green'));
    expect(c.read(boardThemeProvider).id, 'green');
    final prefs = c.read(sharedPrefsProvider);
    expect(prefs.getString('board_theme_user_1'), 'green');
    c.dispose();

    // Same user on a fresh start gets their theme back; another user doesn't.
    c = await container({'auth_session': session(1), 'board_theme_user_1': 'green'});
    expect(c.read(boardThemeProvider).id, 'green');
    c.dispose();
    c = await container({'auth_session': session(2), 'board_theme_user_1': 'green'});
    expect(c.read(boardThemeProvider), brownTheme);
    c.dispose();
  });

  testWidgets('ChessBoard draws squares from the scoped theme', (tester) async {
    final blue = boardThemeById('blue');
    await tester.pumpWidget(MaterialApp(
      home: BoardThemeScope(
        theme: blue,
        child: const Center(
          child: SizedBox(width: 400, child: ChessBoard(fen: '8/8/8/8/8/8/8/8 w - - 0 1', lastMove: 'e2e4')),
        ),
      ),
    ));
    final colors = tester
        .widgetList<Container>(find.byType(Container))
        .map((c) => (c.decoration as BoxDecoration?)?.color ?? c.color)
        .nonNulls
        .toSet();
    expect(colors, containsAll([blue.light, blue.dark, blue.lastMove]));
    expect(colors, isNot(contains(brownTheme.dark)));
  });

  testWidgets('picker swatch selects a theme', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    await tester.pumpWidget(ProviderScope(
      overrides: [sharedPrefsProvider.overrideWithValue(prefs)],
      child: const MaterialApp(home: Scaffold(body: BoardThemePicker())),
    ));
    await tester.tap(find.byKey(const ValueKey('board-theme-maple')));
    await tester.pump();
    expect(prefs.getString('board_theme'), 'maple');
  });
}
