String formatClock(int ms) {
  final clamped = ms < 0 ? 0 : ms;
  final totalSeconds = clamped ~/ 1000;
  final minutes = totalSeconds ~/ 60;
  final seconds = totalSeconds % 60;
  if (clamped < 10000) {
    final tenths = (clamped % 1000) ~/ 100;
    return '$minutes:${seconds.toString().padLeft(2, '0')}.$tenths';
  }
  if (minutes >= 60) {
    return '${minutes ~/ 60}:${(minutes % 60).toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }
  return '$minutes:${seconds.toString().padLeft(2, '0')}';
}

String formatDate(DateTime d) {
  String two(int n) => n.toString().padLeft(2, '0');
  return '${d.year}-${two(d.month)}-${two(d.day)} ${two(d.hour)}:${two(d.minute)}';
}

String capitalize(String s) => s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1)}';

String resultLabel(String? result, String status) {
  if (status == 'aborted') return 'Aborted';
  if (status == 'in_progress') return 'In progress';
  return switch (result) { 'win' => 'Won', 'loss' => 'Lost', 'draw' => 'Draw', _ => '—' };
}

String terminationLabel(String? reason) => switch (reason) {
      'checkmate' => 'checkmate',
      'stalemate' => 'stalemate',
      'draw_rule' => 'draw rule',
      'resignation' => 'resignation',
      'timeout' => 'time out',
      'aborted' => 'aborted',
      _ => '',
    };
