import 'package:chess_robot/core/providers.dart';
import 'package:chess_robot/features/auth/login_screen.dart';
import 'package:chess_robot/features/auth/password_reset_screens.dart';
import 'package:chess_robot/shared/widgets.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<void> pumpApp(WidgetTester tester, Widget home) async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  await tester.pumpWidget(ProviderScope(
    overrides: [sharedPrefsProvider.overrideWithValue(prefs)],
    child: MaterialApp(home: home),
  ));
}

bool obscured(WidgetTester tester, Finder field) =>
    tester.widget<EditableText>(find.descendant(of: field, matching: find.byType(EditableText))).obscureText;

void main() {
  testWidgets('eye button shows and hides the password', (tester) async {
    await pumpApp(tester, const Scaffold(body: _Field()));
    final field = find.byType(PasswordField);
    expect(obscured(tester, field), isTrue);
    expect(find.byTooltip('Show password'), findsOneWidget);
    expect(find.byIcon(Icons.visibility), findsOneWidget);

    await tester.tap(find.byTooltip('Show password'));
    await tester.pump();
    expect(obscured(tester, field), isFalse);
    expect(find.byTooltip('Hide password'), findsOneWidget);
    expect(find.byIcon(Icons.visibility_off), findsOneWidget);
  });

  testWidgets('eye button works from the keyboard', (tester) async {
    await pumpApp(tester, const Scaffold(body: _Field()));
    final button = find.byType(IconButton);
    Focus.of(tester.element(find.descendant(of: button, matching: find.byType(Icon)))).requestFocus();
    await tester.pump();
    await tester.sendKeyEvent(LogicalKeyboardKey.enter);
    await tester.pump();
    expect(obscured(tester, find.byType(PasswordField)), isFalse);
  });

  testWidgets('login page has the toggle and a forgot-password link', (tester) async {
    await pumpApp(tester, const LoginScreen());
    expect(find.byTooltip('Show password'), findsOneWidget);
    await tester.tap(find.text('Forgot password?'));
    await tester.pumpAndSettle();
    expect(find.byType(ForgotPasswordScreen), findsOneWidget);
    await tester.tap(find.text('I have a reset code'));
    await tester.pumpAndSettle();
    expect(find.byType(ResetPasswordScreen), findsOneWidget);
    expect(find.byTooltip('Show password'), findsNWidgets(2));
  });

  testWidgets('reset page validates the code and the confirmation', (tester) async {
    await pumpApp(tester, const ResetPasswordScreen());
    final fields = find.byType(TextFormField);
    await tester.enterText(fields.at(0), 'short');
    await tester.enterText(fields.at(1), 'secret12');
    await tester.enterText(fields.at(2), 'secret13');
    await tester.tap(find.text('Set new password'));
    await tester.pump();
    expect(find.text('Paste the full code from the email'), findsOneWidget);
    expect(find.text('Passwords do not match'), findsOneWidget);
  });
}

class _Field extends StatefulWidget {
  const _Field();

  @override
  State<_Field> createState() => _FieldState();
}

class _FieldState extends State<_Field> {
  final _controller = TextEditingController(text: 'hunter22');

  @override
  Widget build(BuildContext context) => PasswordField(controller: _controller);
}
