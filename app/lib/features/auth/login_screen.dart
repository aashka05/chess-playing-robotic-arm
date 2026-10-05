import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../shared/widgets.dart';
import 'auth_controller.dart';
import 'password_reset_screens.dart';
import 'server_settings_dialog.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _form = GlobalKey<FormState>();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _register = false;
  bool _busy = false;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final auth = ref.read(authProvider.notifier);
    try {
      if (_register) {
        await auth.register(_username.text.trim(), _email.text.trim(), _password.text);
      } else {
        await auth.login(_email.text.trim(), _password.text);
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Robot Chess'),
        actions: [
          IconButton(
            tooltip: 'Server settings',
            icon: const Icon(Icons.settings_ethernet),
            onPressed: () => showServerSettings(context),
          ),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _form,
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  const Icon(Icons.precision_manufacturing, size: 72),
                  const SizedBox(height: 8),
                  Text(_register ? 'Create account' : 'Log in',
                      style: Theme.of(context).textTheme.headlineSmall, textAlign: TextAlign.center),
                  Text('Server: ${ref.watch(baseUrlProvider)}',
                      textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: 24),
                  if (_register)
                    TextFormField(
                      controller: _username,
                      decoration: const InputDecoration(labelText: 'Username'),
                      validator: (v) => (v == null || v.trim().length < 2) ? 'At least 2 characters' : null,
                    ),
                  TextFormField(
                    controller: _email,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.email],
                    decoration: const InputDecoration(labelText: 'Email'),
                    validator: (v) => (v == null || !v.contains('@')) ? 'Enter your email' : null,
                  ),
                  PasswordField(
                    controller: _password,
                    autofillHints: [_register ? AutofillHints.newPassword : AutofillHints.password],
                    validator: (v) => (v == null || v.length < 6) ? 'At least 6 characters' : null,
                    onFieldSubmitted: (_) => _submit(),
                  ),
                  if (!_register)
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => ForgotPasswordScreen(email: _email.text.trim())),
                        ),
                        child: const Text('Forgot password?'),
                      ),
                    ),
                  const SizedBox(height: 24),
                  BusyButton(
                    label: _register ? 'Create account' : 'Log in',
                    busy: _busy,
                    icon: Icons.login,
                    onPressed: _submit,
                  ),
                  TextButton(
                    onPressed: () => setState(() => _register = !_register),
                    child: Text(_register ? 'I already have an account' : 'Create an account'),
                  ),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
