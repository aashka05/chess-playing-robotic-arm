import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../shared/widgets.dart';
import 'setup_step.dart';

/// Setup 1: photograph the empty board so the backend can rectify it.
class SetupEmptyStep extends ConsumerStatefulWidget {
  const SetupEmptyStep({super.key, required this.onCalibrated, required this.onSkip, required this.done});

  final VoidCallback onCalibrated;

  /// Developer shortcut past both camera steps.
  final VoidCallback onSkip;

  /// Already calibrated (the user came back to this step).
  final bool done;

  @override
  ConsumerState<SetupEmptyStep> createState() => _SetupEmptyStepState();
}

class _SetupEmptyStepState extends ConsumerState<SetupEmptyStep> {
  bool _busy = false;
  String? _preview;

  Future<void> _calibrate() async {
    setState(() => _busy = true);
    try {
      final result = await ref.read(apiClientProvider).calibrate();
      setState(() => _preview = result.previewJpegBase64);
      widget.onCalibrated();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _devSkip() async {
    try {
      await ref.read(apiClientProvider).debugSkipSetup();
      widget.onSkip();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SetupStep(
      title: 'Place the empty board',
      instructions: widget.done
          ? 'The board is calibrated. Press Next to continue, or retake the photo '
              '(you will need to check the pieces again afterwards).'
          : 'Place the empty board and mount the camera on top. '
              'All four corner markers must be visible to the camera. Then press Take photo.',
      busy: _busy,
      onOk: _calibrate,
      okLabel: widget.done ? 'Retake photo' : 'Take photo',
      footer: TextButton(onPressed: _devSkip, child: const Text('Developer: skip camera setup')),
      child: _preview == null || _preview!.isEmpty
          ? const Icon(Icons.grid_on, size: 120, color: Colors.brown)
          : Image.memory(base64Decode(_preview!), gaplessPlayback: true),
    );
  }
}
