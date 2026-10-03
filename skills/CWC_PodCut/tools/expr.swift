import Foundation
import Vision
import CoreImage
// expr <width> <height>   - reads raw BGRA frames (width*height*4 bytes each) on stdin, prints one JSON line per frame
// for the LARGEST face: Apple Vision landmarks (lips, eyes) + pose, and CoreImage's smile / eye-blink classifier.
//   {"n":i,"face":0|1,"x","y","w","h" (box / frame, y from the top),"roll","yaw","pitch" (radians, null when unknown),
//    "mw" mouth width / face width, "mo" inner-lip opening / mouth width (teeth showing = laugh),
//    "lift" how far the lip corners sit ABOVE the lip centre / mouth width (a smile lifts them),
//    "eye" eye opening / eye width (mean of both), "smile" 0|1 and "blink" 0|1 from CIDetector, "q" capture quality}
// Used by CWC_PodCut faces.py (2 fps baseline) and reactions.py (10 fps check of each candidate).
let W = Int(CommandLine.arguments[1])!, H = Int(CommandLine.arguments[2])!
let frameBytes = W * H * 4
let cs = CGColorSpaceCreateDeviceRGB()
let ciCtx = CIContext(options: nil)
let detector = CIDetector(ofType: CIDetectorTypeFace, context: ciCtx, options: [CIDetectorAccuracy: CIDetectorAccuracyHigh])!
let input = FileHandle.standardInput
func num(_ v: Double?) -> String { if let v = v, v.isFinite { return String(format: "%.4f", v) } else { return "null" } }
var n = 0
while true {
    var data = Data(); data.reserveCapacity(frameBytes)
    while data.count < frameBytes {
        let chunk = input.readData(ofLength: frameBytes - data.count)
        if chunk.isEmpty { break }
        data.append(chunk)
    }
    if data.count < frameBytes { break }
    // One autoreleasepool per frame: without it the Vision / CoreImage objects of every frame pile up, and after ~5,300
    // frames (44 min at 2 fps) the requests silently return no face - half of Ep 24 had no expression track (2026-10-01).
    autoreleasepool {
        guard let provider = CGDataProvider(data: data as CFData),
              let cg = CGImage(width: W, height: H, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: W * 4, space: cs,
                               bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue),
                               provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent) else { print("{\"n\":\(n),\"face\":0}"); return }
        let lreq = VNDetectFaceLandmarksRequest(); let qreq = VNDetectFaceCaptureQualityRequest()
        let handler = VNImageRequestHandler(cgImage: cg, options: [:])
        try? handler.perform([lreq, qreq])
        guard let face = (lreq.results ?? []).max(by: { $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height }) else { print("{\"n\":\(n),\"face\":0}"); return }
        let b = face.boundingBox
        var mw: Double? = nil, mo: Double? = nil, lift: Double? = nil, eye: Double? = nil
        if let lm = face.landmarks {
            // landmark points are normalised to the face box (origin bottom-left); aspect-correct them into face-width units
            let ar = Double(b.height * CGFloat(H)) / Double(b.width * CGFloat(W))
            func pts(_ r: VNFaceLandmarkRegion2D?) -> [(Double, Double)] { (r?.normalizedPoints ?? []).map { (Double($0.x), Double($0.y) * ar) } }
            let outer = pts(lm.outerLips), inner = pts(lm.innerLips)
            if outer.count >= 6 {
                let l = outer.min(by: { $0.0 < $1.0 })!, r = outer.max(by: { $0.0 < $1.0 })!
                let width = hypot(r.0 - l.0, r.1 - l.1); mw = width
                let cx = (l.0 + r.0) / 2; let mid = outer.filter { abs($0.0 - cx) < width * 0.25 }
                if let top = mid.max(by: { $0.1 < $1.1 }), let bot = mid.min(by: { $0.1 < $1.1 }), width > 1e-6 {
                    lift = ((l.1 + r.1) / 2 - (top.1 + bot.1) / 2) / width
                }
                if inner.count >= 4, width > 1e-6 {
                    let ys = inner.map { $0.1 }; mo = (ys.max()! - ys.min()!) / width
                }
            }
            func openness(_ r: VNFaceLandmarkRegion2D?) -> Double? {
                let p = pts(r); if p.count < 4 { return nil }
                let xs = p.map { $0.0 }, ys = p.map { $0.1 }; let w = xs.max()! - xs.min()!
                return w > 1e-6 ? (ys.max()! - ys.min()!) / w : nil
            }
            let e = [openness(lm.leftEye), openness(lm.rightEye)].compactMap { $0 }
            if !e.isEmpty { eye = e.reduce(0, +) / Double(e.count) }
        }
        var smile = 0, blink = 0
        let ci = CIImage(cgImage: cg)
        let feats = detector.features(in: ci, options: [CIDetectorSmile: true, CIDetectorEyeBlink: true]).compactMap { $0 as? CIFaceFeature }
        // the CI face nearest the Vision face (CI coordinates: pixels, origin bottom-left)
        let fcx = Double(b.midX) * Double(W), fcy = Double(b.midY) * Double(H)
        if let f = feats.min(by: { hypot(Double($0.bounds.midX) - fcx, Double($0.bounds.midY) - fcy) < hypot(Double($1.bounds.midX) - fcx, Double($1.bounds.midY) - fcy) }),
           hypot(Double(f.bounds.midX) - fcx, Double(f.bounds.midY) - fcy) < Double(b.width) * Double(W) {
            smile = f.hasSmile ? 1 : 0; blink = (f.leftEyeClosed && f.rightEyeClosed) ? 1 : 0
        } else { smile = -1 }
        let q = (qreq.results ?? []).max(by: { $0.boundingBox.width < $1.boundingBox.width })?.faceCaptureQuality
        print("{\"n\":\(n),\"face\":1,\"x\":\(num(Double(b.minX))),\"y\":\(num(1 - Double(b.maxY))),\"w\":\(num(Double(b.width))),\"h\":\(num(Double(b.height))),\"roll\":\(num(face.roll?.doubleValue)),\"yaw\":\(num(face.yaw?.doubleValue)),\"pitch\":\(num(face.pitch?.doubleValue)),\"mw\":\(num(mw)),\"mo\":\(num(mo)),\"lift\":\(num(lift)),\"eye\":\(num(eye)),\"smile\":\(smile),\"blink\":\(blink),\"q\":\(num(q.map { Double($0) }))}")
    }
    n += 1
    if n % 20 == 0 { fflush(stdout) }
}
fflush(stdout)
