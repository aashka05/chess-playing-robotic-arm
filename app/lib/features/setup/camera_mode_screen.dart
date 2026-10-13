import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/ws_client.dart';
import '../../shared/wake_lock.dart';
import 'square_crop.dart';

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

  /// Manual flash (torch) for the current game. Off by default, never turned
  /// on automatically, not persisted; reset when the backend says the game ended.
  bool _torch = false;

  /// False once the camera has refused torch mode (no flash unit).
  bool _torchSupported = true;
  final _log = <String>[];
  final _wakeLock = ScreenWakeLock();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _wakeLock.acquire(); // the phone sits above the board for the whole game
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
      // Re-initialised after the app was in the background: restore the torch.
      if (_torch) await _setTorch(true);
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
      switch (m['type']) {
        case 'capture_request':
          _capture(m['request_id'] as String);
        case 'game_over':
          if (_torch) {
            _setTorch(false);
            _addLog('Game over: flash turned off');
          }
      }
    });
    socket.connect();
    _socket = socket;
    _ping = Timer.periodic(const Duration(seconds: 20), (_) => socket.send({'type': 'ping'}));
  }

  /// Torch mode keeps the light on, so every capture (and the preview) is lit
  /// the same way; the photo still goes through the normal square crop.
  Future<void> _setTorch(bool on) async {
    final camera = _camera;
    if (camera == null || !camera.value.isInitialized) return;
    try {
      await camera.setFlashMode(on ? FlashMode.torch : FlashMode.off);
      if (mounted) setState(() => _torch = on);
    } on CameraException catch (e) {
      if (!mounted) return;
      setState(() {
        _torch = false;
        if (on) _torchSupported = false;
      });
      _addLog('Flash unavailable: ${e.description ?? e.code}');
    }
  }

  Future<void> _capture(String requestId) async {
    final camera = _camera;
    if (camera == null || !camera.value.isInitialized) {
      _addLog('Capture requested but the camera is not ready');
      return;
    }
    try {
      final file = await camera.takePicture();
      // The detector expects square photos, matching the square viewfinder.
      final bytes = await compute(cropJpegToSquare, await file.readAsBytes());
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
    _wakeLock.dispose();
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
      appBar: AppBar(
        title: const Text('Camera mode'),
        actions: [
          IconButton(
            tooltip: !_torchSupported
                ? "Flash isn't available on this camera"
                : _torch
                    ? 'Turn flash off'
                    : 'Turn flash on (this game only)',
            isSelected: _torch,
            icon: const Icon(Icons.flash_off),
            selectedIcon: const Icon(Icons.flash_on),
            onPressed: camera == null || !_torchSupported ? null : () => _setTorch(!_torch),
          ),
        ],
      ),
      body: Column(children: [
        ListTile(
          leading: Icon(_connected ? Icons.cloud_done : Icons.cloud_off, color: _connected ? Colors.green : Colors.red),
          title: Text(_connected ? 'Connected. Waiting for capture requests.' : 'Connecting to backend…'),
          subtitle: const Text('Keep this phone mounted above the board with the screen on. Fit the whole board inside the square.'),
        ),
        Expanded(
          child: _error != null
              ? Center(child: Text(_error!))
              : camera == null
                  ? const Center(child: CircularProgressIndicator())
                  : Center(child: _SquarePreview(camera)),
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

/// The camera preview cropped to its centered square, i.e. exactly the part
/// of the frame that is uploaded.
class _SquarePreview extends StatelessWidget {
  const _SquarePreview(this.camera);

  final CameraController camera;

  @override
  Widget build(BuildContext context) {
    // previewSize is reported in landscape (width >= height).
    final size = camera.value.previewSize ?? const Size(4, 3);
    final portrait = MediaQuery.orientationOf(context) == Orientation.portrait;
    return AspectRatio(
      aspectRatio: 1,
      child: ClipRect(
        child: FittedBox(
          fit: BoxFit.cover,
          child: SizedBox(
            width: portrait ? size.height : size.width,
            height: portrait ? size.width : size.height,
            child: CameraPreview(camera),
          ),
        ),
      ),
    );
  }
}
