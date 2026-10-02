import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../shared/format.dart';
import '../../shared/widgets.dart';
import '../replay/replay_screen.dart';
import 'history_providers.dart';

/// Game History list (shown on the home screen).
class HistoryList extends ConsumerWidget {
  const HistoryList({super.key, this.showOwner = false});

  final bool showOwner;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final games = ref.watch(gameHistoryProvider);
    return RefreshIndicator(
      onRefresh: () => ref.refresh(gameHistoryProvider.future),
      child: games.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ListView(children: [ErrorRetry(error: e, onRetry: () => ref.invalidate(gameHistoryProvider))]),
        data: (list) => list.isEmpty
            ? ListView(children: const [
                Padding(padding: EdgeInsets.all(32), child: Center(child: Text('No games yet.'))),
              ])
            : ListView.separated(
                itemCount: list.length,
                separatorBuilder: (_, _) => const Divider(height: 1),
                itemBuilder: (context, i) => _GameTile(game: list[i], showOwner: showOwner),
              ),
      ),
    );
  }
}

class _GameTile extends StatelessWidget {
  const _GameTile({required this.game, required this.showOwner});

  final GameSummary game;
  final bool showOwner;

  @override
  Widget build(BuildContext context) {
    final label = resultLabel(game.result, game.status);
    final color = switch (game.result) {
      'win' => Colors.green,
      'loss' => Colors.red,
      'draw' => Colors.blueGrey,
      _ => Colors.grey,
    };
    final reason = terminationLabel(game.terminationReason);
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: game.userColor == 'white' ? Colors.white : Colors.black,
        child: Icon(Icons.person, color: game.userColor == 'white' ? Colors.black : Colors.white),
      ),
      title: Text('$label${reason.isNotEmpty && game.status != 'aborted' ? ' by $reason' : ''}',
          style: TextStyle(color: color, fontWeight: FontWeight.w600)),
      subtitle: Text([
        if (showOwner && game.username != null) game.username!,
        formatDate(game.startTime),
        '${capitalize(game.difficulty)} · ${game.timeControl} · ${game.moveCount} moves',
      ].join('\n')),
      isThreeLine: true,
      trailing: const Icon(Icons.chevron_right),
      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ReplayScreen(gameId: game.id))),
    );
  }
}
