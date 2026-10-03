// mouth <img...>  -> one JSON line per image: largest face, mouth openness (inner-lip gap / face h), smile (corner lift / face h), capture quality
import Foundation
import Vision
import AppKit
for path in CommandLine.arguments.dropFirst() {
  guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("{\"file\":\"\(path)\",\"error\":\"load\"}"); continue }
  let lm = VNDetectFaceLandmarksRequest()
  let q = VNDetectFaceCaptureQualityRequest()
  let h = VNImageRequestHandler(cgImage: cg, options: [:])
  try? h.perform([lm, q])
  let faces: [VNFaceObservation] = lm.results ?? []
  var best: VNFaceObservation? = nil
  for f in faces { if best == nil || f.boundingBox.width * f.boundingBox.height > best!.boundingBox.width * best!.boundingBox.height { best = f } }
  guard let f = best, let L = f.landmarks else { print("{\"file\":\"\(path)\",\"faces\":0}"); continue }
  let W = CGFloat(cg.width)
  let H = CGFloat(cg.height)
  let bb = f.boundingBox
  let fh: CGFloat = bb.height * H
  func pts(_ r: VNFaceLandmarkRegion2D?) -> [CGPoint] {
    var out: [CGPoint] = []
    for p in (r?.normalizedPoints ?? []) {
      let x: CGFloat = (bb.origin.x + p.x * bb.width) * W
      let y: CGFloat = (1.0 - (bb.origin.y + p.y * bb.height)) * H
      out.append(CGPoint(x: x, y: y))
    }
    return out
  }
  let inner = pts(L.innerLips)
  let outer = pts(L.outerLips)
  var openness: Double = 0
  var smile: Double = 0
  if inner.count >= 4 {
    var ymin: CGFloat = 1e9; var ymax: CGFloat = -1e9
    for p in inner { ymin = min(ymin, p.y); ymax = max(ymax, p.y) }
    openness = Double((ymax - ymin) / fh)
  }
  if outer.count >= 6 {
    var left = outer[0]; var right = outer[0]; var sum: CGFloat = 0
    for p in outer { if p.x < left.x { left = p }; if p.x > right.x { right = p }; sum += p.y }
    let mid: CGFloat = sum / CGFloat(outer.count)
    smile = Double((mid - (left.y + right.y) / 2.0) / fh)
  }
  var qual: Double = 0
  for r in (q.results ?? []) { let v = Double(r.faceCaptureQuality ?? 0); if v > qual { qual = v } }
  let x0 = Double(bb.origin.x * W); let y0 = Double((1.0 - bb.origin.y - bb.height) * H); let fw = Double(bb.width * W)
  print("{\"file\":\"\(path)\",\"faces\":\(faces.count),\"x\":\(Int(x0)),\"y\":\(Int(y0)),\"w\":\(Int(fw)),\"h\":\(Int(fh)),\"open\":\(String(format: "%.4f", openness)),\"smile\":\(String(format: "%.4f", smile)),\"quality\":\(String(format: "%.3f", qual))}")
}
