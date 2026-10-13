import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/providers.dart';
import '../features/auth/auth_controller.dart';

/// Board square colours. Independent of the piece theme (see chess_board.dart).
/// Every board colour lives here; widgets never hardcode square colours.
class BoardTheme {
  const BoardTheme({
    required this.id,
    required this.name,
    required this.light,
    required this.dark,
    required this.lastMove,
    this.lightGrain,
    this.darkGrain,
  });

  final String id;
  final String name;
  final Color light;
  final Color dark;

  /// Overlay on the from/to squares of the last move.
  final Color lastMove;

  /// Optional second colour for a wood-grain gradient on light/dark squares.
  final Color? lightGrain;
  final Color? darkGrain;

  /// Rank/file labels use the opposite square colour, so they always contrast.
  Color coordinateOn({required bool lightSquare}) => lightSquare ? dark : light;

  /// Background for one square. [index] (0..63) varies the grain direction so
  /// the textured themes don't look like a repeated tile.
  BoxDecoration square({required bool isLight, int index = 0}) {
    final base = isLight ? light : dark;
    final grain = isLight ? lightGrain : darkGrain;
    if (grain == null) return BoxDecoration(color: base);
    final tilt = ((index * 37) % 7 - 3) / 10; // -0.3..0.3, deterministic
    return BoxDecoration(
      color: base,
      gradient: LinearGradient(
        begin: Alignment(-1, -1 + tilt),
        end: Alignment(1, 1 - tilt),
        colors: [base, grain, base, grain],
        stops: const [0, 0.35, 0.7, 1],
      ),
    );
  }
}

const brownTheme = BoardTheme(
  id: 'brown',
  name: 'Brown',
  light: Color(0xFFEEDDBB),
  dark: Color(0xFFB58863),
  lastMove: Color(0x66F6F669),
);

const boardThemes = <BoardTheme>[
  brownTheme,
  BoardTheme(
    id: 'wood',
    name: 'Wood',
    light: Color(0xFFE6C496),
    lightGrain: Color(0xFFD9B282),
    dark: Color(0xFF9C6B3F),
    darkGrain: Color(0xFF8A5A32),
    lastMove: Color(0x80E8E05A),
  ),
  BoardTheme(
    id: 'blue',
    name: 'Blue',
    light: Color(0xFFDEE3E6),
    dark: Color(0xFF8CA2AD),
    lastMove: Color(0x80C3D86B),
  ),
  BoardTheme(
    id: 'green',
    name: 'Green',
    light: Color(0xFFEEEED2),
    dark: Color(0xFF769656),
    lastMove: Color(0x80F6F669),
  ),
  BoardTheme(
    id: 'maple',
    name: 'Maple',
    light: Color(0xFFF6E7C9),
    lightGrain: Color(0xFFEEDAB2),
    dark: Color(0xFFCB9F6A),
    darkGrain: Color(0xFFBE905B),
    lastMove: Color(0x80E4E75E),
  ),
];

BoardTheme boardThemeById(String? id) => boardThemes.firstWhere((t) => t.id == id, orElse: () => brownTheme);

/// Makes the selected theme available to every [ChessBoard] below it.
class BoardThemeScope extends InheritedWidget {
  const BoardThemeScope({super.key, required this.theme, required super.child});

  final BoardTheme theme;

  static BoardTheme of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<BoardThemeScope>()?.theme ?? brownTheme;

  @override
  bool updateShouldNotify(BoardThemeScope oldWidget) => theme != oldWidget.theme;
}

/// The chosen board theme, saved per user on this device.
class BoardThemeNotifier extends Notifier<BoardTheme> {
  String get _key {
    final userId = ref.read(authProvider)?.user.id;
    return userId == null ? 'board_theme' : 'board_theme_user_$userId';
  }

  @override
  BoardTheme build() {
    ref.watch(authProvider.select((s) => s?.user.id)); // reload on login/logout
    return boardThemeById(ref.read(sharedPrefsProvider).getString(_key));
  }

  Future<void> select(BoardTheme theme) async {
    state = theme;
    await ref.read(sharedPrefsProvider).setString(_key, theme.id);
  }
}

final boardThemeProvider = NotifierProvider<BoardThemeNotifier, BoardTheme>(BoardThemeNotifier.new);

/// Swatch grid for choosing the board theme.
class BoardThemePicker extends ConsumerWidget {
  const BoardThemePicker({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected = ref.watch(boardThemeProvider);
    final scheme = Theme.of(context).colorScheme;
    return Wrap(spacing: 12, runSpacing: 12, children: [
      for (final theme in boardThemes)
        Semantics(
          button: true,
          selected: theme.id == selected.id,
          label: '${theme.name} board',
          child: InkWell(
            key: ValueKey('board-theme-${theme.id}'),
            borderRadius: BorderRadius.circular(8),
            onTap: () => ref.read(boardThemeProvider.notifier).select(theme),
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Container(
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: theme.id == selected.id ? scheme.primary : Colors.transparent,
                      width: 3,
                    ),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: ClipRRect(borderRadius: BorderRadius.circular(3), child: _Swatch(theme)),
                ),
                const SizedBox(height: 4),
                Text(theme.name, style: TextStyle(fontWeight: theme.id == selected.id ? FontWeight.bold : null)),
              ]),
            ),
          ),
        ),
    ]);
  }
}

class _Swatch extends StatelessWidget {
  const _Swatch(this.theme);

  final BoardTheme theme;

  @override
  Widget build(BuildContext context) {
    const cells = 4;
    const size = 14.0;
    return Column(mainAxisSize: MainAxisSize.min, children: [
      for (var r = 0; r < cells; r++)
        Row(mainAxisSize: MainAxisSize.min, children: [
          for (var c = 0; c < cells; c++)
            Container(
              width: size,
              height: size,
              decoration: theme.square(isLight: (r + c).isEven, index: r * cells + c),
            ),
        ]),
    ]);
  }
}

Future<void> showBoardThemePicker(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Board theme', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            const BoardThemePicker(),
          ]),
        ),
      ),
    );
