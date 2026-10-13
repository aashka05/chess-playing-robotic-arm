import 'dart:convert';

import 'package:chess_robot/core/api_client.dart';
import 'package:chess_robot/core/providers.dart';
import 'package:chess_robot/features/setup/setup_providers.dart';
import 'package:chess_robot/features/setup/setup_wizard.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

const startFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

void main() {
  group('SetupProgress rules', () {
    test('cannot move past a step that is not done', () {
      const p = SetupProgress();
      expect(p.blockedReason(1), contains('empty board'));
      expect(p.blockedReason(2), contains('empty board'));
      expect(p.blockedReason(0), isNull);
    });

    test('completing a step unlocks the next one only', () {
      final p = const SetupProgress().complete(0);
      expect(p.blockedReason(1), isNull);
      expect(p.goTo(1).blockedReason(2), contains('starting position'));
    });

    test('any visited step can be revisited in both directions', () {
      final p = const SetupProgress().complete(0).goTo(1).complete(1).goTo(2);
      expect(p.reached, 2);
      final back = p.goTo(0);
      expect(back.blockedReason(1), isNull);
      expect(back.blockedReason(2), isNull);
      expect(back.goTo(2).current, 2);
    });

    test('redoing a step invalidates the steps after it', () {
      final p = const SetupProgress().complete(0).goTo(1).complete(1).goTo(2).goTo(0).complete(0);
      expect(p.completed, {0});
      expect(p.reached, 1);
      expect(p.blockedReason(1), isNull);
      expect(p.goTo(1).blockedReason(2), contains('starting position'));
    });

    test('a failed piece check needs redoing before the options', () {
      final p = const SetupProgress().complete(0).goTo(1).complete(1).goTo(2).goTo(1).fail(1);
      expect(p.reached, 1);
      expect(p.blockedReason(2), isNotNull);
    });
  });

  testWidgets('wizard: free back and forth, data kept, validation shown', (tester) async {
    tester.view.physicalSize = const Size(500, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final calls = <String>[];
    final client = MockClient((request) async {
      calls.add('${request.method} ${request.url.path}');
      final body = switch (request.url.path) {
        '/setup/calibrate' => {'state': 'SETUP_PIECES', 'preview_jpeg_base64': ''},
        '/setup/verify' => {'state': 'COLOR_SELECT', 'correct': true, 'expected_fen': startFen, 'mismatches': []},
        _ => <String, Object>{},
      };
      return http.Response(jsonEncode(body), 200, headers: {'content-type': 'application/json'});
    });
    await tester.pumpWidget(ProviderScope(
      overrides: [
        apiClientProvider.overrideWithValue(ApiClient(baseUrl: 'http://test', httpClient: client)),
        cameraConnectedProvider.overrideWith((ref) => Stream.value(true)),
      ],
      child: const MaterialApp(home: SetupWizardScreen()),
    ));
    await tester.pumpAndSettle();
    Future<void> tap(Finder f) async {
      await tester.ensureVisible(f);
      await tester.tap(f);
      await tester.pumpAndSettle();
    }

    expect(find.text('Setup 1 of 3'), findsOneWidget);

    // Next without the photo: an error, not a silent no-op.
    await tap(find.text('Next'));
    expect(find.text('Setup 1 of 3'), findsOneWidget);
    expect(find.textContaining('Photograph the empty board first'), findsOneWidget);
    // Same for jumping ahead with the step indicator.
    await tap(find.byKey(const ValueKey('setup-step-2')));
    expect(find.text('Setup 1 of 3'), findsOneWidget);

    await tap(find.text('Take photo'));
    expect(find.text('Setup 2 of 3'), findsOneWidget);
    expect(find.byKey(const ValueKey('setup-error')), findsNothing);

    // Back to 1 and forward again, without retaking the photo.
    await tap(find.text('Back'));
    expect(find.text('Setup 1 of 3'), findsOneWidget);
    expect(find.text('Retake photo'), findsOneWidget);
    await tap(find.text('Next'));
    expect(find.text('Setup 2 of 3'), findsOneWidget);
    expect(calls.where((c) => c.endsWith('/calibrate')).length, 1);

    // Step 3 needs the pieces checked first.
    await tap(find.text('Next'));
    expect(find.textContaining('confirm the starting position'), findsOneWidget);
    await tap(find.text('Check position'));
    expect(find.text('Setup 3 of 3'), findsOneWidget);

    // Enter some options, wander back to step 1 via the indicator, come back: still there.
    await tap(find.text('Hard'));
    await tap(find.text('Black'));
    await tap(find.byKey(const ValueKey('setup-step-0')));
    expect(find.text('Setup 1 of 3'), findsOneWidget);
    await tap(find.byKey(const ValueKey('setup-step-2')));
    expect(find.text('Setup 3 of 3'), findsOneWidget);
    expect(find.text('The robot plays White and moves first.'), findsOneWidget);
    final difficulty = tester.widget<SegmentedButton<String>>(find.byType(SegmentedButton<String>).last);
    expect(difficulty.selected, {'hard'});

    // Back/Next buttons stay in sync with the indicator.
    await tap(find.text('Back'));
    expect(find.text('Setup 2 of 3'), findsOneWidget);
    await tap(find.text('Next'));
    expect(find.text('Setup 3 of 3'), findsOneWidget);
    expect(find.text('Next'), findsNothing); // Start is the action on the last step
    expect(calls.where((c) => c.endsWith('/verify')).length, 1);
  });
}
