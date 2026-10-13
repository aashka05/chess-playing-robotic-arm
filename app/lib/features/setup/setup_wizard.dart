import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'game_options_screen.dart';
import 'setup_empty_screen.dart';
import 'setup_pieces_screen.dart';

const setupStepLabels = ['Empty board', 'Pieces', 'Game options'];

/// What must be done on each step before moving past it for the first time.
const _requirements = [
  'Photograph the empty board first: press "Take photo".',
  'The camera has to confirm the starting position first: press "Check position".',
];

/// Which steps are done and how far the user has got. Pure, so the rules are testable.
@immutable
class SetupProgress {
  const SetupProgress({this.current = 0, this.reached = 0, this.completed = const {}});

  final int current;

  /// Furthest step visited; any step up to here can be revisited freely.
  final int reached;

  /// Steps whose camera check succeeded.
  final Set<int> completed;

  /// Null if [target] can be shown now, otherwise what the user must do first.
  String? blockedReason(int target) {
    if (target < 0 || target >= setupStepLabels.length) return 'There is no such step.';
    if (target <= reached) return null;
    for (var step = current; step < target; step++) {
      if (!completed.contains(step)) return _requirements[step];
    }
    return null;
  }

  SetupProgress goTo(int target) => SetupProgress(
        current: target,
        reached: target > reached ? target : reached,
        completed: completed,
      );

  /// [step] passed its check. Redoing a step invalidates the steps after it
  /// (e.g. a new empty-board photo means the pieces must be checked again).
  SetupProgress complete(int step) => SetupProgress(
        current: current,
        reached: reached > step + 1 ? step + 1 : reached,
        completed: {...completed.where((s) => s < step), step},
      );

  /// [step]'s check failed, so it and the steps after it need doing again.
  SetupProgress fail(int step) => SetupProgress(
        current: current,
        reached: reached > step ? step : reached,
        completed: {...completed.where((s) => s < step)},
      );
}

/// The three setup steps in one screen. Steps stay alive (IndexedStack) so
/// nothing entered is lost when moving back and forth. Pops with the game id.
class SetupWizardScreen extends ConsumerStatefulWidget {
  const SetupWizardScreen({super.key});

  @override
  ConsumerState<SetupWizardScreen> createState() => _SetupWizardScreenState();
}

class _SetupWizardScreenState extends ConsumerState<SetupWizardScreen> {
  SetupProgress _progress = const SetupProgress();
  String? _error;

  void _goTo(int target) {
    final reason = _progress.blockedReason(target);
    setState(() {
      _error = reason;
      if (reason == null) _progress = _progress.goTo(target);
    });
  }

  /// A step's camera check finished: record it and move on if it passed.
  void _stepResult(int step, bool passed) {
    setState(() {
      _error = null;
      _progress = passed ? _progress.complete(step) : _progress.fail(step);
    });
    if (passed) _goTo(step + 1);
  }

  void _skipCameraSteps() {
    setState(() => _progress = _progress.complete(0).complete(1));
    _goTo(2);
  }

  @override
  Widget build(BuildContext context) {
    final current = _progress.current;
    final last = setupStepLabels.length - 1;
    return PopScope(
      onPopInvokedWithResult: (didPop, result) {
        if (didPop && result == null) ref.read(apiClientProvider).cancelSetup().ignore();
      },
      child: Scaffold(
        appBar: AppBar(title: Text('Setup ${current + 1} of ${setupStepLabels.length}')),
        body: SafeArea(
          child: Column(children: [
            _StepIndicator(progress: _progress, onTap: _goTo),
            const Divider(height: 1),
            Expanded(
              child: IndexedStack(index: current, children: [
                SetupEmptyStep(
                  // A failed photo keeps the previous calibration, so only success changes progress.
                  onCalibrated: () => _stepResult(0, true),
                  onSkip: _skipCameraSteps,
                  done: _progress.completed.contains(0),
                ),
                SetupPiecesStep(onResult: (ok) => _stepResult(1, ok), done: _progress.completed.contains(1)),
                const GameOptionsStep(),
              ]),
            ),
            if (_error != null)
              Material(
                color: Theme.of(context).colorScheme.errorContainer,
                child: ListTile(
                  key: const ValueKey('setup-error'),
                  dense: true,
                  leading: Icon(Icons.error_outline, color: Theme.of(context).colorScheme.onErrorContainer),
                  title: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer)),
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
              child: Row(children: [
                OutlinedButton.icon(
                  onPressed: current > 0 ? () => _goTo(current - 1) : null,
                  icon: const Icon(Icons.arrow_back),
                  label: const Text('Back'),
                ),
                const Spacer(),
                if (current < last)
                  FilledButton.tonalIcon(
                    onPressed: () => _goTo(current + 1),
                    icon: const Icon(Icons.arrow_forward),
                    label: const Text('Next'),
                  ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }
}

class _StepIndicator extends StatelessWidget {
  const _StepIndicator({required this.progress, required this.onTap});

  final SetupProgress progress;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(children: [
        for (var i = 0; i < setupStepLabels.length; i++) ...[
          if (i > 0) Expanded(child: Divider(color: i <= progress.reached ? scheme.primary : scheme.outlineVariant)),
          Semantics(
            button: true,
            selected: i == progress.current,
            enabled: i <= progress.reached,
            child: InkWell(
              key: ValueKey('setup-step-$i'),
              borderRadius: BorderRadius.circular(20),
              onTap: () => onTap(i),
              child: Padding(
                padding: const EdgeInsets.all(6),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  CircleAvatar(
                    radius: 14,
                    backgroundColor: i == progress.current
                        ? scheme.primary
                        : i <= progress.reached
                            ? scheme.primaryContainer
                            : scheme.surfaceContainerHighest,
                    foregroundColor: i == progress.current ? scheme.onPrimary : scheme.onSurface,
                    child: progress.completed.contains(i) && i != progress.current
                        ? const Icon(Icons.check, size: 16)
                        : Text('${i + 1}'),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    setupStepLabels[i],
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: i == progress.current ? FontWeight.bold : null,
                      color: i <= progress.reached ? scheme.onSurface : scheme.onSurfaceVariant,
                    ),
                  ),
                ]),
              ),
            ),
          ),
        ],
      ]),
    );
  }
}
