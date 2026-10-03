// face <img...>  -> one JSON line per image, the LARGEST face (Colden 2026-10-02: thumbnail stills need eyes at the camera
// and a confirmed smile). Apple Vision: head pose (yaw / pitch / roll, degrees, rev 3 rectangles), where each PUPIL sits
// inside its eye contour (gx: 0 = outer-left .. 1 = right, 0.5 = centred; gy: 0 = top .. 1 = bottom), eye openness
// (eye contour height / width), mouth openness (inner-lip gap / face height), smile (mouth-corner lift / face height,
// positive = corners above the lip centre), mouth width / face width, capture quality.
import Foundation
import Vision
import AppKit
import CoreImage
// Core Image's face detector has what Vision lacks: a blink classifier per eye and a smile classifier (CIDetectorEyeBlink /
// CIDetectorSmile). Vision's eye CONTOUR stays "open" on a shut eye (C03 v1, 2026-10-02: a closed-eye still passed).
let ciDetector = CIDetector(ofType: CIDetectorTypeFace, context: nil, options: [CIDetectorAccuracy: CIDetectorAccuracyHigh])
func ciFace(_ cg: CGImage) -> (Bool, Bool, Bool, Bool) {       // found, leftClosed, rightClosed, smile  (the largest face)
  let feats = ciDetector?.features(in: CIImage(cgImage: cg), options: [CIDetectorEyeBlink: true, CIDetectorSmile: true]) ?? []
  var best: CIFaceFeature? = nil
  for f in feats { if let ff = f as? CIFaceFeature { if best == nil || ff.bounds.width * ff.bounds.height > best!.bounds.width * best!.bounds.height { best = ff } } }
  guard let b = best else { return (false, false, false, false) }
  return (true, b.leftEyeClosed, b.rightEyeClosed, b.hasSmile)
}
func deg(_ n: NSNumber?) -> Double { return n == nil ? 999 : n!.doubleValue * 180.0 / Double.pi }
for path in CommandLine.arguments.dropFirst() {
  guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("{\"file\":\"\(path)\",\"error\":\"load\"}"); continue }
  let rect = VNDetectFaceRectanglesRequest(); rect.revision = VNDetectFaceRectanglesRequestRevision3
  let lm = VNDetectFaceLandmarksRequest(); lm.revision = VNDetectFaceLandmarksRequestRevision3
  let q = VNDetectFaceCaptureQualityRequest()
  let h = VNImageRequestHandler(cgImage: cg, options: [:])
  try? h.perform([rect, lm, q])
  func biggest(_ fs: [VNFaceObservation]) -> VNFaceObservation? { return fs.max(by: { $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height }) }
  guard let f = biggest(lm.results ?? []), let L = f.landmarks else { print("{\"file\":\"\(path)\",\"faces\":0}"); continue }
  let pose = biggest(rect.results ?? [])
  let W = CGFloat(cg.width), H = CGFloat(cg.height), bb = f.boundingBox, fh = bb.height * H, fw = bb.width * W
  func pts(_ r: VNFaceLandmarkRegion2D?) -> [CGPoint] { return (r?.normalizedPoints ?? []).map { CGPoint(x: (bb.origin.x + $0.x * bb.width) * W, y: (1.0 - (bb.origin.y + $0.y * bb.height)) * H) } }
  func gaze(_ eye: [CGPoint], _ pupil: [CGPoint]) -> (Double, Double, Double) {
    guard eye.count >= 4, let p = pupil.first else { return (-1, -1, 0) }
    let xs = eye.map { $0.x }, ys = eye.map { $0.y }
    let w = xs.max()! - xs.min()!, hh = ys.max()! - ys.min()!
    return (w > 0 ? Double((p.x - xs.min()!) / w) : -1, hh > 0 ? Double((p.y - ys.min()!) / hh) : -1, w > 0 ? Double(hh / w) : 0)
  }
  let (lgx, lgy, lop) = gaze(pts(L.leftEye), pts(L.leftPupil)), (rgx, rgy, rop) = gaze(pts(L.rightEye), pts(L.rightPupil))
  let inner = pts(L.innerLips), outer = pts(L.outerLips)
  var openness = 0.0, smile = 0.0, mw = 0.0
  if inner.count >= 4 { let ys = inner.map { $0.y }; openness = Double((ys.max()! - ys.min()!) / fh) }
  if outer.count >= 6 {
    let left = outer.min(by: { $0.x < $1.x })!, right = outer.max(by: { $0.x < $1.x })!
    let mid = outer.map { $0.y }.reduce(0, +) / CGFloat(outer.count)
    smile = Double((mid - (left.y + right.y) / 2.0) / fh); mw = Double((right.x - left.x) / fw)
  }
  let qual = (q.results ?? []).map { Double($0.faceCaptureQuality ?? 0) }.max() ?? 0
  func box(_ e: [CGPoint]) -> String { guard e.count >= 4 else { return "[]" }; let xs = e.map { $0.x }, ys = e.map { $0.y }; return "[\(Int(xs.min()!)),\(Int(ys.min()!)),\(Int(xs.max()!)),\(Int(ys.max()!))]" }
  let s = { (v: Double) in String(format: "%.4f", v) }
  let ci = ciFace(cg)
  func pt(_ e: [CGPoint]) -> String { guard let p = e.first else { return "[]" }; return "[\(Int(p.x)),\(Int(p.y))]" }
  print("{\"file\":\"\(path)\",\"faces\":\((lm.results ?? []).count),\"x\":\(Int(bb.origin.x * W)),\"y\":\(Int((1.0 - bb.origin.y - bb.height) * H)),\"w\":\(Int(fw)),\"h\":\(Int(fh)),\"yaw\":\(s(deg(pose?.yaw))),\"pitch\":\(s(deg(pose?.pitch))),\"roll\":\(s(deg(pose?.roll))),\"gx\":[\(s(lgx)),\(s(rgx))],\"gy\":[\(s(lgy)),\(s(rgy))],\"eye_open\":[\(s(lop)),\(s(rop))],\"open\":\(s(openness)),\"smile\":\(s(smile)),\"mouth_w\":\(s(mw)),\"quality\":\(s(qual)),\"le\":\(box(pts(L.leftEye))),\"re\":\(box(pts(L.rightEye))),\"lp\":\(pt(pts(L.leftPupil))),\"rp\":\(pt(pts(L.rightPupil))),\"ci\":\(ci.0),\"l_closed\":\(ci.1),\"r_closed\":\(ci.2),\"ci_smile\":\(ci.3)}")
}
