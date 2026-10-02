import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/models.dart';
import '../../core/providers.dart';
import '../../shared/widgets.dart';

class _TimeControl {
  const _TimeControl(this.minutes, this.increment);

  final int minutes;
  final int increment;

  String get label => '$minutes+$increment';
}

const _presets = [
  _TimeControl(3, 2),
  _TimeControl(5, 0),
  _TimeControl(10, 0),
  _TimeControl(10, 5),
  _TimeControl(15, 10),
  _TimeControl(30, 0),
];

/// Setup 3: colour, difficulty and time control. Pops with the game id.
class GameOptionsScreen extends ConsumerStatefulWidget {
  const GameOptionsScreen({super.key});

  @override
  ConsumerState<GameOptionsScreen> createState() => _GameOptionsScreenState();
}

class _GameOptionsScreenState extends ConsumerState<GameOptionsScreen> {
  String _color = 'white';
  String _difficulty = 'medium';
  int _minutes = 10;
  int _increment = 5;
  bool _busy = false;

  Future<void> _start() async {
    setState(() => _busy = true);
    try {
      final game = await ref.read(apiClientProvider).startGame(GameOptions(
            color: _color,
            difficulty: _difficulty,
            timeBaseSec: _minutes * 60,
            timeIncrementSec: _increment,
          ));
      if (mounted) Navigator.pop(context, game.gameId);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = Theme.of(context).textTheme.titleMedium;
    return Scaffold(
      appBar: AppBar(title: const Text('Setup 3 of 3')),
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(20), children: [
          Text('Board is ready ✓', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 24),
          Text('Your colour', style: title),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'white', label: Text('White'), icon: Icon(Icons.circle_outlined)),
              ButtonSegment(value: 'black', label: Text('Black'), icon: Icon(Icons.circle)),
            ],
            selected: {_color},
            onSelectionChanged: (s) => setState(() => _color = s.first),
          ),
          if (_color == 'black')
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text('The robot plays White and moves first.'),
            ),
          const SizedBox(height: 24),
          Text('Difficulty', style: title),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'easy', label: Text('Easy')),
              ButtonSegment(value: 'medium', label: Text('Medium')),
              ButtonSegment(value: 'hard', label: Text('Hard')),
            ],
            selected: {_difficulty},
            onSelectionChanged: (s) => setState(() => _difficulty = s.first),
          ),
          const SizedBox(height: 24),
          Text('Time control (minutes + increment seconds)', style: title),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 4, children: [
            for (final p in _presets)
              ChoiceChip(
                label: Text(p.label),
                selected: p.minutes == _minutes && p.increment == _increment,
                onSelected: (_) => setState(() {
                  _minutes = p.minutes;
                  _increment = p.increment;
                }),
              ),
          ]),
          const SizedBox(height: 8),
          _Stepper(label: 'Minutes', value: _minutes, min: 1, max: 180, onChanged: (v) => setState(() => _minutes = v)),
          _Stepper(label: 'Increment (s)', value: _increment, min: 0, max: 60, onChanged: (v) => setState(() => _increment = v)),
          const SizedBox(height: 32),
          BusyButton(label: 'Start', icon: Icons.timer, busy: _busy, onPressed: _start),
        ]),
      ),
    );
  }
}

class _Stepper extends StatelessWidget {
  const _Stepper({required this.label, required this.value, required this.min, required this.max, required this.onChanged});

  final String label;
  final int value;
  final int min;
  final int max;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Expanded(child: Text(label)),
      IconButton(onPressed: value > min ? () => onChanged(value - 1) : null, icon: const Icon(Icons.remove)),
      SizedBox(width: 36, child: Text('$value', textAlign: TextAlign.center)),
      IconButton(onPressed: value < max ? () => onChanged(value + 1) : null, icon: const Icon(Icons.add)),
    ]);
  }
}
