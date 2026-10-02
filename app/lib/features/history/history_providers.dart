import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../core/providers.dart';

final gameHistoryProvider = FutureProvider.autoDispose<List<GameSummary>>(
  (ref) => ref.watch(apiClientProvider).listGames(),
);

final gameDetailProvider = FutureProvider.autoDispose.family<GameDetail, int>(
  (ref, id) => ref.watch(apiClientProvider).getGame(id),
);
