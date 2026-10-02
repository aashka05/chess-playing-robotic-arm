import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';

/// Polls whether phone A (camera mode) is connected to the backend.
final cameraConnectedProvider = StreamProvider.autoDispose<bool>((ref) async* {
  final api = ref.watch(apiClientProvider);
  while (true) {
    try {
      yield await api.cameraConnected();
    } catch (_) {
      yield false;
    }
    await Future<void>.delayed(const Duration(seconds: 3));
  }
});
