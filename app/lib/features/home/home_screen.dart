import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../shared/widgets.dart';
import '../auth/auth_controller.dart';
import '../auth/server_settings_dialog.dart';
import '../game/game_screen.dart';
import '../history/history_list.dart';
import '../history/history_providers.dart';
import '../setup/camera_mode_screen.dart';
import '../setup/setup_empty_screen.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _resumeActiveGame());
  }

  /// If a game is still running on the backend (app was closed), go back to it.
  Future<void> _resumeActiveGame() async {
    try {
      final active = await ref.read(apiClientProvider).activeGame();
      if (active != null && mounted) await _openGame(active.gameId);
    } catch (_) {
      // offline or logged out; the history list will show the error
    }
  }

  Future<void> _openGame(int gameId) async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => GameScreen(gameId: gameId)));
    ref.invalidate(gameHistoryProvider);
  }

  Future<void> _playNewGame() async {
    setState(() => _busy = true);
    try {
      final status = await ref.read(apiClientProvider).startSetup();
      if (!mounted) return;
      final gameId = await Navigator.push<int>(
        context,
        MaterialPageRoute(builder: (_) => SetupEmptyScreen(initialStatus: status)),
      );
      if (gameId != null && mounted) await _openGame(gameId);
      ref.invalidate(gameHistoryProvider);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider)?.user;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Robot Chess'),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) async {
              switch (value) {
                case 'camera':
                  Navigator.push(context, MaterialPageRoute(builder: (_) => const CameraModeScreen()));
                case 'server':
                  await showServerSettings(context);
                  ref.invalidate(gameHistoryProvider);
                case 'logout':
                  ref.read(authProvider.notifier).logout();
              }
            },
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'camera', child: ListTile(leading: Icon(Icons.photo_camera), title: Text('Camera mode (phone A)'))),
              const PopupMenuItem(value: 'server', child: ListTile(leading: Icon(Icons.settings_ethernet), title: Text('Server settings'))),
              PopupMenuItem(value: 'logout', child: ListTile(leading: const Icon(Icons.logout), title: Text('Log out ${user?.username ?? ''}'))),
            ],
          ),
        ],
      ),
      body: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: BusyButton(label: 'Play New Game', icon: Icons.play_arrow, busy: _busy, onPressed: _playNewGame),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
            child: Text(user?.isAdmin == true ? 'Game History (all players)' : 'Game History',
                style: Theme.of(context).textTheme.titleMedium),
          ),
          Expanded(child: HistoryList(showOwner: user?.isAdmin == true)),
        ]),
      ),
    );
  }
}
