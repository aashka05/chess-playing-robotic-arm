import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'features/auth/auth_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/home/home_screen.dart';

class ChessRobotApp extends ConsumerWidget {
  const ChessRobotApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loggedIn = ref.watch(authProvider) != null;
    return MaterialApp(
      title: 'Robot Chess',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.brown, useMaterial3: true),
      darkTheme: ThemeData(colorSchemeSeed: Colors.brown, brightness: Brightness.dark, useMaterial3: true),
      // Logging out swaps the whole navigator back to the login screen.
      home: loggedIn ? const HomeScreen(key: ValueKey('home')) : const LoginScreen(key: ValueKey('login')),
    );
  }
}
