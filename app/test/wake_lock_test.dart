import 'package:chess_robot/shared/wake_lock.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('acquire, re-acquire on resume, release', () async {
    final calls = <bool>[];
    final lock = ScreenWakeLock(setEnabled: (on) async => calls.add(on));
    lock.acquire();
    lock.acquire(); // idempotent
    expect(calls, [true]);
    // The OS may drop the lock while the app is hidden; it comes back on resume.
    lock.didChangeAppLifecycleState(AppLifecycleState.paused);
    lock.didChangeAppLifecycleState(AppLifecycleState.resumed);
    expect(calls, [true, true]);
    lock.release();
    expect(calls, [true, true, false]);
    // Not re-acquired after release (e.g. the game ended).
    lock.didChangeAppLifecycleState(AppLifecycleState.resumed);
    expect(calls, [true, true, false]);
    lock.dispose();
    expect(calls, [true, true, false]);
  });

  test('dispose releases a held lock', () {
    final calls = <bool>[];
    ScreenWakeLock(setEnabled: (on) async => calls.add(on))
      ..acquire()
      ..dispose();
    expect(calls, [true, false]);
  });

  test('unsupported platforms degrade gracefully', () async {
    final lock = ScreenWakeLock(setEnabled: (on) => Future.error(UnsupportedError('no wake lock')));
    lock.acquire();
    await Future<void>.delayed(Duration.zero);
    expect(lock.held, isTrue);
    lock.dispose();
  });
}
