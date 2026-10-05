import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import '../../shared/widgets.dart';

/// Step 1: ask the server to email a reset code.
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key, this.email = ''});

  final String email;

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _form = GlobalKey<FormState>();
  late final _email = TextEditingController(text: widget.email);
  bool _busy = false;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ApiClient(baseUrl: ref.read(baseUrlProvider)).forgotPassword(_email.text.trim());
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('If an account exists for this email, a reset code has been sent.')),
      );
      _openReset();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _openReset() =>
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const ResetPasswordScreen()));

  @override
  Widget build(BuildContext context) {
    return _AuthPage(
      title: 'Forgot password',
      child: Form(
        key: _form,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Enter your account email and we\'ll send you a reset code.'),
          const SizedBox(height: 16),
          TextFormField(
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            decoration: const InputDecoration(labelText: 'Email'),
            validator: (v) => (v == null || !v.contains('@')) ? 'Enter your email' : null,
            onFieldSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 24),
          BusyButton(label: 'Send reset code', icon: Icons.email, busy: _busy, onPressed: _submit),
          TextButton(onPressed: _openReset, child: const Text('I have a reset code')),
        ]),
      ),
    );
  }
}

/// Step 2: enter the emailed code and the new password (twice).
class ResetPasswordScreen extends ConsumerStatefulWidget {
  const ResetPasswordScreen({super.key});

  @override
  ConsumerState<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _form = GlobalKey<FormState>();
  final _code = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ApiClient(baseUrl: ref.read(baseUrlProvider)).resetPassword(_code.text.trim(), _password.text);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Password updated. Log in with your new password.')),
      );
      Navigator.popUntil(context, (route) => route.isFirst);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _AuthPage(
      title: 'Reset password',
      child: Form(
        key: _form,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          TextFormField(
            controller: _code,
            autocorrect: false,
            enableSuggestions: false,
            decoration: const InputDecoration(labelText: 'Reset code', helperText: 'Paste the code from the email'),
            validator: (v) => (v == null || v.trim().length < 16) ? 'Paste the full code from the email' : null,
          ),
          PasswordField(
            controller: _password,
            label: 'New password',
            autofillHints: const [AutofillHints.newPassword],
            validator: (v) => (v == null || v.length < 6) ? 'At least 6 characters' : null,
          ),
          PasswordField(
            controller: _confirm,
            label: 'Confirm new password',
            autofillHints: const [AutofillHints.newPassword],
            validator: (v) => v != _password.text ? 'Passwords do not match' : null,
            onFieldSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 24),
          BusyButton(label: 'Set new password', icon: Icons.lock_reset, busy: _busy, onPressed: _submit),
        ]),
      ),
    );
  }
}

class _AuthPage extends StatelessWidget {
  const _AuthPage({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 420), child: child),
          ),
        ),
      ),
    );
  }
}
