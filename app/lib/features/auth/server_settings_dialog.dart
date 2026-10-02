import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import '../../core/providers.dart';

Future<void> showServerSettings(BuildContext context) =>
    showDialog(context: context, builder: (_) => const _ServerSettingsDialog());

class _ServerSettingsDialog extends ConsumerStatefulWidget {
  const _ServerSettingsDialog();

  @override
  ConsumerState<_ServerSettingsDialog> createState() => _ServerSettingsDialogState();
}

class _ServerSettingsDialogState extends ConsumerState<_ServerSettingsDialog> {
  late final _controller = TextEditingController(text: ref.read(baseUrlProvider));
  String? _status;

  Future<void> _test() async {
    setState(() => _status = 'Testing…');
    try {
      final r = await http.get(Uri.parse('${_controller.text.trim()}/health')).timeout(const Duration(seconds: 5));
      setState(() => _status = r.statusCode == 200 ? 'Connected ✓' : 'Server answered ${r.statusCode}');
    } catch (e) {
      setState(() => _status = 'Cannot connect: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Backend server'),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(
          controller: _controller,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(labelText: 'Base URL', hintText: 'http://192.168.1.10:8000'),
        ),
        if (_status != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_status!)),
      ]),
      actions: [
        TextButton(onPressed: _test, child: const Text('Test')),
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        FilledButton(
          onPressed: () async {
            await ref.read(baseUrlProvider.notifier).set(_controller.text);
            if (context.mounted) Navigator.pop(context);
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}
