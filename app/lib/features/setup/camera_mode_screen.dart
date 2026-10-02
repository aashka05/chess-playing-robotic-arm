import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/ws_client.dart';

/// Phone A: mounted above the board. Waits for capture requests from the
/// backend, takes a photo and uploads it (the AppUploadCameraSource).
class CameraModeScreen extends ConsumerStatefulWidget {
  const CameraModeScreen({super.key});

  @override
  ConsumerState<CameraModeScreen> createState() => _CameraModeScreenState();
}

class _CameraModeScreenState extends ConsumerState<CameraModeScreen> with WidgetsBindingObserver {
  CameraController? _camera;
  ReconnectingSocket? _socket;
  StreamSubscription? _sub;
  Timer? _ping;
  bool _connected = false;
  String? _error;
  final _log = <String>[];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initCamera();
    _connect();
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      final back = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );
      final controller = CameraController(back, ResolutionPreset.veryHigh, enableAudio: false);
      await controller.initialize();
      await controller.setFlashMode(FlashMode.off);
      if (!mounted) return controller.dispose();
      setState(() => _camera = controller);
    } catch (e) {
      setState(() => _error = 'Camera error: $e');
    }
  }

  void _connect() {
    final api = ref.read(apiClientProvider);
    final socket = ReconnectingSocket(
      api.wsUri('/ws/camera'),
      onConnectionChange: (c) => mounted ? setState(() => _connected = c) : null,
    );
    _sub = socket.messages.listen((m) {
      if (m['type'] == 'capture_request') _capture(m['request_id'] as String);
    });
    socket.connect();
    _socket = socket;
    _ping = Timer.periodic(const Duration(seconds: 20), (_) => socket.send({'type': 'ping'}));
  }

  Future<void> _capture(String requestId) async {
    final camera = _camera;
    if (camera == null || !camera.value.isInitialized) {
      _addLog('Capture requested but the camera is not ready');
      return;
    }
    try {
      final file = await camera.takePicture();
      final bytes = await file.readAsBytes();
      await ref.read(apiClientProvider).uploadCapture(requestId, bytes);
      _addLog('Photo sent (${(bytes.length / 1024).round()} KB)');
    } catch (e) {
      _addLog('Capture failed: $e');
    }
  }

  void _addLog(String line) {
    if (!mounted) return;
    final now = TimeOfDay.now().format(context);
    setState(() {
      _log.insert(0, '$now  $line');
      if (_log.length > 20) _log.removeLast();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final camera = _camera;
    if (camera == null) return;
    if (state == AppLifecycleState.inactive) {
      camera.dispose();
      setState(() => _camera = null);
    } else if (state == AppLifecycleState.resumed) {
      _initCamera();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _ping?.cancel();
    _sub?.cancel();
    _socket?.close();
    _camera?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final camera = _camera;
    return Scaffold(
      appBar: AppBar(title: const Text('Camera mode')),
      body: Column(children: [
        ListTile(
          leading: Icon(_connected ? Icons.cloud_done : Icons.cloud_off, color: _connected ? Colors.green : Colors.red),
          title: Text(_connected ? 'Connected. Waiting for capture requests.' : 'Connecting to backend…'),
          subtitle: const Text('Keep this phone mounted above the board with the screen on.'),
        ),
        Expanded(
          child: _error != null
              ? Center(child: Text(_error!))
              : camera == null
                  ? const Center(child: CircularProgressIndicator())
                  : Center(child: CameraPreview(camera)),
        ),
        SizedBox(
          height: 120,
          child: ListView(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: [for (final l in _log) Text(l, style: Theme.of(context).textTheme.bodySmall)],
          ),
        ),
      ]),
    );
  }
}
