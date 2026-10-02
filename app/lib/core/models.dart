// Typed models for the backend's REST and WebSocket payloads.

typedef Json = Map<String, dynamic>;

class User {
  const User({required this.id, required this.username, required this.email, required this.role});

  final int id;
  final String username;
  final String email;
  final String role;

  bool get isAdmin => role == 'admin';

  factory User.fromJson(Json j) => User(
        id: j['user_id'] as int,
        username: j['username'] as String,
        email: j['email'] as String,
        role: j['role'] as String,
      );

  Json toJson() => {'user_id': id, 'username': username, 'email': email, 'role': role};
}

class AuthSession {
  const AuthSession({required this.token, required this.user});

  final String token;
  final User user;

  factory AuthSession.fromJson(Json j) =>
      AuthSession(token: j['access_token'] as String, user: User.fromJson(j['user'] as Json));
}

class MoveInfo {
  const MoveInfo({
    required this.ply,
    required this.san,
    required this.uci,
    required this.player,
    required this.fenAfter,
    required this.timeTakenMs,
    this.evalCp,
    this.evalMate,
    this.detectionConfidence,
  });

  final int ply;
  final String san;
  final String uci;
  final String player; // human | robot
  final String fenAfter;
  final int timeTakenMs;
  final int? evalCp;
  final int? evalMate;
  final double? detectionConfidence;

  bool get hasEval => evalCp != null || evalMate != null;

  /// Live snapshots use `ply`/`san`; the REST history uses `move_number`/`move`.
  factory MoveInfo.fromJson(Json j) => MoveInfo(
        ply: (j['ply'] ?? j['move_number']) as int,
        san: (j['san'] ?? j['move']) as String,
        uci: j['uci'] as String,
        player: j['player'] as String,
        fenAfter: j['fen_after'] as String,
        timeTakenMs: j['time_taken_ms'] as int,
        evalCp: j['eval_cp'] as int?,
        evalMate: j['eval_mate'] as int?,
        detectionConfidence: (j['detection_confidence'] as num?)?.toDouble(),
      );

  MoveInfo withEval(int? cp, int? mate) => MoveInfo(
        ply: ply,
        san: san,
        uci: uci,
        player: player,
        fenAfter: fenAfter,
        timeTakenMs: timeTakenMs,
        evalCp: cp,
        evalMate: mate,
        detectionConfidence: detectionConfidence,
      );
}

class GameSummary {
  const GameSummary({
    required this.id,
    required this.username,
    required this.startTime,
    required this.endTime,
    required this.difficulty,
    required this.result,
    required this.status,
    required this.terminationReason,
    required this.userColor,
    required this.timeBaseSec,
    required this.timeIncrementSec,
    required this.moveCount,
  });

  final int id;
  final String? username;
  final DateTime startTime;
  final DateTime? endTime;
  final String difficulty;
  final String? result;
  final String status;
  final String? terminationReason;
  final String userColor;
  final int timeBaseSec;
  final int timeIncrementSec;
  final int moveCount;

  String get timeControl => '${timeBaseSec ~/ 60}+$timeIncrementSec';

  factory GameSummary.fromJson(Json j) => GameSummary(
        id: j['game_id'] as int,
        username: j['username'] as String?,
        startTime: DateTime.parse(j['start_time'] as String).toLocal(),
        endTime: j['end_time'] == null ? null : DateTime.parse(j['end_time'] as String).toLocal(),
        difficulty: j['difficulty'] as String,
        result: j['result'] as String?,
        status: j['status'] as String,
        terminationReason: j['termination_reason'] as String?,
        userColor: j['user_color'] as String,
        timeBaseSec: j['time_base_sec'] as int,
        timeIncrementSec: j['time_increment_sec'] as int,
        moveCount: (j['move_count'] ?? 0) as int,
      );
}

class GameDetail {
  const GameDetail({
    required this.summary,
    required this.initialFen,
    required this.finalFen,
    required this.pgn,
    required this.moves,
  });

  final GameSummary summary;
  final String initialFen;
  final String? finalFen;
  final String? pgn;
  final List<MoveInfo> moves;

  factory GameDetail.fromJson(Json j) => GameDetail(
        summary: GameSummary.fromJson(j),
        initialFen: j['initial_fen'] as String,
        finalFen: j['final_fen'] as String?,
        pgn: j['pgn'] as String?,
        moves: [for (final m in j['moves'] as List) MoveInfo.fromJson(m as Json)],
      );
}

class ClockState {
  const ClockState({
    required this.whiteMs,
    required this.blackMs,
    required this.running,
    required this.baseMs,
    required this.incrementMs,
  });

  final int whiteMs;
  final int blackMs;
  final String? running; // white | black | null
  final int baseMs;
  final int incrementMs;

  factory ClockState.fromJson(Json j) => ClockState(
        whiteMs: j['white_ms'] as int,
        blackMs: j['black_ms'] as int,
        running: j['running'] as String?,
        baseMs: j['base_ms'] as int,
        incrementMs: j['increment_ms'] as int,
      );

  int msFor(String color) => color == 'white' ? whiteMs : blackMs;
}

