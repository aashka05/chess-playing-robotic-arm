import 'dart:math';
import 'dart:typed_data';

import 'package:image/image.dart' as img;

/// Center-crops a JPEG to 1:1 (EXIF rotation applied first, so portrait and
/// landscape shots both come out upright). Returns [jpeg] unchanged if it
/// can't be decoded; the backend crops again in that case.
Uint8List cropJpegToSquare(Uint8List jpeg) {
  final decoded = img.decodeJpg(jpeg);
  if (decoded == null) return jpeg;
  final image = img.bakeOrientation(decoded);
  final side = min(image.width, image.height);
  final square = img.copyCrop(
    image,
    x: (image.width - side) ~/ 2,
    y: (image.height - side) ~/ 2,
    width: side,
    height: side,
  );
  return img.encodeJpg(square, quality: 92);
}
