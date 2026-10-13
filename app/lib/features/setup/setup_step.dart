import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/widgets.dart';
import 'setup_providers.dart';

/// Shared layout for the setup steps: title, instructions, camera status, body, action button.
class SetupStep extends ConsumerWidget {
  const SetupStep({
    super.key,
    required this.title,
    required this.instructions,
    required this.busy,
    required this.onOk,
    this.okLabel = 'OK',
    this.child,
    this.footer,
  });

  final String title;
  final String instructions;
  final bool busy;
  final VoidCallback onOk;
  final String okLabel;
  final Widget? child;
  final Widget? footer;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final camera = ref.watch(cameraConnectedProvider).value ?? false;
    return ListView(padding: const EdgeInsets.all(20), children: [
      Text(title, style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 12),
      Text(instructions, style: Theme.of(context).textTheme.bodyLarge),
      const SizedBox(height: 12),
      Align(alignment: Alignment.centerLeft, child: CameraStatusChip(connected: camera)),
      const SizedBox(height: 16),
      ?child,
      const SizedBox(height: 16),
      BusyButton(label: busy ? 'Taking picture…' : okLabel, busy: busy, onPressed: onOk),
      ?footer,
    ]);
  }
}
