import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../core/providers.dart';
import '../../shared/widgets.dart';
import 'game_options_screen.dart';
import 'setup_pieces_screen.dart';
import 'setup_step.dart';

/// Setup 1: photograph the empty board so the backend can rectify it.
/// Pops with the new game id once the whole setup finishes.
class SetupEmptyScreen extends ConsumerStatefulWidget {
  const SetupEmptyScreen({super.key, required this.initialStatus});

  final SetupStatus initialStatus;

  @override
  ConsumerState<SetupEmptyScreen> createState() => _SetupEmptyScreenState();
}

class _SetupEmptyScreenState extends ConsumerState<SetupEmptyScreen> {
  bool _busy = false;
  String? _preview;

  Future<void> _continue(Widget next) async {
    final gameId = await Navigator.push<int>(context, MaterialPageRoute(builder: (_) => next));
    if (gameId != null && mounted) Navigator.pop(context, gameId);
  }

  Future<void> _calibrate() async {
    setState(() => _busy = true);
    try {
      final result = await ref.read(apiClientProvider).calibrate();
      setState(() => _preview = result.previewJpegBase64);
      if (mounted) await _continue(const SetupPiecesScreen());
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _devSkip() async {
    try {
      await ref.read(apiClientProvider).debugSkipSetup();
      if (mounted) await _continue(const GameOptionsScreen());
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      onPopInvokedWithResult: (didPop, result) {
        if (didPop && result == null) ref.read(apiClientProvider).cancelSetup().ignore();
      },
      child: SetupStep(
        step: 1,
        title: 'Place the empty board',
        instructions: 'Place the empty board and mount the camera on top. '
            'All four corner markers must be visible to the camera. Then press OK.',
        busy: _busy,
        onOk: _calibrate,
        footer: TextButton(onPressed: _devSkip, child: const Text('Developer: skip camera setup')),
        child: _preview == null || _preview!.isEmpty
            ? const Icon(Icons.grid_on, size: 120, color: Colors.brown)
            : Image.memory(base64Decode(_preview!), gaplessPlayback: true),
      ),
    );
  }
}
