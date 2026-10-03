import Foundation
import Vision
import AppKit
// usage: facequality <image paths...> -> JSON lines {file, faces:[{x,y,w,h,quality}]}; quality = Vision face capture quality 0..1
// (sharpness, lighting, eyes open, expression). Also prints sharpness = variance of the Laplacian on the largest face crop.
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("{\"file\":\"\(path)\",\"error\":\"load\"}"); continue }
    let W = cg.width, H = cg.height
    let req = VNDetectFaceCaptureQualityRequest()
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    var faces: [String] = []
    for r in (req.results ?? []) {
        let b = r.boundingBox
        let x = Int(b.origin.x * CGFloat(W)); let w = Int(b.size.width * CGFloat(W))
        let h = Int(b.size.height * CGFloat(H)); let y = Int((1 - b.origin.y - b.size.height) * CGFloat(H))
        let q = r.faceCaptureQuality ?? 0
        faces.append("{\"x\":\(x),\"y\":\(y),\"w\":\(w),\"h\":\(h),\"quality\":\(q)}")
    }
    print("{\"file\":\"\(path)\",\"w\":\(W),\"h\":\(H),\"faces\":[\(faces.joined(separator: ","))]}")
}
