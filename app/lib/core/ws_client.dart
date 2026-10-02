import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import 'models.dart';

/// A JSON WebSocket that reconnects with backoff until [close] is called.
class ReconnectingSocket {
  ReconnectingSocket(this.uri, {this.onConnectionChange});

  final Uri uri;
  final void Function(bool connected)? onConnectionChange;

  final _messages = StreamController<Json>.broadcast();
  WebSocketChannel? _channel;
  bool _closed = false;
  Duration _backoff = const Duration(seconds: 1);

  Stream<Json> get messages => _messages.stream;

  void connect() => _run();

  Future<void> _run() async {
    while (!_closed) {
      try {
        final channel = WebSocketChannel.connect(uri);
        _channel = channel;
        await channel.ready;
        _backoff = const Duration(seconds: 1);
        onConnectionChange?.call(true);
        await for (final raw in channel.stream) {
          if (raw is String) _messages.add(jsonDecode(raw) as Json);
        }
      } catch (_) {
        // fall through to reconnect
      }
      if (_closed) break;
      onConnectionChange?.call(false);
      await Future<void>.delayed(_backoff);
      _backoff = Duration(seconds: (_backoff.inSeconds * 2).clamp(1, 10));
    }
  }

  void send(Json message) => _channel?.sink.add(jsonEncode(message));

  Future<void> close() async {
    _closed = true;
    await _channel?.sink.close();
    await _messages.close();
  }
}