class ManualAction {
  const ManualAction({required this.kind, required this.message, this.square, this.piece});

  final String kind; // place_promoted_piece | arm_error
  final String message;
  final String? square;
  final String? piece;

  factory ManualAction.fromJson(Json j) => ManualAction(
        kind: j['kind'] as String,
        message: j['message'] as String,
        square: j['square'] as String?,
        piece: j['piece'] as String?,
      );
}

/// Backend state machine states that matter to the game screen.
abstract final class GamePhase {
  static const humanTurn = 'HUMAN_TURN';
  static const detecting = 'DETECTING';
  static const engineThinking = 'ENGINE_THINKING';
  static const armExecuting = 'ARM_EXECUTING';
  static const gameOver = 'GAME_OVER';
}

/// One `{"type": "state"}` snapshot from /ws/games/{id}.
class LiveGameState {
  const LiveGameState({
    required this.gameId,
    required this.state,
    required this.fen,
    required this.turn,
    required this.inCheck,
    required this.userColor,
    required this.difficulty,
    required this.clock,
    required this.moves,
    required this.lastMove,
    required this.message,
    required this.manualAction,
    required this.status,
    required this.result,
    required this.terminationReason,
    required this.cameraConnected,
  });

  final int gameId;
  final String state;
  final String fen;
  final String turn;
  final bool inCheck;
  final String userColor;
  final String difficulty;
  final ClockState? clock;
  final List<MoveInfo> moves;
  final String? lastMove;
  final String? message;
  final ManualAction? manualAction;
  final String status;
  final String? result;
  final String? terminationReason;
  final bool cameraConnected;

  String get robotColor => userColor == 'white' ? 'black' : 'white';
  bool get isOver => state == GamePhase.gameOver;

  factory LiveGameState.fromJson(Json j) => LiveGameState(
        gameId: j['game_id'] as int,
        state: j['state'] as String,
        fen: j['fen'] as String,
        turn: j['turn'] as String,
        inCheck: (j['in_check'] ?? false) as bool,
        userColor: j['user_color'] as String,
        difficulty: j['difficulty'] as String,
        clock: j['clock'] == null ? null : ClockState.fromJson(j['clock'] as Json),
        moves: [for (final m in j['moves'] as List) MoveInfo.fromJson(m as Json)],
        lastMove: j['last_move'] as String?,
        message: j['message'] as String?,
        manualAction: j['manual_action'] == null ? null : ManualAction.fromJson(j['manual_action'] as Json),
        status: j['status'] as String,
        result: j['result'] as String?,
        terminationReason: j['termination_reason'] as String?,
        cameraConnected: (j['camera_connected'] ?? false) as bool,
      );

  LiveGameState withMoves(List<MoveInfo> newMoves) => LiveGameState(
        gameId: gameId,
        state: state,
        fen: fen,
        turn: turn,
        inCheck: inCheck,
        userColor: userColor,
        difficulty: difficulty,
        clock: clock,
        moves: newMoves,
        lastMove: lastMove,
        message: message,
        manualAction: manualAction,
        status: status,
        result: result,
        terminationReason: terminationReason,
        cameraConnected: cameraConnected,
      );
}

class SetupStatus {
  const SetupStatus({required this.state, required this.cameraConnected});

  final String state;
  final bool cameraConnected;

  factory SetupStatus.fromJson(Json j) =>
      SetupStatus(state: j['state'] as String, cameraConnected: (j['camera_connected'] ?? false) as bool);
}

class CalibrationResult {
  const CalibrationResult({required this.state, required this.previewJpegBase64});

  final String state;
  final String previewJpegBase64;

  factory CalibrationResult.fromJson(Json j) => CalibrationResult(
        state: j['state'] as String,
        previewJpegBase64: (j['preview_jpeg_base64'] ?? '') as String,
      );
}

class Mismatch {
  const Mismatch({required this.square, this.expected, this.detected});

  final String square;
  final String? expected; // FEN symbol or null (empty)
  final String? detected;

  factory Mismatch.fromJson(Json j) => Mismatch(
        square: j['square'] as String,
        expected: j['expected'] as String?,
        detected: j['detected'] as String?,
      );
}

class VerifyResult {
  const VerifyResult({required this.state, required this.correct, required this.expectedFen, required this.mismatches});

  final String state;
  final bool correct;
  final String expectedFen;
  final List<Mismatch> mismatches;

  factory VerifyResult.fromJson(Json j) => VerifyResult(
        state: j['state'] as String,
        correct: j['correct'] as bool,
        expectedFen: j['expected_fen'] as String,
        mismatches: [for (final m in j['mismatches'] as List) Mismatch.fromJson(m as Json)],
      );
}

class GameOptions {
  const GameOptions({
    required this.color,
    required this.difficulty,
    required this.timeBaseSec,
    required this.timeIncrementSec,
  });

  final String color;
  final String difficulty;
  final int timeBaseSec;
  final int timeIncrementSec;

  Json toJson() => {
        'color': color,
        'difficulty': difficulty,
        'time_base_sec': timeBaseSec,
        'time_increment_sec': timeIncrementSec,
      };
}
