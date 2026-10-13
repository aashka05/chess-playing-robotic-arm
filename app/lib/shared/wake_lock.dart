import 'package:flutter/widgets.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

/// Keeps the screen on while held, e.g. during a game.
///
/// Uses wakelock_plus: FLAG_KEEP_SCREEN_ON on Android, idleTimerDisabled on
/// iOS (and the Screen Wake Lock API with a hidden-video fallback on web).
/// The lock is re-applied whenever the app comes back to the foreground,
/// since the OS may drop it while the app is hidden. Failures are ignored:
/// the screen simply sleeps as usual.
class ScreenWakeLock with WidgetsBindingObserver {
  ScreenWakeLock({@visibleForTesting Future<void> Function(bool enable)? setEnabled})
      : _setEnabled = setEnabled ?? ((enable) => WakelockPlus.toggle(enable: enable)) {
    WidgetsBinding.instance.addObserver(this);
  }

  final Future<void> Function(bool enable) _setEnabled;
  bool _held = false;

  bool get held => _held;

  void acquire() {
    if (_held) return;
    _held = true;
    _apply(true);
  }

  void release() {
    if (!_held) return;
    _held = false;
    _apply(false);
  }

  /// Releases the lock; call from the owning widget's dispose().
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    release();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _held) _apply(true);
  }

  void _apply(bool enable) {
    _setEnabled(enable).catchError((Object e) => debugPrint('Wake lock unavailable: $e'));
  }
}
