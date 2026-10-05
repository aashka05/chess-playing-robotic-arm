import 'package:flutter/material.dart';

void showError(BuildContext context, Object error) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(error.toString()), backgroundColor: Colors.red.shade700));
}

/// Primary button that shows a spinner while [onPressed] runs.
class BusyButton extends StatelessWidget {
  const BusyButton({super.key, required this.label, required this.busy, required this.onPressed, this.icon});

  final String label;
  final bool busy;
  final VoidCallback? onPressed;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return FilledButton.icon(
      style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
      onPressed: busy ? null : onPressed,
      icon: busy
          ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
          : Icon(icon ?? Icons.check),
      label: Text(label),
    );
  }
}

class ErrorRetry extends StatelessWidget {
  const ErrorRetry({super.key, required this.error, required this.onRetry});

  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(error.toString(), textAlign: TextAlign.center),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
        ]),
      ),
    );
  }
}

class CameraStatusChip extends StatelessWidget {
  const CameraStatusChip({super.key, required this.connected});

  final bool connected;

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(connected ? Icons.videocam : Icons.videocam_off, size: 18,
          color: connected ? Colors.green : Colors.red),
      label: Text(connected ? 'Camera phone connected' : 'Camera phone not connected'),
    );
  }
}

/// Password input with an eye button that shows/hides the text.
class PasswordField extends StatefulWidget {
  const PasswordField({
    super.key,
    required this.controller,
    this.label = 'Password',
    this.validator,
    this.onFieldSubmitted,
    this.autofillHints = const [AutofillHints.password],
  });

  final TextEditingController controller;
  final String label;
  final FormFieldValidator<String>? validator;
  final ValueChanged<String>? onFieldSubmitted;
  final Iterable<String> autofillHints;

  @override
  State<PasswordField> createState() => _PasswordFieldState();
}

class _PasswordFieldState extends State<PasswordField> {
  bool _obscured = true;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: widget.controller,
      obscureText: _obscured,
      autocorrect: false,
      enableSuggestions: false,
      autofillHints: widget.autofillHints,
      decoration: InputDecoration(
        labelText: widget.label,
        // A focusable button (keyboard/screen-reader reachable); the tooltip is its accessible label.
        suffixIcon: IconButton(
          tooltip: _obscured ? 'Show password' : 'Hide password',
          icon: Icon(_obscured ? Icons.visibility : Icons.visibility_off),
          onPressed: () => setState(() => _obscured = !_obscured),
        ),
      ),
      validator: widget.validator,
      onFieldSubmitted: widget.onFieldSubmitted,
    );
  }
}
