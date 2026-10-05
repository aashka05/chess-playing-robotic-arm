import 'package:chess_robot/features/setup/square_crop.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;

void main() {
  for (final (w, h) in [(640, 480), (480, 640), (300, 300)]) {
    test('crops a ${w}x$h photo to a centered square', () {
      final photo = img.Image(width: w, height: h);
      img.fill(photo, color: img.ColorRgb8(0, 0, 0));
      img.fillRect(photo, x1: w ~/ 2 - 5, y1: h ~/ 2 - 5, x2: w ~/ 2 + 5, y2: h ~/ 2 + 5, color: img.ColorRgb8(255, 255, 255));
      final out = img.decodeJpg(cropJpegToSquare(img.encodeJpg(photo)))!;
      final side = w < h ? w : h;
      expect((out.width, out.height), (side, side));
      expect(out.getPixel(side ~/ 2, side ~/ 2).r, greaterThan(200)); // the center stays centered
    });
  }

  test('applies EXIF rotation before cropping', () {
    final photo = img.Image(width: 640, height: 480)..exif.imageIfd.orientation = 6; // rotate 90°
    final out = img.decodeJpg(cropJpegToSquare(img.encodeJpg(photo)))!;
    expect((out.width, out.height), (480, 480));
    expect(out.exif.imageIfd.orientation ?? 1, 1);
  });
}
